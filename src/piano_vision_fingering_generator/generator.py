import logging
import multiprocessing
import multiprocessing.pool
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Optional, cast

import music21 as m21
import pianoplayer
import pianoplayer.hand
import pianoplayer.scorereader
from music21 import converter
from tqdm.auto import tqdm

from piano_vision_fingering_generator.ai import PianoVisionFingeringGeneratorAI
from piano_vision_fingering_generator.constants import (
    LEFT,
    RIGHT,
    Finger,
    Hand,
    HandSize,
    NoteLengthType,
    StrPath,
    TimeSignature,
    round_duration_to_nearest,
)
from piano_vision_fingering_generator.models import (
    Direction,
    KeySignature,
    Note,
    PianoVisionMeasure,
    PianoVisionSection,
    PianoVisionSong,
    PianoVisionTimeSignature,
    Rest,
    SupportingTrack,
    SupportingTrackMidi,
    Tempo,
    TracksV2,
)

logger = logging.getLogger(__name__)


@dataclass
class SongPartMixin:
    m21_song: Optional[m21.stream.Score] = None
    right_hand_part_index: Optional[int] = None
    left_hand_part_index: Optional[int] = None

    @property
    def right_hand_part(self) -> m21.stream.Part:
        if self.right_hand_part_index is None:
            self._find_part_index()
        if self.right_hand_part_index is None:
            raise ValueError("Right hand part index not found")
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        return self.m21_song.parts[self.right_hand_part_index]

    @property
    def left_hand_part(self) -> m21.stream.Part:
        if self.left_hand_part_index is None:
            self._find_part_index()
        if self.left_hand_part_index is None:
            raise ValueError("Left hand part index not found")
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        return self.m21_song.parts[self.left_hand_part_index]

    def _find_part_index(self):
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        if self.right_hand_part_index is None:
            try:
                treble_clef = (
                    self.m21_song.recurse()
                    .getElementsByClass(m21.clef.TrebleClef)
                    .first()
                )
                treble_clef = cast(m21.clef.TrebleClef, treble_clef)
                rh_part = treble_clef.getContextByClass(m21.stream.Part)
                rh_index = self.m21_song.parts.parts.index(rh_part)
                self.right_hand_part_index = rh_index
                logger.info(f"Right hand part index found: {rh_index}")
            except Exception as e:
                logger.error(
                    f"Error finding right hand part index, defaulting to 0: {e}"
                )
                self.right_hand_part_index = 0
        if self.left_hand_part_index is None:
            try:
                bass_clef = (
                    self.m21_song.recurse()
                    .getElementsByClass(m21.clef.BassClef)
                    .first()
                )
                bass_clef = cast(m21.clef.BassClef, bass_clef)
                lh_part = bass_clef.getContextByClass(m21.stream.Part)
                lh_index = self.m21_song.parts.parts.index(lh_part)
                self.left_hand_part_index = lh_index
                logger.info(f"Left hand part index found: {lh_index}")
            except Exception as e:
                logger.error(
                    f"Error finding left hand part index, defaulting to 1: {e}"
                )
                self.left_hand_part_index = 1


