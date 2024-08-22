from enum import Enum, StrEnum

import music21


class NoteLengthType(StrEnum):
    WHOLE = "whole"
    HALF = "half"
    QUARTER = "quarter"
    EIGHTH = "eighth"
    SIXTEENTH = "sixteenth"
    THIRTY_SECOND = "thirtysecond"
    SIXTY_FOURTH = "sixtyfourth"
    DOTTED_WHOLE = "dottedwhole"
    DOTTED_HALF = "dottedhalf"
    DOTTED_QUARTER = "dottedquarter"
    DOTTED_EIGHTH = "dottedeighth"
    DOTTED_SIXTEENTH = "dottedsixteenth"
    DOTTED_THIRTY_SECOND = "dottedthirtysecond"
    DOTTED_SIXY_FOURTH = "dottedsixtyfourth"
    COMPLEX = "complex"

    @classmethod
    def _missing_(cls, value: str) -> "NoteLengthType":
        if value == "16th":
            return cls.SIXTEENTH
        return super()._missing_(value)


class TimeSignature(Enum):
    TWO_FOUR = [2, 4]
    THREE_FOUR = [3, 4]
    FOUR_FOUR = [4, 4]
    FIVE_FOUR = [5, 4]
    SIX_EIGHT = [6, 8]
    TWELVE_EIGHT = [12, 8]

    @classmethod
    def from_music21(cls, tim_sig: music21.meter.TimeSignature) -> "TimeSignature":
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
