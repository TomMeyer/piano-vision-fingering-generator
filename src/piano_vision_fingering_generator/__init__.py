import logging
from typing import Union

import tqdm
import yaml

from piano_vision_fingering_generator.constants import (
    COMMON_DURATIONS,
    DURATION_MAP,
    LEFT,
    ORDINAL_NUMBERS_TO_WORDS,
    RIGHT,
    Direction,
    Finger,
    Hand,
    HandSize,
    NoteLengthType,
    StrPath,
    TimeSignature,
)
from piano_vision_fingering_generator.generator import PianoVisionSongBuilder
from piano_vision_fingering_generator.io import (
    build_and_save_piano_vision_json,
    build_piano_vision_json,
    compare_piano_vision_json_files,
    read_piano_vision_json,
    save_piano_vision_json,
)
from piano_vision_fingering_generator.models import (
    KeySignature,
    Note,
    PianoVisionMeasure,
    PianoVisionPositionGroup,
    PianoVisionSection,
    PianoVisionSong,
    PianoVisionTechnicalGroup,
    PianoVisionTimeSignature,
    Rest,
    Tempo,
)


class YAMLformatter(logging.Formatter):
    def __init__(self, *arg, **kwargs) -> None:
        yaml.SafeDumper.add_representer(str, self.str_representer)
        super().__init__(*arg, **kwargs)

    COLORS = {
        "DEBUG": "\033[95m",  # Purple
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"  # Reset color

    def str_representer(self, dumper, data):
        # Use block style if the string contains new lines, otherwise use the default
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    def format(self, record):
        if record.levelno != logging.INFO:
            log_record = {
                "level": record.levelname,
                "timestamp": self.formatTime(record, self.datefmt),
                "pathname": f"{record.pathname}:{record.lineno}",
                "logger_name": record.name,
                "function": record.funcName,
                # "threadName": record.threadName,
                # "processName": record.processName,
                "message": record.getMessage(),
            }
        else:
            log_record = {
                "level": record.levelname,
                "timestamp": self.formatTime(record, self.datefmt),
                "message": record.getMessage(),
            }

        msg: str = yaml.safe_dump(log_record, default_flow_style=False, sort_keys=False)
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            msg = f"{color}{msg}{self.RESET}"

        return msg


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.setFormatter(YAMLformatter())

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


logging.basicConfig(
    level=logging.INFO,
)
for handler in logging.getLogger().handlers:
    handler.setFormatter(YAMLformatter())

logging.getLogger("piano_vision_fingering_generator").setLevel(logging.INFO)


def set_logging_level(level: Union[int, str]) -> None:
    logging.getLogger("piano_vision_fingering_generator").setLevel(level)


__all__ = [
    "HandSize",
    "set_logging_level",
    "RIGHT",
    "LEFT",
    "Direction",
    "Finger",
    "Hand",
    "NoteLengthType",
    "TimeSignature",
    "COMMON_DURATIONS",
    "DURATION_MAP",
    "ORDINAL_NUMBERS_TO_WORDS",
    "StrPath",
    "PianoVisionSongBuilder",
    "PianoVisionSong",
    "PianoVisionSection",
    "PianoVisionMeasure",
    "Note",
    "Rest",
    "KeySignature",
    "TimeSignature",
    "Tempo",
    "PianoVisionPositionGroup",
    "PianoVisionTechnicalGroup",
    "PianoVisionTimeSignature",
    "read_piano_vision_json",
    "save_piano_vision_json",
    "build_piano_vision_json",
    "build_and_save_piano_vision_json",
    "compare_piano_vision_json_files",
]
