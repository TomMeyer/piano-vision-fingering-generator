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
        choices=[h.value for h in HandSize],
        help="Hand size for the generated fingering",
    )

    return parser


def main():
    parser = build_cli()
    options = parser.parse_args()
    print(options)
    build_and_save_piano_vision_json(
        options.midi_path,
        options.hand_size,
    )