@dataclass
class SongTimeSignatureFixer(SongPartMixin):
    part_index_to_clean: Optional[int] = field(init=False, default=None)
    part_index_to_source: Optional[int] = field(init=False, default=None)

    def run(self) -> None:
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        clean_needed = self.check_if_clean_is_needed()
        if not clean_needed:
            return
        logger.info("Cleaning time signatures is needed")
        if self.part_index_to_clean is None:
            raise ValueError("Part index to clean not found")
        if self.part_index_to_source is None:
            raise ValueError("Part index to source not found")
        part_to_clean = self.m21_song.parts[self.part_index_to_clean]
        part_to_source = self.m21_song.parts[self.part_index_to_source]
        self.change_time_signature_for_part(part_to_clean, part_to_source)

    def is_default_time_signature(self, time_sig: m21.meter.TimeSignature) -> bool:
        return time_sig.ratioString == "4/4"

    def check_if_clean_is_needed(self) -> bool:
        clean_needed: bool = False
        left_time_sigs: list[m21.meter.TimeSignature] = (
            self.left_hand_part.getTimeSignatures()
        )
        right_time_sigs: list[m21.meter.TimeSignature] = (
            self.right_hand_part.getTimeSignatures()
        )

        all_default_right_time_sigs = all(
            self.is_default_time_signature(ts) for ts in right_time_sigs
        )
        all_default_left_time_sigs = all(
            self.is_default_time_signature(ts) for ts in left_time_sigs
        )

        if all_default_left_time_sigs and not all_default_right_time_sigs:
            self.part_index_to_clean = self.left_hand_part_index
            self.part_index_to_source = self.right_hand_part_index
            clean_needed = True

        if not all_default_left_time_sigs and all_default_right_time_sigs:
            self.part_index_to_clean = self.right_hand_part_index
            self.part_index_to_source = self.left_hand_part_index
            clean_needed = True

        return clean_needed

    def change_time_signature_for_part(
        self, target_part: m21.stream.Part, source_part: m21.stream.Part
    ) -> None:
        source_part_measures_count = len(source_part.measures(0, None))
        original_target_part_measures_count = len(target_part.measures(0, None))

        for ts in source_part.getTimeSignatures():
            target_part.insert(ts.offset, ts)
        target_part.makeMeasures(inPlace=True)
        source_part.makeMeasures(inPlace=True)

        new_target_part_measures_count = len(target_part.measures(0, None))
        self.align_bpms(target_part, source_part)
        target_part.makeMeasures(inPlace=True)
        source_part.makeMeasures(inPlace=True)
        if new_target_part_measures_count != source_part_measures_count:
            self.try_remove_final_measure(target_part)
            new_target_part_measures_count = len(target_part.measures(0, None))
        # self.m21_song.makeMeasures(inPlace=True)
        target_part.makeMeasures(inPlace=True)
        source_part.makeMeasures(inPlace=True)
        logger.info(
            (
                f"source measure count: {source_part_measures_count}\n"
                f"target measure count: {original_target_part_measures_count}\n"
                f"new target measures count: {new_target_part_measures_count}"
            )
        )

    def try_remove_final_measure(self, part: m21.stream.Part):
        last_measure = part.measure(-1)
        if not last_measure:
            raise ValueError("No last measure found")
        if not all(el.isRest for el in last_measure.notesAndRests):
            logger.info(
                "different number of note containing measures in the source and "
                "target parts, post-cleaning"
            )
            return
        part.remove(last_measure)

    def align_bpms(
        self, target_part: m21.stream.Part, source_part: m21.stream.Part
    ) -> None:
        for measure in source_part.measures(0, None):
            target_measure = target_part.measure(measure.measureNumber)
            if not target_measure:
                raise ValueError(
                    f"No measure {measure.measureNumber} found for target part"
                )
            for metronome in measure.getElementsByClass(m21.tempo.MetronomeMark):
                target_measure.insert(metronome.offset, metronome)

    def align_durations(
        self, target_part: m21.stream.Part, source_part: m21.stream.Part
    ):
        for measure in source_part.measures(0, None):
            target_measure = target_part.measure(measure.measureNumber)
            if not target_measure:
                raise ValueError(f"No measure {measure.measureNumber} found")


@dataclass
class MetronomeGetterMixin(SongPartMixin):
    right_hand_metronomes: list["MetronomeWithBoundaries"] = field(
        default_factory=list, init=False
    )
    left_hand_metronomes: list["MetronomeWithBoundaries"] = field(
        default_factory=list, init=False
    )

    def __post_init__(self):
        for metronome_data in self.right_hand_part.metronomeMarkBoundaries():
            self.right_hand_metronomes.append(
                MetronomeWithBoundaries(
                    metronome_data[2], metronome_data[0], metronome_data[1]
                )
            )
        for metronome_data in self.left_hand_part.metronomeMarkBoundaries():
            self.left_hand_metronomes.append(
                MetronomeWithBoundaries(
                    metronome_data[2], metronome_data[0], metronome_data[1]
                )
            )

    @property
    def right_metronome_tempos(self) -> list[float]:
        return [metronome.metronome.number for metronome in self.right_hand_metronomes]

    @property
    def left_metronome_tempos(self) -> list[float]:
        return [metronome.metronome.number for metronome in self.left_hand_metronomes]

    def get_metronome_for_offset(
        self, offset: m21.common.OffsetQL, hand: Hand
    ) -> "MetronomeWithBoundaries":
        offset = float(offset)
        if hand == Hand.RIGHT:
            if len(self.right_hand_metronomes) == 1:
                return self.right_hand_metronomes[0]
            for metronome in self.right_hand_metronomes:
                if metronome.in_bounds(offset):
                    return metronome
        elif hand == Hand.LEFT:
            if len(self.left_hand_metronomes) == 1:
                return self.left_hand_metronomes[0]
            for metronome in self.left_hand_metronomes:
                if metronome.in_bounds(offset):
                    return metronome
        raise ValueError(f"No metronome found for offset {offset}")


