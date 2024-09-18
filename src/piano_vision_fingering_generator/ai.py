import json
import logging
from dataclasses import dataclass
from itertools import islice
from typing import Any, Generic, Optional, TypeVar

import requests
import torch
import transformers
from tqdm import tqdm

from piano_vision_fingering_generator.constants import Finger, HandSize
from piano_vision_fingering_generator.models import (
    Note,
    PianoVisionMeasure,
    PianoVisionSong,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMNote:
    id: str
    note: str
    finger: int | str

    def __post_init__(self):
        if isinstance(self.finger, str):
            self.finger = int(self.finger)

    @classmethod
    def from_note(cls, note: Note) -> "LLMNote":
        return cls(note.id, note.note_name, note.finger.value)

    @classmethod
    def from_dict(cls, note: dict[str, Any]) -> "LLMNote":
        return cls(note["id"], note["note"], note["fingering"])


class LLMFingeringGeneratorAgent:
    @classmethod
    def _format_note_for_prompt(cls, note: Note) -> dict:
        return {
            "id": note.id,
            "note": note.note_name,
            "finger": note.finger.value if note.finger is not None else None,
            "start": note.start,
        }

    @classmethod
    def _build_note_prompt(cls, notes: dict[str, list[Note]]) -> str:
        data = {"right": [cls._format_note_for_prompt(n) for n in notes["right"]]}
        data["left"] = [cls._format_note_for_prompt(n) for n in notes["left"]]
        return json.dumps(data)

    @staticmethod
    def _parse_response(
        data: dict[str, list[dict[str, str]]],
    ) -> dict[str, list[LLMNote]]:
        result = {"right": [], "left": []}
        for llm_data in data["right"]:
            llm_note = LLMNote.from_dict(llm_data)
            result["right"].append(llm_note)
        for llm_data in data["left"]:
            llm_note = LLMNote.from_dict(llm_data)
            result["left"].append(llm_note)
        return result

    def run(
        self,
        hand_size: HandSize,
        new_notes: dict[str, list[Note]],
        previous_notes: Optional[dict[str, list[Note]]] = None,
    ) -> dict[str, list[LLMNote]]:
        prompt = self._generate_fingering_prompt(hand_size, new_notes, previous_notes)
        return self._execute(prompt)

    def _generate_fingering_prompt(
        self,
        hand_size: HandSize,
        new_notes: dict[str, list[Note]],
        previous_notes: Optional[dict[str, list[Note]]] = None,
    ) -> str:
        raise NotImplementedError("Must be implemented in a subclass.")

    def _execute(self, prompt: str) -> dict[str, list[LLMNote]]:
        raise NotImplementedError("Must be implemented in a subclass.")


LLMFingeringGeneratorAgentT = TypeVar(
    "LLMFingeringGeneratorAgentT", bound=LLMFingeringGeneratorAgent
)


@dataclass
class LMStudioAgent(LLMFingeringGeneratorAgent):
    url: str = "http://localhost:1234"

    def _send_request(self, message: str) -> dict[str, list[dict[str, str]]]:
        payload = {"messages": [{"role": "user", "content": message}]}
        response = requests.post(
            f"{self.url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        result_data = result["choices"][0]["message"]["content"]
        return json.loads(result_data)

    def send_request(self, message: str) -> dict[str, list[LLMNote]]:
        retry_count = 0
        while retry_count < 3:
            try:
                response = self._send_request(message)
                return self._parse_response(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from LLM. error: {e}")
                retry_count += 1
                continue
            except Exception:
                raise
        raise ValueError("Failed to get a valid response from the LLM.")

    def _generate_fingering_prompt(
        self,
        hand_size: HandSize,
        new_notes: dict[str, list[Note]],
        previous_notes: Optional[dict[str, list[Note]]] = None,
    ) -> str:
        """
        Generate a structured prompt for the LLM to assign fingerings to new notes.

        Returns:
        - A string prompt ready to be used for the LLM
        """
        prompt_dict: dict[str, Any] = {
            "hand_span": f"{hand_size.to_span()} cm",
        }
        if previous_notes is not None:
            prompt_dict["previous_notes"] = self._build_note_prompt(previous_notes)
        new_notes_str = self._build_note_prompt(new_notes)
        prompt_dict["assign_notes"] = new_notes_str
        return json.dumps(prompt_dict)

    def _execute(self, prompt: str) -> dict[str, list[LLMNote]]:
        return self.send_request(prompt)


@dataclass
class LLMModelAgent(LLMFingeringGeneratorAgent):
    model_id: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    max_new_tokens: int = 300

    def __post_init__(self) -> None:
        self.quantization_config = transformers.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            self.model_id,
            device_map="auto",
            torch_dtype=torch.float16,
            quantization_config=self.quantization_config,
        )
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(self.model_id)
        # self.generator: transformers.Pipeline = transformers.pipeline(
        #     "text-generation",
        #     model=self.model_id,
        #     model_kwargs={
        #         "torch_dtype": torch.float16,
        #     },
        #     device_map="auto",
        # )

    @property
    def preprompt(self) -> str:
        return """
        You are a professional piano player.
        You need to pick the finger to use for notes in a piano piece.
        
        Follow these guidelines and rules;
            - Each note must have exactly one corresponding finger. 
            - Use the following numbers for each note's fingering: 
                - Thumb 1 
                - Index finger 2 
                - Middle finger 3 
                - Ring finger: 4
                - Pinky finger: 5
            - Minimize hand and finger movement for efficiency and comfort.
            - Avoid using the same finger for sequential notes.
            - Assign a score for confidence on finger picked from 0 to 1
            - Add the reasoning behind picking that finger

            General Guidelines for Both Hands:
            - Use shorter fingers (thumb and pinky) for white keys
            - User longer fingers (index, middle, ring) for black keys when possible.
            - Avoid using the thumb on black keys unless absolutely necessary.
            - For chromatic passages, alternate fingers between black and white.
            - Maintain consistent fingering for repeated patterns.

            Right Hand Guidelines:
            - Use the thumb (1) for the lowest notes.
            - Use the index (2) and middle (3) fingers for middle-range notes.
            - Use the ring (4) and pinky (5) for higher notes.
            - Alternate between fingers for sequential notes to avoid hand strain.

            Left Hand Guidelines:
            - Use the pinky (5) for the lowest notes.
            - Use the index (2) and **middle (3)** for middle-range notes.
            - Use the thumb (1) for notes between C3 and C4.
            - Use the ring finger (4) for smooth transitions in higher ranges.

        Do not output anything other than the JSON format specified.
        Do not output comments. Do not output code.
        Output JSON only.
        Make sure the JSON is correctly formatted to be parsed.

        Output JSON in the following format:
        {
            "left": [
                {
                    "id": <id>, 
                    "note": <note>,
                    "start": <start>,
                    "reason": <reason>, 
                    "fingering": <fingering>,
                    "score": <score>
                },
                ...
            ],
            "right":[
                {
                    "id": <id>, 
                    "note": <note>,
                    "start": <start>,
                    "reason": <reason>,
                    "fingering": <fingering>,
                    "score"; <score>
                },
                ...
            ]
        }
        """

    def _generate_fingering_prompt(
        self,
        hand_size: HandSize,
        new_notes: dict[str, list[Note]],
        previous_notes: Optional[dict[str, list[Note]]] = None,
    ) -> str:
        """
        Generate a structured prompt for the LLM to assign fingerings to new notes.

        Returns:
        - A string prompt ready to be used for the LLM
        """
        prompt_dict: dict[str, Any] = {
            "hand_span": f"{hand_size.to_span()} cm",
            "rules": self.preprompt,
        }
        if previous_notes is not None:
            prompt_dict["previous_notes"] = self._build_note_prompt(previous_notes)
        new_notes_str = self._build_note_prompt(new_notes)
        prompt_dict["assign_notes"] = new_notes_str
        return json.dumps(prompt_dict)

    def _execute(self, prompt: str) -> dict[str, list[LLMNote]]:
        input_ids = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        # raw_response: Any = self.generator(
        #     prompt, max_new_tokens=self.max_new_tokens
        # )  # what is the real return type?
        output_ids = self.model.generate(
            **input_ids, max_new_tokens=self.max_new_tokens
        )
        raw_response: str = self.tokenizer.decode(
            output_ids[0], skip_special_tokens=True
        )
        raw_response = raw_response.replace(prompt, "")
        response = json.loads(raw_response)
        return self._parse_response(response)


@dataclass
class PianoVisionFingeringGeneratorAI(Generic[LLMFingeringGeneratorAgentT]):
    song: PianoVisionSong
    agent: LLMFingeringGeneratorAgentT
    measures_per_prompt: int = 10
    hand_size: HandSize = HandSize.MEDIUM

    @staticmethod
    def group_and_flatten_objects(
        measures: list[PianoVisionMeasure], group_size: int
    ) -> list[list[Note]]:
        it = iter(measures)
        return list(
            iter(
                lambda: [
                    note for measure in islice(it, group_size) for note in measure.notes
                ],
                [],
            )
        )

    def build(self) -> None:
        logger.info(f"Building fingering for song using: {self.agent}")

        previous_notes: Optional[dict[str, list[Note]]] = None
        current_notes: dict[str, list[Note]] = {}

        right_note_groups: list[list[Note]] = self.group_and_flatten_objects(
            self.song.tracks_v2.right, group_size=self.measures_per_prompt
        )
        left_note_groups: list[list[Note]] = self.group_and_flatten_objects(
            self.song.tracks_v2.left, group_size=self.measures_per_prompt
        )
        for right_note_group, left_note_group in tqdm(
            zip(right_note_groups, left_note_groups, strict=False)
        ):
            current_notes = {"right": right_note_group, "left": left_note_group}
            response = self.agent.run(self.hand_size, current_notes, previous_notes)
            for llm_note in response["right"]:
                for note in right_note_group:
                    if note.id == llm_note.id:
                        note.finger = Finger(llm_note.finger)
            for llm_note in response["left"]:
                for note in left_note_group:
                    if note.id == llm_note.id:
                        note.finger = Finger(llm_note.finger)
            previous_notes = current_notes
