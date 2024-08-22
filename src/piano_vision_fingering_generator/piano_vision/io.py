import json
from pathlib import Path
from piano_vision_fingering_generator.piano_vision.models import PianoVisionSong


def read_piano_vision_json(pv_path: Path) -> PianoVisionSong:
    data = json.loads(pv_path.read_text())
    return PianoVisionSong.model_validate(data)


def save_piano_vision_json(
    song: PianoVisionSong,
    pv_path: Path,
) -> None:
    pv_path.write_text(song.model_dump_json(indent=2, by_alias=True))
