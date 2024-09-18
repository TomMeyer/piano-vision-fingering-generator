import argparse
from pathlib import Path

from piano_vision_fingering_generator import set_logging_level
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
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Use the AI model to generate the fingerings",
    )
    parser.add_argument(
        "--right-hand-midi-part-index",
        type=int,
        help="Index of the right hand MIDI part",
        default=None,
    )
    parser.add_argument(
        "--left-hand-midi-part-index",
        type=int,
        help="Index of the left hand MIDI part",
        default=None,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
    )
    parser.add_help = True
    return parser


def main():
    parser = build_cli()
    options = parser.parse_args()
    print(options)
    if options.verbose:
        set_logging_level("DEBUG")
    build_and_save_piano_vision_json(
        midi_path=options.midi_path,
        hand_size=options.hand_size,
        left_hand_midi_part_index=options.left_hand_midi_part_index,
        right_hand_midi_part_index=options.right_hand_midi_part_index,
        ai=options.ai,
    )
