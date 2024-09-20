import pytest

from piano_vision_fingering_generator.constants import Direction, Hand, TimeSignature
from piano_vision_fingering_generator.models import (
    Finger,
    KeySignature,
    Measure,
    Note,
    NoteLengthType,
    PianoVisionMeasure,
    PianoVisionPositionGroup,
    PianoVisionSection,
    PianoVisionSong,
    PianoVisionTechnicalGroup,
    PianoVisionTimeSignature,
    Rest,
    SupportingTrack,
    SupportingTrackMidi,
    Tempo,
    TracksV2,
    string_to_hand,
)


def test_string_to_hand():
    # Right hand
    assert string_to_hand("r") == Hand.RIGHT
    assert string_to_hand("right") == Hand.RIGHT
    assert string_to_hand("righthand") == Hand.RIGHT
    assert string_to_hand("right_hand") == Hand.RIGHT

    # Left hand
    assert string_to_hand("l") == Hand.LEFT
    assert string_to_hand("left") == Hand.LEFT
    assert string_to_hand("lefthand") == Hand.LEFT
    assert string_to_hand("left_hand") == Hand.LEFT

    # Invalid
    with pytest.raises(ValueError):
        string_to_hand("invalid")


def test_rest_model():
    rest = Rest(time=1.0, noteLengthType=NoteLengthType.QUARTER)
    assert rest.time == 1.0
    assert rest.noteLengthType == NoteLengthType.QUARTER


def test_note_model():
    note = Note(
        note=60,
        durationTicks=480,
        noteOffVelocity=64,
        ticksStart=0,
        velocity=0.8,
        measureBars=1.0,
        duration=1.0,
        noteName="C4",
        octave=4,
        notePitch="C",
        start=0.0,
        end=1.0,
        noteLengthType=NoteLengthType.QUARTER,
        group=1,
        measureInd=1,
        noteMeasureInd=1,
        id="r1",
        finger=Finger.THUMB,
    )
    assert note.note == 60
    assert note.duration_ticks == 480
    assert note.note_off_velocity == 64
    assert note.ticks_start == 0
    assert note.velocity == 0.8
    assert note.measure_bars == 1.0
    assert note.duration == 1.0
    assert note.note_name == "C4"
    assert note.octave == 4
    assert note.note_pitch == "C"
    assert note.start == 0.0
    assert note.end == 1.0
    assert note.note_length_type == NoteLengthType.QUARTER
    assert note.group == 1
    assert note.measure == 1
    assert note.note_measure_ind == 1
    assert note.id == "r1"
    assert note.finger == Finger.THUMB.value


def test_piano_vision_measure_model():
    note = Note(
        note=60,
        durationTicks=480,
        noteOffVelocity=64,
        ticksStart=0,
        velocity=0.8,
        measureBars=1.0,
        duration=1.0,
        noteName="C4",
        octave=4,
        notePitch="C",
        start=0.0,
        end=1.0,
        noteLengthType=NoteLengthType.QUARTER,
        group=1,
        measureInd=1,
        noteMeasureInd=1,
        id="r1",
        finger=Finger.THUMB,
    )
    measure = PianoVisionMeasure(
        direction=Direction.UP,
        time=0.0,
        timeEnd=1.0,
        timeSignature=TimeSignature.FOUR_FOUR,
        notes=[note],
        min=60,
        max=72,
        measureTicksStart=0.0,
        measureTicksEnd=480.0,
        rests=[],
    )
    assert measure.direction == Direction.UP
    assert measure.time == 0.0
    assert measure.time_end == 1.0
    assert measure.time_signature == TimeSignature.FOUR_FOUR.value
    assert measure.notes == [note]
    assert measure.min == 60
    assert measure.max == 72
    assert measure.measure_ticks_start == 0.0
    assert measure.measure_ticks_end == 480.0
    assert measure.rests == []
    assert measure.note_count == 1


def test_tracks_v2_model():
    note = Note(
        note=60,
        durationTicks=480,
        noteOffVelocity=64,
        ticksStart=0,
        velocity=0.8,
        measureBars=1.0,
        duration=1.0,
        noteName="C4",
        octave=4,
        notePitch="C",
        start=0.0,
        end=1.0,
        noteLengthType=NoteLengthType.QUARTER,
        group=1,
        measureInd=1,
        noteMeasureInd=1,
        id="r1",
        finger=Finger.THUMB,
    )
    measure = PianoVisionMeasure(
        direction=Direction.UP,
        time=0.0,
        timeEnd=1.0,
        timeSignature=TimeSignature.FOUR_FOUR,
        notes=[note],
        min=60,
        max=72,
        measureTicksStart=0.0,
        measureTicksEnd=480.0,
        rests=[],
    )
    tracks = TracksV2(right=[measure], left=[measure])
    assert tracks.right == [measure]
    assert tracks.left == [measure]
    assert tracks.all_notes == [note, note]
    assert tracks.right_notes == [note]
    assert tracks.left_notes == [note]
    assert tracks["right"] == [measure]
    assert tracks["left"] == [measure]
    assert tracks.get_note_by_id("right", 1) == note
    assert tracks.get_number_of_measures("right") == 1
    assert tracks.get_number_of_notes("right") == 1


def test_tempo_model():
    tempo = Tempo(bpm=120.0, ticks=480, time=0.0)
    assert tempo.bpm == 120.0
    assert tempo.ticks == 480
    assert tempo.time == 0.0


def test_piano_vision_section_model():
    section = PianoVisionSection(name="Intro", startMeasure=0.0, endMeasure=4.0)
    assert section.name == "Intro"
    assert section.start_measure == 0.0
    assert section.end_measure == 4.0


