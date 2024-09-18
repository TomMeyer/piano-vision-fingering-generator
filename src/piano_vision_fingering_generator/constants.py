import os
from enum import Enum, StrEnum
from pathlib import Path
from typing import Final, Union

import music21 as m21

RIGHT: Final = "right"
LEFT: Final = "left"
HANDS: Final = (RIGHT, LEFT)

StrPath = Union[str, Path, os.PathLike[str]]

ORDINAL_NUMBERS_TO_WORDS: Final = {
    "8th": "eighth",
    "16th": "sixteenth",
    "32nd": "thirtysecond",
    "64th": "sixtyfourth",
    "128th": "onehundredtwentyeighth",
    "256th": "twohundredfiftysixth",
}

COMMON_DURATIONS: Final = [
    m21.duration.Duration(type="whole", dots=0),
    m21.duration.Duration(type="whole", dots=1),
    m21.duration.Duration(type="half", dots=0),
    m21.duration.Duration(type="half", dots=1),
    m21.duration.Duration(type="quarter", dots=0),
    m21.duration.Duration(type="quarter", dots=1),
    m21.duration.Duration(type="eighth", dots=0),
    m21.duration.Duration(type="eighth", dots=1),
    m21.duration.Duration(type="16th", dots=0),
    m21.duration.Duration(type="16th", dots=1),
    m21.duration.Duration(type="32nd", dots=0),
    m21.duration.Duration(type="32nd", dots=1),
    m21.duration.Duration(type="64th", dots=0),
    m21.duration.Duration(type="64th", dots=1),
    m21.duration.Duration(type="128th", dots=0),
    m21.duration.Duration(type="128th", dots=1),
    m21.duration.Duration(type="256th", dots=0),
    m21.duration.Duration(type="256th", dots=1),
]

DURATION_MAP: Final = {float(d.quarterLength): d for d in COMMON_DURATIONS}


def round_duration_to_nearest(
    duration: m21.duration.Duration,
) -> m21.duration.Duration:
    """
    Rounds a duration to the nearest music21 duration.
    """
    closest_duration = min(
        DURATION_MAP.keys(), key=lambda x: abs(x - float(duration.quarterLength))
    )
    matched_duration = DURATION_MAP[closest_duration]
    rounded_duration = m21.duration.Duration(
        type=matched_duration.type, dots=matched_duration.dots
    )
    return rounded_duration


class NoteLengthType(StrEnum):
    WHOLE = "whole"
    HALF = "half"
    QUARTER = "quarter"
    EIGHTH = "eighth"
    SIXTEENTH = "sixteenth"
    THIRTY_SECOND = "thirtysecond"
    SIXTY_FOURTH = "sixtyfourth"
    ONE_HUNDRED_TWENTY_EIGHTH = "onehundredtwentyeighth"
    TWO_HUNDRED_FIFTY_SIXTH = "twohundredfiftysixth"
    DOTTED_WHOLE = "dottedwhole"
    DOTTED_HALF = "dottedhalf"
    DOTTED_QUARTER = "dottedquarter"
    DOTTED_EIGHTH = "dottedeighth"
    DOTTED_SIXTEENTH = "dottedsixteenth"
    DOTTED_THIRTY_SECOND = "dottedthirtysecond"
    DOTTED_SIXY_FOURTH = "dottedsixtyfourth"

    @classmethod
    def from_duration(cls, value: m21.duration.Duration) -> "NoteLengthType":
        name = value.type
        if name in ORDINAL_NUMBERS_TO_WORDS:
            name = ORDINAL_NUMBERS_TO_WORDS[name]

        if value.dots > 0:
            name = "dotted" + value.type
        if name in [v.value for v in cls.__members__.values()]:
            return cls(name)

        # no matches, get the closest match
        closest = round_duration_to_nearest(value)
        name = closest.type
        if name in ORDINAL_NUMBERS_TO_WORDS:
            name = ORDINAL_NUMBERS_TO_WORDS[name]
        if closest.dots > 0:
            name = "dotted" + name
        return cls(name)


class TimeSignature(Enum):
    TWO_TWO = [2, 2]
    TWO_FOUR = [2, 4]
    THREE_FOUR = [3, 4]
    FOUR_FOUR = [4, 4]
    FIVE_FOUR = [5, 4]
    SIX_EIGHT = [6, 8]
    TWELVE_EIGHT = [12, 8]
    NINE_EIGHT = [9, 8]

    @classmethod
    def from_music21(cls, tim_sig: m21.meter.TimeSignature) -> "TimeSignature":
        return cls([tim_sig.numerator, tim_sig.denominator])


class Hand(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"


class Finger(Enum):
    NOT_SET = None
    THUMB = 1
    INDEX = 2
    MIDDLE = 3
    RING = 4
    PINKY = 5


class HandSize(StrEnum):
    EXTRA_EXTRA_SMALL = "XXS"
    EXTRA_SMALL = "XS"
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"
    EXTRA_LARGE = "XL"
    EXTRA_ExTRA_LARGE = "XXL"
