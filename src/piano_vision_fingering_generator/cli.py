import argparse
from pathlib import Path
from piano_vision_fingering_generator.constants import HandSize
from piano_vision_fingering_generator.io import build_and_save_piano_vision_json


def build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Piano Vision Fingering Generator")
    parser.add_argument("midi_path", type=Path, help="Path to the MIDI file")
    parser.add_argument(
        "hand_size",
        type=HandSize,
        choices=[h.value.lower() for h in HandSize],
        help="Hand size for the generated fingering",
    )
    # parser.add_argument(
    #     "--right_hand_midi_part_index",
    #     type=int,
    #     default=None,
    #     help="Index of the right hand MIDI part. Will be automatically determined if not specified.",
    # )
    # parser.add_argument(
    #     "--left_hand_midi_part_index",
    #     type=int,
    #     default=None,
    #     help="Index of the left hand MIDI part. Will be automatically determined if not specified.",
    # )
    return parser


def main():
    parser = build_cli()
    options = parser.parse_args()
    build_and_save_piano_vision_json(
        options.midi_path,
        options.hand_size,
    )
