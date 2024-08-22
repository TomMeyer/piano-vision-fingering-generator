import logging
from typing import Optional, TypeGuard, Union
from music21 import converter, note, articulations, chord
from pathlib import Path
from pianoplayer.scorereader import reader
from pianoplayer.hand import Hand
from piano_vision_fingering_generator.constants import (
    HandSize,
    Hand as Chirality,
    Finger,
    NoteLengthType,
)
from tqdm import tqdm
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class PianoFingering(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    name: str
    hand: Chirality
    finger: Finger
    offset: float
    id: Union[int, str]
    duration: str
    measure: Optional[int] = None

    @classmethod
    def from_music21_note(cls, note: note.Note, hand: Chirality) -> "PianoFingering":
        if note.measureNumber is not None:
            measure_number = note.measureNumber - 1
        if measure_number is None:
            raise ValueError("Note does not have a measure number")
        if note.duration.type == "complex":
            breakpoint()
        for articulation in note.articulations:
            if isinstance(articulation, articulations.Fingering):
                return cls(
                    name=note.nameWithOctave,
                    hand=hand,
                    finger=Finger(articulation.fingerNumber),
                    measure=measure_number,
                    offset=float(note.offset),
                    duration=note.duration.type,
                    id=note.id,
                )
        logger.warn(f"No fingering found for {note.nameWithOctave}")
        return cls(
            name=note.nameWithOctave,
            hand=hand,
            finger=Finger.NOT_SET,
            measure=measure_number,
            offset=float(note.offset),
            duration=note.duration.type,
            id=note.id,
        )


class GeneratedPianoFingerings(BaseModel):
    left: list[PianoFingering]
    right: list[PianoFingering]

    @property
    def all(self) -> list[PianoFingering]:
        return self.left + self.right

    @classmethod
    def from_piano_fingerings(
        cls, fingerings: list[PianoFingering]
    ) -> "GeneratedPianoFingerings":
        left: list[PianoFingering] = []
        right: list[PianoFingering] = []
        for f in fingerings:
            if f.hand == Chirality.LEFT:
                left.append(f)
            else:
                right.append(f)
        return cls(left=left, right=right)


def is_note(obj: note.GeneralNote) -> TypeGuard[note.Note]:
    return obj.isNote


def is_chord(obj: note.GeneralNote) -> TypeGuard[chord.Chord]:
    return obj.isChord


def is_rest(obj: note.GeneralNote) -> TypeGuard[note.Rest]:
    return obj.isRest


def generate_piano_fingerings(
    midi_path: Path, hand_size: HandSize, verbose: bool = True
) -> GeneratedPianoFingerings:
    midi = converter.parse(midi_path)
    fingerings: list[PianoFingering] = []
    rhand = Hand("right", hand_size)
    rhand.verbose = verbose
    rhand.noteseq = reader(midi, beam=0)
    lhand = Hand("left", hand_size)
    lhand.verbose = verbose
    lhand.noteseq = reader(midi, beam=1)
    logger.info("Generating left hand fingerings")
    lhand.generate()
    logger.info("Generating right hand fingerings")
    rhand.generate()
    # midi.write("musicxml", "./data/output.xml")
    fingerings: list[PianoFingering] = []
    measures_seen = set()
    for i, part in tqdm(enumerate(midi.parts), desc="Song Parts"):
        chirality: Chirality = Chirality.RIGHT if i == 0 else Chirality.LEFT
        for n in tqdm(part.flatten().notes, desc="Notes"):
            measures_seen.add(n.measureNumber)
            if is_note(n):
                piano_fingering: PianoFingering = PianoFingering.from_music21_note(
                    n,
                    chirality,
                )
                fingerings.append(piano_fingering)
            elif is_chord(n):
                # Chords store fingerings in the chord articulations and not the individual notes
                chord_fingerings: list[articulations.Fingering] = [
                    art
                    for art in n.articulations
                    if isinstance(art, articulations.Fingering)
                ]
                if len(chord_fingerings) != len(n.notes):
                    logger.warn(
                        f"Chord {n} has {len(n.notes)} notes but {len(chord_fingerings)} fingerings"
                    )
                    raise ValueError(
                        "number of chord notes and fingerings do not match"
                    )
                # Assign each note in the chord the corresponding fingering
                for chord_note, articulation in zip(n.notes, chord_fingerings):
                    logger.debug(
                        f"note: {chord_note.nameWithOctave} finger: {articulation.fingerNumber}"
                    )
                    piano_fingering: PianoFingering = PianoFingering(
                        name=chord_note.nameWithOctave,
                        hand=chirality,
                        finger=Finger(articulation.fingerNumber),
                        measure=n.measureNumber,
                        id=chord_note.id,
                        offset=float(chord_note.offset),
                        duration=chord_note.duration.type,
                    )
                    fingerings.append(piano_fingering)
            else:
                logger.warn(f"Unhandled note type: {type(n)}")
    print(f"Measures seen: {measures_seen}")
    return GeneratedPianoFingerings.from_piano_fingerings(fingerings)