@dataclass
class SongDurationFixer(MetronomeGetterMixin):
    def run(self) -> None:  # sourcery skip: remove-redundant-if
        left_measure_count = len(self.left_hand_part.measures(0, None))
        right_measure_count = len(self.right_hand_part.measures(0, None))
        measure_count = max(left_measure_count, right_measure_count)

        for i in range(measure_count + 1):
            rh_m = self.right_hand_part.measure(i)
            lh_m = self.left_hand_part.measure(i)
            generated_measure = False
            if rh_m is None and lh_m is None:
                continue
            elif rh_m is None and lh_m is not None:
                rh_m = m21.stream.Measure()
                rh_m.number = i
                rh_m.duration = lh_m.duration
                self.right_hand_part.append(rh_m)
                generated_measure = True
            elif lh_m is None and rh_m is not None:
                lh_m = m21.stream.Measure()
                lh_m.duration = rh_m.duration
                self.left_hand_part.append(lh_m)
                generated_measure = True
            if rh_m is None:
                raise ValueError("Right hand measure is None")
            if lh_m is None:
                raise ValueError("Left hand measure is None")
            durations_match = rh_m.duration.quarterLength == lh_m.duration.quarterLength
            if not generated_measure and durations_match:
                continue
            if rh_m is None:
                raise ValueError("One of the measures is None")
            logger.info(f"Fixing measure duration for measure {rh_m.number}")
            self.fix_measure_duration(rh_m, lh_m)

    def fix_measure_duration(self, m1: m21.stream.Measure, m2: m21.stream.Measure):
        if m1.duration.quarterLength > m2.duration.quarterLength:
            target = m2
            source = m1
        elif m1.duration.quarterLength < m2.duration.quarterLength:
            target = m1
            source = m2
        elif len(m1.notesAndRests) == 0 and len(m2.notesAndRests) > 0:
            target = m1
            source = m2
        elif len(m2.notesAndRests) == 0 and len(m1.notesAndRests) > 0:
            target = m2
            source = m1
        else:
            return

        target.duration = m21.duration.Duration(source.duration.quarterLength)
        rest_duration = abs(
            source.duration.quarterLength - target.duration.quarterLength
        )
        if len(target.notesAndRests) == 0:
            rest_duration = target.duration.quarterLength
        rest = m21.note.Rest(rest_duration)

        target.append(rest)


