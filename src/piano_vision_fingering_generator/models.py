from time import sleep
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
import yaml
from piano_vision_fingering_generator.constants import (
    NoteLengthType,
    TimeSignature,
    Hand,
    Direction,
    Finger,
)
import music21 as m21

HandOrString = Union[Hand, str]


def string_to_hand(hand: str) -> Hand:
    if hand.lower() in ("r", "right", "righthand", "right_hand"):
        hand = "right"
    elif hand.lower() == ("l", "left", "lefthand", "left_hand"):
        hand = "left"
    return Hand(hand)


class Rest(BaseModel):
    time: float
    noteLengthType: NoteLengthType


class Note(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    note: int
    duration_ticks: int = Field(alias="durationTicks")
    note_off_velocity: int = Field(alias="noteOffVelocity")
    ticks_start: int = Field(alias="ticksStart")
    velocity: float
    measure_bars: float = Field(alias="measureBars")
    duration: float
    note_name: str = Field(alias="noteName")
    octave: int
    note_pitch: str = Field(alias="notePitch")
    start: float
    end: float
    note_length_type: NoteLengthType = Field(alias="noteLengthType")
    group: int
    measure: int = Field(alias="measureInd")
    note_measure_ind: int = Field(alias="noteMeasureInd")
    id: str
    finger: Finger
    smp: Optional[str] = None

    def simple_json(self) -> dict[str, Any]:
        return {
            "note": self.note,
            "name": self.note_name,
            "measure": self.measure,
            "finger": self.finger,
        }

    def simple_yaml(self) -> str:
        return yaml.safe_dump(self.simple_json())


class PianoVisionMeasure(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    direction: Direction
    time: float
    time_end: float = Field(alias="timeEnd")
    time_signature: TimeSignature = Field(alias="timeSignature")
    notes: list[Note]
    min: int
    max: int
    measure_ticks_start: float = Field(alias="measureTicksStart")
    measure_ticks_end: float = Field(alias="measureTicksEnd")
    rests: list[Rest]

    @property
    def note_count(self) -> int:
        return len(self.notes)

    def to_measure(self) -> "Measure":
        return Measure(
            time=self.time,
            timeSignature=self.time_signature,
            ticksPerMeasure=int(self.measure_ticks_end - self.measure_ticks_start),
            ticksStart=self.measure_ticks_start,
            totalTicks=self.measure_ticks_end - self.measure_ticks_start,
            type=2,  # TODO: What does type mean? So far I've seen it as 0, 1, 2. Almost always 2.
        )


class TracksV2(BaseModel):
    right: list[PianoVisionMeasure]
    left: list[PianoVisionMeasure]

    @property
    def all_notes(self) -> list[Note]:
        notes: list[Note] = []
        for hand in (Hand.LEFT, Hand.RIGHT):
            for measure in self[hand]:
                notes.extend(measure.notes)
        return notes

    @property
    def right_notes(self) -> list[Note]:
        notes = []
        for measure in self.right:
            notes.extend(measure.notes)
        return notes

    @property
    def left_notes(self) -> list[Note]:
        notes = []
        for measure in self.left:
            notes.extend(measure.notes)
        return notes

    def __getitem__(self, hand: HandOrString) -> list[PianoVisionMeasure]:
        if isinstance(hand, str):
            hand = string_to_hand(hand)
        return getattr(self, hand)

    def get_note_by_id(self, hand: Union[Hand, str], id: int) -> Optional[Note]:
        if isinstance(hand, str):
            hand = string_to_hand(hand)
        id_prefix: str = "r" if hand == Hand.RIGHT else "l"
        for measure in self[hand]:
            for note in measure.notes:
                if note.id == f"{id_prefix}{id}":
                    return note
        return None

    def get_number_of_measures(self, hand: Union[Hand, str]) -> int:
        if isinstance(hand, str):
            hand = string_to_hand(hand)
        return len(self[hand])

    def get_number_of_notes(self, hand: Union[Hand, str]) -> int:
        if isinstance(hand, str):
            hand = string_to_hand(hand)
        return sum(measure.note_count for measure in self[hand])


class Tempo(BaseModel):
    bpm: float
    ticks: int
    time: float


class PianoVisionSection(BaseModel):
    name: str
    start_measure: float = Field(alias="startMeasure")
    end_measure: float = Field("endMeasure")


class PianoVisionPositionGroup(BaseModel):
    name: str
    is_treble: bool = Field(alias="isTreble")
    start_measure: float = Field(alias="startMeasure")
    end_measure: float = Field("endMeasure")


class PianoVisionTechnicalGroup(BaseModel):
    name: str
    is_treble: bool = Field(alias="isTreble")
    bar_type: str = Field(alias="barType")
    start_measure: float = Field(alias="startMeasure")
    end_measure: float = Field("endMeasure")


class Measure(BaseModel):
    time: float
    time_signature: TimeSignature = Field(alias="timeSignature")
    ticks_per_measure: int = Field(alias="ticksPerMeasure")
    ticks_start: float = Field(alias="ticksStart")
    type: int
    total_ticks: float = Field(alias="totalTicks")


class SupportingTrackMidi(BaseModel):
    midi: int
    time: float
    velocity: float
    duration: float


class SupportingTrack(BaseModel):
    notes: list[SupportingTrackMidi]
    my_instrument: int = Field(alias="myInstrument")
    their_instrument: int = Field(alias="theirInstrument")


class KeySignature(BaseModel):
    key: str
    scale: str
    ticks: int


class PianoVisionTimeSignature(BaseModel):
    ticks: int
    time_signature: TimeSignature = Field(alias="timeSignature")
    measures: int


class PianoVisionSong(BaseModel):

    supporting_tracks: list[SupportingTrack] = Field(alias="supportingTracks")
    start_time: float
    song_length: float
    resolution: int
    tempos: list[Tempo]
    key_signatures: list[KeySignature] = Field(alias="keySignatures")
    time_signatures: list[PianoVisionTimeSignature] = Field(alias="timeSignatures")
    measures: list[Measure]
    tracks_v2: TracksV2 = Field(alias="tracksV2")
    accompanying_instruments: list[int] = Field(alias="accompanyingInstruments")
    accompanying_channels: list[int] = Field(alias="accompanyingChannels")
    name: str
    artist: str
    accompanying_tracks: Optional[list[Any]] = Field(
        alias="accompanyingTracks",
        default=None,
    )
    sections: list[PianoVisionSection]
    position_groups: list[PianoVisionPositionGroup] = Field(alias="positionGroups")
    technical_groups: list[PianoVisionTechnicalGroup] = Field(alias="technicalGroups")
    max_simplification: int = Field(alias="maxSimplification")
