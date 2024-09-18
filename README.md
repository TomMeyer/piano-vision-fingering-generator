[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/TomMeyer/piano-vision-fingering-generator/main.svg)](https://results.pre-commit.ci/latest/github/TomMeyer/piano-vision-fingering-generator/main)


# piano-vision-fingering-generator

Generate a PianoVision song file with fingerings from a MIDI file.

## Usage

### CLI 

`pv-fingering-generator [-h] midi_path {XXS,XS,S,M,L,XL,XXL}`

```bash
pv-fingering-generator <midi_file> <hand_size>
```

#### Example
```bash
pv-fingering-generator "path/to/midi/file.mid" M
```

## Acknowledgements

Uses [PianoPlayer by marcomusy](https://github.com/marcomusy/pianoplayer) to generate piano fingerings.