@dataclass
class PianoVisionSongBuilder(SongPartMixin):
    midi_path: InitVar[StrPath] = ""
    hand_size: HandSize = HandSize.MEDIUM
    sections: list[PianoVisionSection] = field(default_factory=list)
    ai: bool = False
    _fingerings_generated: bool = field(init=False, default=False)

    def __post_init__(self, midi_path: StrPath) -> None:
        if not midi_path:
            raise ValueError(f"No MIDI path provided {midi_path}")
        self.midi_song_path: Path = Path(midi_path)
        song = converter.parse(self.midi_song_path)
        if not isinstance(song, m21.stream.Score):
            raise ValueError("Only scores are supported")
        self.m21_song = song
        self._find_part_index()
        self.m21_song.stripTies(inPlace=True)
        self.m21_song.makeMeasures(inPlace=True)
        for part in self.m21_song.parts:
            part.makeBeams(inPlace=True)
        SongTimeSignatureFixer(
            self.m21_song,
            right_hand_part_index=self.right_hand_part_index,
            left_hand_part_index=self.left_hand_part_index,
        ).run()
        SongDurationFixer(
            self.m21_song,
            right_hand_part_index=self.right_hand_part_index,
            left_hand_part_index=self.left_hand_part_index,
        ).run()
        self.strip_empty_trailing_measures()

    def strip_empty_trailing_measures(self):
        if self.m21_song is None:
            raise ValueError("No music21 song found")

        rm = self.right_hand_part.measure(-1)
        if rm is None:
            raise ValueError("No last measure found for right hand")
        if rm.duration.quarterLength == 0:
            self.right_hand_part.remove(rm)
        lm = self.left_hand_part.measure(-1)
        if lm is None:
            raise ValueError("No last measure found for left hand")
        if lm.duration.quarterLength == 0:
            self.left_hand_part.remove(lm)

    @cached_property
    def song_name(self) -> str:
        """
        Try to get the name from the metadata of the song.

        If it is not available, returns the name of the MIDI file
        with dashes and underscores replaced with spaces.
        """
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        name = self.m21_song.metadata.title
        if not name:
            name = self.midi_song_path.stem
            name = name.replace("_", " ")
            name = name.replace("-", " ")
        return name

    @property
    def song_author(self) -> str:
        """
        Try to get the author from the metadata of the song.
        If it is not available, returns "AUTHOR MISSING"

        TODO: How else can we get the author?
        """
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        try:
            author = self.m21_song.metadata.author
        except AttributeError:
            author = "AUTHOR MISSING"
        return author

    @cached_property
    def song_resolution(self) -> int:
        """
        Reads the MIDI file directly to get the ticks per quarter note.
        """
        mf = m21.midi.MidiFile()
        mf.open(str(self.midi_song_path))
        mf.read()
        midi_song_ticks_per_quarter_note = int(mf.ticksPerQuarterNote)
        mf.close()
        return midi_song_ticks_per_quarter_note

    def _add_fingerings_to_music21(self) -> None:
        """
        Uses marcomusy/pianoplayer library to generate fingerings
        for the song and add them to the midi song.
        """
        if self._fingerings_generated:
            return
        if self.right_hand_part_index is None:
            raise ValueError("Right hand part index not found")
        if self.left_hand_part_index is None:
            raise ValueError("Left hand part index not found")
        rhand = pianoplayer.hand.Hand(RIGHT, self.hand_size.value)
        rhand.noteseq = pianoplayer.scorereader.reader(
            self.m21_song, beam=self.right_hand_part_index
        )
        rhand.verbose = False
        rhand.generate()
        lhand = pianoplayer.hand.Hand(LEFT, self.hand_size.value)
        lhand.verbose = False
        lhand.noteseq = pianoplayer.scorereader.reader(
            self.m21_song, beam=self.left_hand_part_index
        )
        lhand.generate()
        self._fingerings_generated = True

    def build(self) -> PianoVisionSong:
        """
        Main method to build the PianoVisionSong object from the MIDI file.
        """
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        if not self.ai:
            self._add_fingerings_to_music21()

        with tqdm(total=6) as pbar:
            logger.info("Building PianoVisionSong")
            tracks_v2 = PianoVisionMeasureBuilder(
                self.m21_song,
                ticks_per_quarter=self.song_resolution,
                left_hand_part_index=self.left_hand_part_index,
                right_hand_part_index=self.right_hand_part_index,
            ).build()
            pbar.update(1)
            tempos = PianoVisionTempoBuilder(
                self.m21_song, self.song_resolution
            ).build()
            pbar.update(1)
            key_signatures = PianoVisionKeySignatureBuilder(
                self.m21_song, self.song_resolution
            ).build()
            pbar.update(1)
            song_length = PianoVisionSongLengthBuilder(self.m21_song).build()
            pbar.update(1)
            supporting_tracks = PianoVisionSupportingTracksBuilder(
                self.m21_song,
                right_hand_part_index=self.right_hand_part_index,
                left_hand_part_index=self.left_hand_part_index,
            ).build()
            pbar.update(1)
            time_signatures = PianoVisionTimeSignatureBuilder(
                self.m21_song,
                right_hand_part_index=self.right_hand_part_index,
                left_hand_part_index=self.left_hand_part_index,
            ).build()
            pbar.update(1)

        logger.info("finished building PianoVisionSong")
        song = PianoVisionSong(
            name=self.song_name,
            artist=self.song_author,
            resolution=self.song_resolution,
            start_time=0,
            song_length=song_length,
            accompanyingChannels=[0, 0],  # TODO: is this always [0, 0]?
            accompanyingInstruments=[-2, -1],  # TODO: is this always [-2, -1]?
            accompanyingTracks=[],  # TODO: Is this always empty?
            keySignatures=key_signatures,
            tempos=tempos,
            timeSignatures=time_signatures,
            measures=[],  # TODO: provide the correct value
            tracksV2=tracks_v2,
            maxSimplification=0,  # TODO: Add this later, how to get this value
            supportingTracks=supporting_tracks,
            sections=[],  # TODO: Add this later
            positionGroups=[],  # TODO: Add this later
            technicalGroups=[],  # TODO: Add this later
        )
        if self.ai:
            PianoVisionFingeringGeneratorAI(song).build()
        return song

    def build_parallel(self) -> PianoVisionSong:
        if self.m21_song is None:
            raise ValueError("No music21 song found")
        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            functions = {
                "tracksV2": PianoVisionMeasureBuilder(self.m21_song).build,
                "tempos": PianoVisionTempoBuilder(self.m21_song).build,
                "keySignatures": PianoVisionKeySignatureBuilder(self.m21_song).build,
                "song_length": PianoVisionSongLengthBuilder(self.m21_song).build,
            }
            results = {
                "name": self.song_name,
                "artist": self.song_author,
                "resolution": self.song_resolution,
                "start_time": 0,
                "accompanyingChannels": [0, 0],
                "accompanyingInstruments": [-2, -1],
                "accompanyingTracks": [],
                "timeSignatures": [],
                "measures": [],
                "maxSimplification": 0,
                "supportingTracks": [],
                "sections": [],
                "positionGroups": [],
                "technicalGroups": [],
            }

            with tqdm(total=len(functions)) as pbar:

                def update_results(result):
                    results.update(result)
                    pbar.update(1)

                for _, func in functions.items():
                    pool.apply_async(func, callback=update_results)
            pool.close()
            pool.join()

        return PianoVisionSong(**results)


