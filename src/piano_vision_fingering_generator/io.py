import json
from pathlib import Path
from piano_vision_fingering_generator.constants import HandSize, StrPath
from piano_vision_fingering_generator.generator import PianoVisionSongBuilder
from piano_vision_fingering_generator.models import PianoVisionSong
import difflib


def read_piano_vision_json(pv_path: StrPath) -> PianoVisionSong:
    pv_path = Path(pv_path)
    data = json.loads(pv_path.read_text())
    # return PianoVisionSong.model_validate_json(pv_path.read_text())
    return PianoVisionSong.model_validate(data)


def save_piano_vision_json(
    song: PianoVisionSong,
    pv_path: StrPath,
    indent: int = 2,
) -> None:
    pv_path = Path(pv_path)
    pv_path.write_text(song.model_dump_json(indent=indent, by_alias=True))


def build_piano_vision_json(
    midi_path: StrPath,
    hand_size: HandSize,
    right_hand_midi_part_index: int = 0,
    left_hand_midi_part_index: int = 1,
) -> PianoVisionSong:
    midi_path = Path(midi_path)
    builder = PianoVisionSongBuilder(midi_path, hand_size)
    return builder.build()


def build_and_save_piano_vision_json(midi_path: StrPath, hand_size: HandSize):
    midi_path = Path(midi_path)
    builder = PianoVisionSongBuilder(midi_path, hand_size)
    song = builder.build()
    outpath = midi_path.with_name(f"{midi_path.stem}_piano_vision.json")
    save_piano_vision_json(song, outpath)


def compare_piano_vision_json_files(pv_path1: StrPath, pv_path2: StrPath):
    pv_path1 = Path(pv_path1)
    pv_path2 = Path(pv_path2)
    song1 = read_piano_vision_json(pv_path1)
    song2 = read_piano_vision_json(pv_path2)
    song_1_data = song1.model_dump_json(by_alias=True, indent=2).strip().splitlines()
    song_2_data = song2.model_dump_json(by_alias=True, indent=2).strip().splitlines()
    output_data = []
    for line in difflib.unified_diff(song_1_data, song_2_data):
        output_data.append(line)
    output_path = Path(f"{pv_path1.stem}_diff_{pv_path2.stem}.diff")
    output_path.write_text("\n".join(output_data))
