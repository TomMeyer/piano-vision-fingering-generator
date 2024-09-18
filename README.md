![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FTomMeyer%2Fpiano-vision-fingering-generator%2Fmain%2Fpyproject.toml&style=flat-square) 
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/TomMeyer/piano-vision-fingering-generator/main.svg)](https://results.pre-commit.ci/latest/github/TomMeyer/piano-vision-fingering-generator/main)


# piano-vision-fingering-generator

Generate a PianoVision song file with fingerings from a MIDI file.

The generation can be done in the following ways:
- depth based search using PianoPlayer (default)
- response from an LLM model (LLama 3.1)

## Usage

### CLI 

```
usage: pv-fingering-generator [-h] [--ai] [--right-hand-midi-part-index RIGHT_HAND_MIDI_PART_INDEX] [--left-hand-midi-part-index LEFT_HAND_MIDI_PART_INDEX] [--verbose] midi_path {XXS,XS,S,M,L,XL,XXL}
Piano Vision Fingering Generator

positional arguments:
  midi_path             Path to the MIDI file
  {XXS,XS,S,M,L,XL,XXL}
                        Hand size for the generated fingering

options:
  -h, --help            show this help message and exit
  --ai                  Use the AI model to generate the fingerings
  --right-hand-midi-part-index RIGHT_HAND_MIDI_PART_INDEX
                        Index of the right hand MIDI part
  --left-hand-midi-part-index LEFT_HAND_MIDI_PART_INDEX
                        Index of the left hand MIDI part
  --verbose, -v
```
#### Example
```bash
pv-fingering-generator "path/to/midi/file.mid" M
pv-fingering-generator "path/to/midi/file.mid" M --ai -v
```

## Acknowledgements

Uses [PianoPlayer by marcomusy](https://github.com/marcomusy/pianoplayer) to generate piano fingerings.