@dataclass
class PianoVisionSongLengthBuilder:
    m21_song: m21.stream.Score

    def build(self) -> float:
        logging.info("Building PianoVisionSongLength")
        metronome = (
            self.m21_song.recurse().getElementsByClass(m21.tempo.MetronomeMark).first()
        )
        if not metronome:
            raise ValueError("No metronome found")
        metronome = cast(m21.tempo.MetronomeMark, metronome)

        return float(metronome.durationToSeconds(self.m21_song.duration))


@dataclass
class PianoVisionTimeSignatureBuilder(SongPartMixin):
    def build(self) -> list[PianoVisionTimeSignature]:
        results: list[PianoVisionTimeSignature] = []
        rh_time_sigs = self._build_time_signature_for_part(self.right_hand_part)
        results.extend(rh_time_sigs)
        lh_time_sigs = self._build_time_signature_for_part(self.left_hand_part)

        # Check if left hand time signatures are dummy time signatures
        all_lh_time_sigs_4_4 = all(
            sig.time_signature == TimeSignature.FOUR_FOUR for sig in lh_time_sigs
        )
        all_rh_time_sigs_4_4 = all(
            sig.time_signature == TimeSignature.FOUR_FOUR for sig in rh_time_sigs
        )

        if all_lh_time_sigs_4_4 and not all_rh_time_sigs_4_4:
            return results

        results.extend(lh_time_sigs)
        return results

    def _build_time_signature_for_part(
        self, part: m21.stream.Part
    ) -> list[PianoVisionTimeSignature]:
        time_sigs: list[PianoVisionTimeSignature] = []
        for sig in part.getTimeSignatures():
            sig = cast(m21.meter.TimeSignature, sig)
            if not sig.measureNumber:
                raise ValueError("No measure number found for time signature")
            time_sig = PianoVisionTimeSignature(
                ticks=int(sig.offset * 480),
                measures=sig.measureNumber - 1,
                timeSignature=TimeSignature.from_music21(sig),
            )
            time_sigs.append(time_sig)
        return time_sigs


@dataclass
class PianoVisionKeySignatureBuilder:
    m21_song: m21.stream.Score
    ticks_per_quarter: int = 480

    def build(self) -> list[KeySignature]:
        logging.info("Building PianoVisionKeySignature")
        result: list[KeySignature] = []
        for key_sig in self.m21_song.recurse().getElementsByClass(m21.key.KeySignature):
            key = key_sig.asKey()
            if key_sig.activeSite is None:
                raise ValueError("No active site found for key signature")
            ticks = int(key_sig.activeSite.offset * self.ticks_per_quarter)
            pv_keysig = KeySignature(key=key.tonic.name, scale=key.mode, ticks=ticks)
            result.append(pv_keysig)
        return result


@dataclass
class PianoVisionTempoBuilder:
    m21_song: m21.stream.Score
    ticks_per_quarter: int = 480

    def build(self) -> list[Tempo]:
        logging.info("Building PianoVisionTempo")
        result: list[Tempo] = []
        for lower_bound, _, metronome in self.m21_song.metronomeMarkBoundaries():
            time = metronome.durationToSeconds(lower_bound)
            ticks = int(self.ticks_per_quarter * lower_bound)
            pv_tempo = Tempo(
                bpm=metronome.number,
                time=time,
                ticks=ticks,
            )
            result.append(pv_tempo)
        return result


@dataclass
class MetronomeWithBoundaries:
    metronome: m21.tempo.MetronomeMark
    lower_bound: float
    upper_bound: float

    def to_seconds(self, offset: m21.common.OffsetQL | m21.duration.Duration) -> float:
        return self.metronome.durationToSeconds(offset)

    def in_bounds(self, offset: float) -> bool:
        return self.lower_bound <= offset <= self.upper_bound

    @property
    def tempo(self) -> float:
        return self.metronome.number

    @property
    def is_default_tempo(self) -> bool:
        return self.tempo == 120


