import music21
import pytest
from music21.stream.base import Measure, Score

from piano_vision_fingering_generator.constants import TimeSignature
from piano_vision_fingering_generator.generator import (
    MetronomeWithBoundaries,
    PianoVisionKeySignatureBuilder,
    PianoVisionMeasureBuilder,
    PianoVisionSongLengthBuilder,
    PianoVisionSupportingTracksBuilder,
    PianoVisionTempoBuilder,
    PianoVisionTimeSignatureBuilder,
    SongDurationFixer,
    SongPartMixin,
    SongTimeSignatureFixer,
)


@pytest.fixture
def measure_with_notes():
    def _measure_with_notes(num_notes: int) -> Measure:
        measure = music21.stream.Measure()
        note = music21.note.Note(nameWithOctave="C4")
        measure.repeatAppend(note, num_notes)
        return measure

    return _measure_with_notes


@pytest.fixture
def basic_score(measure_with_notes) -> Score:
    score = music21.stream.Score()
    part1 = music21.stream.Part()
    part1.append(music21.key.KeySignature(0))
    part1.append(music21.clef.TrebleClef())
    part1.append(music21.tempo.MetronomeMark(number=104))

    part2 = music21.stream.Part()
    part2.append(music21.clef.BassClef())

    for i in range(4):  # Create 4 measures for part1
        measure = measure_with_notes(2)
        measure.number = i + 1
        part1.append(measure)

    for i in range(5):  # Create 5 measures for part2
        measure = measure_with_notes(2)  # Use measure_with_notes fixture
        measure.number = i + 1
        part2.append(measure)

    if m1 := part1.measure(1):
        m1.insert(0, music21.meter.TimeSignature("3/4"))

    score.append(part1)
    score.append(part2)
    return score


def test_song_part_mixin(basic_score: music21.stream.Score):
    mixin = SongPartMixin(
        m21_song=basic_score, right_hand_part_index=None, left_hand_part_index=None
    )
    assert mixin.right_hand_part_index is None
    assert mixin.left_hand_part_index is None

    assert mixin.right_hand_part == basic_score.parts[0]
    assert mixin.left_hand_part == basic_score.parts[1]

    assert mixin.right_hand_part_index == 0
    assert mixin.left_hand_part_index == 1


def test_duration_fixer(basic_score: music21.stream.Score):
    fixer = SongDurationFixer(m21_song=basic_score)
    right_hand_measure_count = len(fixer.right_hand_part.measures(0, None))
    left_hand_measure_count = len(fixer.left_hand_part.measures(0, None))
    assert right_hand_measure_count != left_hand_measure_count
    fixer.run()
    right_hand_measure_count = len(fixer.right_hand_part.measures(0, None))
    left_hand_measure_count = len(fixer.left_hand_part.measures(0, None))
    assert right_hand_measure_count == left_hand_measure_count


def test_time_signature_fixer(basic_score: music21.stream.Score):
    fixer = SongTimeSignatureFixer(m21_song=basic_score)
    assert fixer.check_if_clean_is_needed()
    assert fixer.right_hand_part.getTimeSignatures()[0].ratioString == "3/4"
    assert fixer.left_hand_part.getTimeSignatures()[0].ratioString == "4/4"

    fixer.run()
    assert fixer.right_hand_part.getTimeSignatures()[0].ratioString == "3/4"
    assert fixer.left_hand_part.getTimeSignatures()[0].ratioString == "3/4"


def test_metronome_with_boundaries():
    metronome = music21.tempo.MetronomeMark(number=120)
    boundaries = MetronomeWithBoundaries(metronome, 0, 10)
    assert boundaries.in_bounds(5)
    assert not boundaries.in_bounds(15)


def test_tempo_builder(basic_score: music21.stream.Score):
    builder = PianoVisionTempoBuilder(m21_song=basic_score)
    tempos = builder.build()
    assert len(tempos) == 1
    assert tempos[0].bpm == 104.0


def test_key_signature_builder(basic_score):
    builder = PianoVisionKeySignatureBuilder(m21_song=basic_score)
    key_signatures = builder.build()
    assert len(key_signatures) == 1


def test_measure_builder(basic_score: music21.stream.Score):
    SongTimeSignatureFixer(m21_song=basic_score).run()
    builder = PianoVisionMeasureBuilder(m21_song=basic_score)
    measures = builder.build()
    assert len(measures.right) == 3
    assert len(measures.left) == 4
    SongDurationFixer(m21_song=basic_score).run()
    measures = builder.build()
    assert len(measures.right) == 4
    assert len(measures.left) == 4


def test_supporting_tracks_builder(basic_score: music21.stream.Score):
    builder = PianoVisionSupportingTracksBuilder(m21_song=basic_score)
    tracks = builder.build()
    assert len(tracks) == 2


def test_time_signature_builder(basic_score: music21.stream.Score):
    SongTimeSignatureFixer(m21_song=basic_score).run()
    SongDurationFixer(m21_song=basic_score).run()
    builder = PianoVisionTimeSignatureBuilder(m21_song=basic_score)
    time_signatures = builder.build()
    assert len(time_signatures) == 2
    assert time_signatures[0].time_signature == TimeSignature.THREE_FOUR
    assert time_signatures[1].time_signature == TimeSignature.THREE_FOUR


def test_song_length_builder(basic_score: music21.stream.Score):
    builder = PianoVisionSongLengthBuilder(m21_song=basic_score)
    length = builder.build()
    assert length > 0


# def test_piano_vision_song_builder():
#     builder = PianoVisionSongBuilder(midi_path="path/to/midi")
#     song = builder.build()
#     assert song.name == builder.song_name
#     assert song.artist == builder.song_author