def test_piano_vision_position_group_model():
    position_group = PianoVisionPositionGroup(
        name="Treble", isTreble=True, startMeasure=0.0, endMeasure=4.0
    )
    assert position_group.name == "Treble"
    assert position_group.is_treble is True
    assert position_group.start_measure == 0.0
    assert position_group.end_measure == 4.0


def test_piano_vision_technical_group_model():
    technical_group = PianoVisionTechnicalGroup(
        name="Arpeggio",
        isTreble=True,
        barType="solid",
        startMeasure=0.0,
        endMeasure=4.0,
    )
    assert technical_group.name == "Arpeggio"
    assert technical_group.is_treble is True
    assert technical_group.bar_type == "solid"
    assert technical_group.start_measure == 0.0
    assert technical_group.end_measure == 4.0


def test_measure_model():
    measure = Measure(
        time=0.0,
        timeSignature=TimeSignature.FOUR_FOUR,
        ticksPerMeasure=480,
        ticksStart=0.0,
        type=2,
        totalTicks=480.0,
    )
    assert measure.time == 0.0
    assert measure.time_signature == TimeSignature.FOUR_FOUR
    assert measure.ticks_per_measure == 480
    assert measure.ticks_start == 0.0
    assert measure.type == 2
    assert measure.total_ticks == 480.0


def test_supporting_track_midi_model():
    midi = SupportingTrackMidi(midi=60, time=0.0, velocity=0.8, duration=1.0)
    assert midi.midi == 60
    assert midi.time == 0.0
    assert midi.velocity == 0.8
    assert midi.duration == 1.0


def test_supporting_track_model():
    midi = SupportingTrackMidi(midi=60, time=0.0, velocity=0.8, duration=1.0)
    track = SupportingTrack(notes=[midi], myInstrument=1, theirInstrument=2)
    assert track.notes == [midi]
    assert track.my_instrument == 1
    assert track.their_instrument == 2


def test_key_signature_model():
    key_signature = KeySignature(key="C", scale="major", ticks=0)
    assert key_signature.key == "C"
    assert key_signature.scale == "major"
    assert key_signature.ticks == 0


def test_piano_vision_time_signature_model():
    time_signature = PianoVisionTimeSignature(
        ticks=0, timeSignature=TimeSignature.FOUR_FOUR, measures=4
    )
    assert time_signature.ticks == 0
    assert time_signature.time_signature == TimeSignature.FOUR_FOUR
    assert time_signature.measures == 4


def test_piano_vision_song_model():
    midi = SupportingTrackMidi(midi=60, time=0.0, velocity=0.8, duration=1.0)
    track = SupportingTrack(notes=[midi], myInstrument=1, theirInstrument=2)
    note = Note(
        note=60,
        durationTicks=480,
        noteOffVelocity=64,
        ticksStart=0,
        velocity=0.8,
        measureBars=1.0,
        duration=1.0,
        noteName="C4",
        octave=4,
        notePitch="C",
        start=0.0,
        end=1.0,
        noteLengthType=NoteLengthType.QUARTER,
        group=1,
        measureInd=1,
        noteMeasureInd=1,
        id="r1",
        finger=Finger.THUMB,
    )
    measure = PianoVisionMeasure(
        direction=Direction.UP,
        time=0.0,
        timeEnd=1.0,
        timeSignature=TimeSignature.FOUR_FOUR,
        notes=[note],
        min=60,
        max=72,
        measureTicksStart=0.0,
        measureTicksEnd=480.0,
        rests=[],
    )
    tracks = TracksV2(right=[measure], left=[measure])
    tempo = Tempo(bpm=120.0, ticks=480, time=0.0)
    key_signature = KeySignature(key="C", scale="major", ticks=0)
    time_signature = PianoVisionTimeSignature(
        ticks=0, timeSignature=TimeSignature.FOUR_FOUR, measures=4
    )
    section = PianoVisionSection(name="Intro", startMeasure=0.0, endMeasure=4.0)
    position_group = PianoVisionPositionGroup(
        name="Treble", isTreble=True, startMeasure=0.0, endMeasure=4.0
    )
    technical_group = PianoVisionTechnicalGroup(
        name="Arpeggio",
        isTreble=True,
        barType="solid",
        startMeasure=0.0,
        endMeasure=4.0,
    )
    measure_obj = Measure(
        time=0.0,
        timeSignature=TimeSignature.FOUR_FOUR,
        ticksPerMeasure=480,
        ticksStart=0.0,
        type=2,
        totalTicks=480.0,
    )
    song = PianoVisionSong(
        supportingTracks=[track],
        start_time=0.0,
        song_length=120.0,
        resolution=480,
        tempos=[tempo],
        keySignatures=[key_signature],
        timeSignatures=[time_signature],
        measures=[measure_obj],
        tracksV2=tracks,
        accompanyingInstruments=[1, 2],
        accompanyingChannels=[1, 2],
        name="Test Song",
        artist="Test Artist",
        accompanyingTracks=None,
        sections=[section],
        positionGroups=[position_group],
        technicalGroups=[technical_group],
        maxSimplification=2,
    )
    assert song.supporting_tracks == [track]
    assert song.start_time == 0.0
    assert song.song_length == 120.0
    assert song.resolution == 480
    assert song.tempos == [tempo]
    assert song.key_signatures == [key_signature]
    assert song.time_signatures == [time_signature]
    assert song.measures == [measure_obj]
    assert song.tracks_v2 == tracks
    assert song.accompanying_instruments == [1, 2]
    assert song.accompanying_channels == [1, 2]
    assert song.name == "Test Song"
    assert song.artist == "Test Artist"
    assert song.accompanying_tracks is None
    assert song.sections == [section]
    assert song.position_groups == [position_group]
    assert song.technical_groups == [technical_group]
    assert song.max_simplification == 2
