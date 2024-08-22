import logging
from pathlib import Path

from tqdm import tqdm
from piano_vision_fingering_generator.constants import Finger
from piano_vision_fingering_generator.midi import generate_piano_fingerings, HandSize
from piano_vision_fingering_generator.midi.generate_fingerings import (
    GeneratedPianoFingerings,
)
from piano_vision_fingering_generator.piano_vision import (
    read_piano_vision_json,
    PianoVisionSong,
)
from piano_vision_fingering_generator.piano_vision.models import (
    PianoVisionMeasure,
)
from piano_vision_fingering_generator.piano_vision import save_piano_vision_json

logger = logging.getLogger(__name__)


def generate_fingerings_and_update_piano_vision_song(
    pv_json_path: Path, midi_path: Path, hand_size: HandSize
) -> PianoVisionSong:
    pv_song: PianoVisionSong = read_piano_vision_json(pv_json_path)
    generated_fingerings: GeneratedPianoFingerings = generate_piano_fingerings(
        midi_path, hand_size
    )
    matched_notes = []
    matched_fingerings = []
    logger.info("Updating song with generated fingerings")
    for fingering in tqdm(generated_fingerings.left, desc="Scanning left fingerings"):
        if fingering.measure is None:
            # logger.warning(f"Fingering {fingering} does not have a measure number")
            continue
        if fingering.finger == Finger.NOT_SET:
            # logger.warning(f"Fingering not set for {fingering.name}")
            continue
        pv_measure: PianoVisionMeasure = pv_song.tracks_v2.left[fingering.measure]
        for pv_note in pv_measure.notes:
            if pv_note in matched_notes:
                continue
            if not pv_note.fingering_matches(fingering):
                continue
            pv_note.finger = fingering.finger
            matched_notes.append(pv_note)
            matched_fingerings.append(fingering)
            break

    for fingering in tqdm(generated_fingerings.right, desc="Scanning right fingerings"):
        if fingering.measure is None:
            logger.error("duplicate")

            # logger.warning(f"Fingering {fingering} does not have a measure number")
            continue
        if fingering.finger == Finger.NOT_SET:
            # logger.warning(f"Fingering not set for {fingering.name}")
            continue

        pv_measure = pv_song.tracks_v2.right[fingering.measure]
        for pv_note in pv_measure.notes:
            if pv_note in matched_notes:
                continue
            if not pv_note.fingering_matches(fingering):
                continue
            pv_note.finger = fingering.finger
            matched_notes.append(pv_note.id)
            matched_fingerings.append(fingering)
            break

    save_piano_vision_json(
        pv_song, pv_json_path.with_stem(f"{pv_json_path.stem}_with_fingerings")
    )
    return pv_song
