import logging
from typing import Union
import yaml
import piano_vision_fingering_generator.piano_vision as piano_vision
from piano_vision_fingering_generator.midi import generate_piano_fingerings, HandSize
from piano_vision_fingering_generator.main import (
    generate_fingerings_and_update_piano_vision_song,
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
                "message": record.msg,
            }
        else:
            log_record = {
                "level": record.levelname,
                "timestamp": self.formatTime(record, self.datefmt),
                "message": record.msg,
            }

        msg: str = yaml.safe_dump(log_record, default_flow_style=False, sort_keys=False)
        if record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            msg = f"{color}{msg}{self.RESET}"

        return msg


logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
for handler in logging.getLogger().handlers:
    handler.setFormatter(YAMLformatter())


def set_logging_level(level: Union[int, str]) -> None:
    logging.getLogger().setLevel(level)


__all__ = [
    "piano_vision",
    "generate_piano_fingerings",
    "HandSize",
    "set_logging_level",
    "generate_fingerings_and_update_piano_vision_song",
]