@dataclass
class PianoVisionSupportingTracksBuilder(MetronomeGetterMixin):
    def __post_init__(self) -> None:
        MetronomeGetterMixin.__post_init__(self)

    def build(self) -> list[SupportingTrack]:
        rh = self._build_supporting_track_for_hand(self.right_hand_part, Hand.RIGHT)
        lh = self._build_supporting_track_for_hand(self.left_hand_part, Hand.LEFT)
        return [rh, lh]

    # Called by build
    def _build_supporting_track_for_hand(
        self, part: m21.stream.Part, hand: Hand
    ) -> SupportingTrack:
        notes: list[SupportingTrackMidi] = []
        for el in part.flatten().notes:
            match el:
                case m21.note.Note():
                    stm = self._build_supporting_track_midis_from_m21_note(el, hand)
                    notes.append(stm)
                case m21.chord.Chord():
                    stms = self._build_supporting_track_midis_from_m21_chord(el, hand)
                    notes.extend(stms)
        return SupportingTrack(myInstrument=-5, theirInstrument=0, notes=notes)

    def _build_supporting_track_midis_from_m21_chord(
        self, chord: m21.chord.Chord, hand: Hand
    ) -> list[SupportingTrackMidi]:
        result = []
        for note in chord.notes:
            note.offset = chord.offset
            stm = self._build_supporting_track_midis_from_m21_note(note, hand)
            result.append(stm)
        return result

    def _build_supporting_track_midis_from_m21_note(
        self, note: m21.note.Note, hand: Hand
    ) -> SupportingTrackMidi:
        offset = float(note.offset)
        metronome = self.get_metronome_for_offset(offset, hand)
        start_time = metronome.to_seconds(offset)
        duration = metronome.to_seconds(note.duration)
        volume = note.volume.velocityScalar
        if volume is None:
            volume = float(0)
        elif not isinstance(volume, float):
            volume = float(volume)
        return SupportingTrackMidi(
            midi=note.pitch.midi,
            time=start_time,
            duration=duration,
            velocity=volume,
        )


@dataclass
class PianoVisionMeasureBuilder(MetronomeGetterMixin):
    """
    A class for building PianoVisionMeasure objects from a music21 Score

    Attributes
    ----------
        midi_song: m21.stream.Score
            The music21 object representing the MIDI song.
        min_note_id: int
            The minimum MIDI note ID encountered during the building process.
        max_note_id: int
            The maximum MIDI note ID encountered during the building process.
        note_count: int
            The total count of notes encountered during the building process.
        measure_note_count: int
            The count of notes within the current measure being processed.
        _metronome: Optional[m21.tempo.MetronomeMark]
            The metronome mark for the current measure.
        _time_sig: Optional[m21.meter.TimeSignature]
            The time signature for the current measure.

    Properties
    ----------
        metronome: m21.tempo.MetronomeMark
            The metronome mark for the current measure.
        time_sig: m21.meter.TimeSignature
            The time signature for the current measure.
        right_hand_part: m21.stream.Part
            The right hand part of the MIDI song.
        left_hand_part: m21.stream.Part
            The left hand part of the MIDI song.

    Methods
    -------
        build(): TracksV2:
            Builds and returns the PianoVisionMeasure objects
            for both the right and left hand parts.
    """

    ticks_per_quarter: int = 480
    min_note_id: int = field(default=0, init=False)
    max_note_id: int = field(default=0, init=False)
    note_count: int = field(default=0, init=False)
    measure_note_count: int = field(default=0, init=False)
    _right_time_sig: Optional[m21.meter.TimeSignature] = field(default=None, init=False)
    _left_time_sig: Optional[m21.meter.TimeSignature] = field(default=None, init=False)
    _active_tie: Optional[m21.tie.Tie] = field(default=None, init=False)
    _active_tie_note: Optional[m21.note.Note] = field(default=None, init=False)

    def __post_init__(self) -> None:
        MetronomeGetterMixin.__post_init__(self)

    def get_time_signature(self, hand: Hand) -> Optional[m21.meter.TimeSignature]:
        if hand == Hand.RIGHT:
            return self._right_time_sig
        elif hand == Hand.LEFT:
            return self._left_time_sig
        raise ValueError(f"Invalid hand {hand}")

    def set_time_signature(self, hand: Hand, time_sig: m21.meter.TimeSignature) -> None:
        if hand == Hand.RIGHT:
            self._right_time_sig = time_sig
        elif hand == Hand.LEFT:
            self._left_time_sig = time_sig
        else:
            raise ValueError(f"Invalid hand {hand}")

    def build(self) -> TracksV2:
        """
        Generates the PianoVisionMeasure objects for both the right and left hand
        parts of the song from data in music21.

        Call Chain:
        -----------
        - build()
            - _build_piano_vision_measures_for_hand()
            - _build_pv_measure_from_m21_measure()
                - _handle_m21_general_note()
                    - _build_pv_note_from_m21_note()
                        - _build_pv_note()
                    - _build_pv_notes_from_m21_chord()
                        - _build_pv_note()
                    - _build_pv_rest_from_m21_rest()
        """
        logging.info("Building PianoVisionMeasures")
        right_measures = self._build_piano_vision_measures_for_hand(
            self.right_hand_part, Hand.RIGHT
        )
        left_measures = self._build_piano_vision_measures_for_hand(
            self.left_hand_part, Hand.LEFT
        )
        return TracksV2(right=right_measures, left=left_measures)

    # Called by build
    def _build_piano_vision_measures_for_hand(
        self, part: m21.stream.Part, hand: Hand
    ) -> list[PianoVisionMeasure]:
        pv_measures = []
        self.note_count = 0
        for measure_data in part.secondsMap:
            if not isinstance(measure_data["element"], m21.stream.Measure):
                continue
            pv_measure = self._build_pv_measure_from_m21_measure(
                measure_data,
                hand,
            )
            pv_measures.append(pv_measure)
        return pv_measures

    def _get_metronomes_for_hand(self, part: m21.stream.Part, hand: Hand) -> None:
        metronomes = [
            MetronomeWithBoundaries(
                metronome_data[2], metronome_data[0], metronome_data[1]
            )
            for metronome_data in part.metronomeMarkBoundaries()
        ]
        if hand == Hand.RIGHT:
            self._right_hand_metronomes = metronomes
        elif hand == Hand.LEFT:
            self._left_hand_metronomes = metronomes

    # Called by _build_piano_vision_measures_for_hand
    def _build_pv_measure_from_m21_measure(
        self, measure_data: dict[str, Any], hand: Hand
    ) -> PianoVisionMeasure:
        # reset tracked values
        self.measure_note_count: int = 0
        self.max_note_id = 0
        self.min_note_id = 200
        measure: m21.stream.Measure = measure_data["element"]  # type: ignore

        # Check if the time signature has changed
        if (
            measure.timeSignature
            and self.get_time_signature(hand) != measure.timeSignature
        ):
            self.set_time_signature(hand, measure.timeSignature)

        time_sig = self.get_time_signature(hand)
        if not time_sig:
            raise ValueError("No time signature found")
        time_signature = TimeSignature([time_sig.numerator, time_sig.denominator])

        notes: list[Note] = []
        rests: list[Rest] = []
        for element in measure.notesAndRests:
            pv_element = self._handle_m21_general_note(element, measure, hand)
            match pv_element:
                case Note():
                    notes.append(pv_element)
                case list():
                    notes.extend(pv_element)
                case Rest():
                    rests.append(pv_element)

        tick_start = float(measure.offset * self.ticks_per_quarter)
        tick_end = (
            float(measure.offset + measure.duration.quarterLength)
            * self.ticks_per_quarter
        )
        return PianoVisionMeasure(
            direction=Direction.DOWN,
            time=measure_data["offsetSeconds"],
            timeEnd=measure_data["endTimeSeconds"],
            max=self.max_note_id,
            min=self.min_note_id,
            measureTicksEnd=tick_end,
            measureTicksStart=tick_start,
            notes=notes,
            rests=rests,
            timeSignature=time_signature,
        )

    # Called by _build_pv_measure_from_m21_measure
    def _handle_m21_general_note(
        self, element: m21.note.GeneralNote, measure: m21.stream.Measure, hand: Hand
    ) -> Note | list[Note] | Rest:
        match element:
            case m21.note.Note():
                if element.tie is not None:
                    if element.tie.type == "start":
                        self._active_tie_note = element
                    if element.tie.type == "stop":
                        if self._active_tie_note is not None:
                            for articulation in self._active_tie_note.articulations:
                                if isinstance(
                                    articulation, m21.articulations.Fingering
                                ):
                                    element.articulations.append(articulation)
                        self._active_tie_note = None
                return self._build_pv_note_from_m21_note(element, measure, hand)
            case m21.chord.Chord():
                return self._build_pv_notes_from_m21_chord(element, measure, hand)
            case m21.note.Rest():
                return self._build_pv_rest_from_m21_rest(element, hand)
        raise ValueError(f"Element {element} not supported")

    # Called by _handle_m21_general_note
    def _build_pv_note_from_m21_note(
        self,
        m21_note: m21.note.Note,
        measure: m21.stream.Measure,
        hand: Hand,
    ) -> Note:
        fingering = Finger.NOT_SET
        for art in m21_note.articulations:
            if isinstance(art, m21.articulations.Fingering):
                fingering = Finger(art.fingerNumber)
            else:
                print(art)
        if m21_note.pitch.midi < self.min_note_id:
            self.min_note_id = m21_note.pitch.midi
        if m21_note.pitch.midi > self.max_note_id:
            self.max_note_id = m21_note.pitch.midi
        note: Note = self._build_pv_note(
            m21_note,
            measure,
            hand,
            fingering,
        )
        return note

    # Called by _handle_m21_general_note
    def _build_pv_notes_from_m21_chord(
        self, m21_chord: m21.chord.Chord, measure: m21.stream.Measure, hand: Hand
    ) -> list[Note]:
        notes: list[Note] = []
        fingerings: list[Finger] = []
        for art in m21_chord.articulations:
            if isinstance(art, m21.articulations.Fingering):
                fingerings.append(Finger(art.fingerNumber))
            else:
                print(art)
        for chord_note, fingering in zip(m21_chord.notes, fingerings, strict=False):
            chord_note.offset = m21_chord.offset
            note = self._build_pv_note(
                chord_note,
                measure,
                hand,
                fingering,
            )
            notes.append(note)
        return notes

    # Called by _handle_m21_general_note
    def _build_pv_rest_from_m21_rest(self, m21_rest: m21.note.Rest, hand: Hand) -> Rest:
        metronome = self.get_metronome_for_offset(m21_rest.offset, hand)
        if not m21_rest.activeSite:
            raise ValueError("No active site found for rest")
        start_time = metronome.to_seconds(m21_rest.activeSite.offset + m21_rest.offset)
        return Rest(
            noteLengthType=NoteLengthType.from_duration(m21_rest.duration),
            time=start_time,
        )

    # Final step to build the note
    def _build_pv_note(
        self,
        m21_note: m21.note.Note,
        m21_measure: m21.stream.Measure,  # type: ignore
        note_hand: Hand,
        fingering: Finger,
    ) -> Note:
        octave: int = int(m21_note.pitch.octave)  # type: ignore
        hand_abbrev = "r" if note_hand == Hand.RIGHT else "l"
        metronome = self.get_metronome_for_offset(m21_note.offset, note_hand)
        note_id = f"{hand_abbrev}{self.note_count}"
        note_offset = float(m21_measure.offset + m21_note.offset)
        start_ticks = int(self.ticks_per_quarter * note_offset)
        duration_ticks = int(self.ticks_per_quarter * m21_note.quarterLength)
        velocity = 0
        if m21_note.volume.velocityScalar is not None:
            velocity = float(m21_note.volume.velocityScalar)
        measure_fraction = float(m21_note.offset / m21_measure.duration.quarterLength)
        measure_number = (m21_measure.measureNumber or 1) - 1
        measure_bars = measure_number + measure_fraction
        if m21_note.duration.type == "complex":
            nearest = round_duration_to_nearest(m21_note.duration)
            m21_note.duration = nearest
        note = Note(
            id=note_id,
            note=m21_note.pitch.midi,
            duration=metronome.to_seconds(m21_note.duration),
            durationTicks=duration_ticks,
            finger=fingering,
            group=-1,
            start=metronome.to_seconds(note_offset),
            end=metronome.to_seconds(note_offset + m21_note.duration.quarterLength),
            measureBars=measure_bars,
            noteOffVelocity=0,
            ticksStart=start_ticks,
            velocity=velocity,
            noteName=m21_note.pitch.nameWithOctave,
            octave=octave,
            notePitch=m21_note.pitch.name,
            noteLengthType=NoteLengthType.from_duration(m21_note.duration),
            measureInd=measure_number,
            noteMeasureInd=self.measure_note_count,
        )
        self.note_count += 1
        self.measure_note_count += 1
        return note


# class PianoVisionFingeringBuilder:
#     def __init__(self, m21_song: m21.stream.Score):
#         self.m21_song = m21_song

#     def build(self) -> list[PianoVisionFingering]:
#         return []
