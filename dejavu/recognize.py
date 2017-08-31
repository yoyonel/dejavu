import dejavu.fingerprint as fingerprint
import dejavu.decoder as decoder
import inotify.adapters
import numpy as np
import os
import pyaudio
import time
from dejavu import _is_audio_media, _is_video_media
from dejavu.logger import logger


class BaseRecognizer(object):
    def __init__(self, dejavu):
        self.dejavu = dejavu
        self.Fs = fingerprint.DEFAULT_FS

    def _recognize(self, *data):
        matches = []
        for d in data:
            matches.extend(self.dejavu.find_matches(d, Fs=self.Fs))
        return self.dejavu.align_matches(iter(matches))

    def _recognize_for_video(self, data, **kargs):
        # logger.debug("_recognize_for_video")
        # Iterator sur les matches des fingerprints des frames de la video input
        iter_on_matches = self.dejavu.find_matches_for_video(data, **kargs)
        # Alignement des matches et calcul du best match.
        match, diff_counter = self.dejavu.align_matches_for_video(iter_on_matches, **kargs)
        return match

    def _recognize_doublons_for_video(self, data, **kargs):
        # logger.debug("_recognize_for_video")
        # Iterator sur les matches des fingerprints des frames de la video input
        iter_on_matches = self.dejavu.find_matches_for_video(data, **kargs)
        # Alignement des matches et calcul du best match.
        video, diff_counter = self.dejavu.align_matches_for_video(iter_on_matches, **kargs)
        # Construction d'un dictionnaire avec les fingerprints et leurs valeurs de count
        sid_counter = {}
        for diff, sid_counter in diff_counter.iteritems():
            for sid, counter in sid_counter.iteritems():
                sid_counter[sid] = counter
        # On trie ce dictionnaire
        ordered_fp_counter = sorted(sid_counter.items(), key=lambda (k, v): v, reverse=True)
        return video, ordered_fp_counter

    def recognize(self):
        pass  # base class does nothing


class FileRecognizer(BaseRecognizer):
    def __init__(self, dejavu):
        super(FileRecognizer, self).__init__(dejavu)

    def recognize_file(self, filename, **kwargs):
        match = False
        if _is_video_media(filename):
            # logger.warning("Video recognition not supported (yet) !")
            # use the Decoder
            frames, fps, file_hash, length = decoder.read_video(filename, self.dejavu.limit)

            t = time.time()
            # On place la longueur (length) de la video input (a reconnaitre) dans le dictionnaire
            # des parametres/arguments.
            kwargs['length'] = length
            # On lance la recognition et on recupere le best match
            match = self._recognize_for_video(frames, **kwargs)
            t = time.time() - t
        elif _is_audio_media(filename):
            frames, self.Fs, file_hash = decoder.read(filename, self.dejavu.limit)

            t = time.time()
            match = self._recognize(*frames)
            t = time.time() - t

        if match:
            match['match_time'] = t

        return match

    def recognize(self, filename, **kwoptions):
        return self.recognize_file(filename, **kwoptions)


class StreamRecognizer(BaseRecognizer):
    def __init__(self, dejavu):
        super(StreamRecognizer, self).__init__(dejavu)
        self._dejavu = dejavu

    def recognize_stream_on_directory(self, directory, **kwargs):
        #
        directory_to_watch = directory
        i = inotify.adapters.Inotify()

        logger.debug("add watch on: {}".format(directory_to_watch))
        i.add_watch(directory_to_watch)

        try:
            for event in i.event_gen():
                if event is not None:
                    (header, type_names, watch_path, filename) = event
                    if type_names == ['IN_CLOSE_WRITE']:
                        logger.debug("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) MASK->NAMES=%s "
                                    "WATCH-PATH=[%s] FILENAME=[%s]",
                                    header.wd, header.mask, header.cookie, header.len, type_names,
                                    watch_path.decode('utf-8'), filename.decode('utf-8'))
                        #
                        media_filepath = os.path.join(watch_path.decode('utf-8'), filename.decode('utf-8'))
                        #
                        t = time.time()
                        logger.debug("media_filepath: {}".format(media_filepath))
                        song = self._dejavu.recognize(FileRecognizer, media_filepath, threshold_matches=1.0)
                        t = time.time() - t
                        if song:
                            song['match_time'] = t
                        #
                        print(song)
        except KeyboardInterrupt:
            logger.warning("Keyboard interruption!")
        finally:
            i.remove_watch(directory_to_watch)
            logger.debug("watch on: {} removed".format(directory_to_watch))
        return ""

    def recognize(self, directory, **kwoptions):
        return self.recognize_stream_on_directory(directory, **kwoptions)


class MicrophoneRecognizer(BaseRecognizer):
    default_chunksize = 8192
    default_format = pyaudio.paInt16
    default_channels = 2
    default_samplerate = 44100

    def __init__(self, dejavu):
        super(MicrophoneRecognizer, self).__init__(dejavu)
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.data = []
        self.channels = MicrophoneRecognizer.default_channels
        self.chunksize = MicrophoneRecognizer.default_chunksize
        self.samplerate = MicrophoneRecognizer.default_samplerate
        self.recorded = False

    def start_recording(self, channels=default_channels,
                        samplerate=default_samplerate,
                        chunksize=default_chunksize):
        self.chunksize = chunksize
        self.channels = channels
        self.recorded = False
        self.samplerate = samplerate

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()

        self.stream = self.audio.open(
            format=self.default_format,
            channels=channels,
            rate=samplerate,
            input=True,
            frames_per_buffer=chunksize,
        )

        self.data = [[] for _ in xrange(channels)]

    def process_recording(self):
        data = self.stream.read(self.chunksize)
        nums = np.fromstring(data, np.int16)
        for c in range(self.channels):
            self.data[c].extend(nums[c::self.channels])

    def stop_recording(self):
        self.stream.stop_stream()
        self.stream.close()
        self.stream = None
        self.recorded = True

    def recognize_recording(self):
        if not self.recorded:
            raise NoRecordingError("Recording was not complete/begun")
        return self._recognize(*self.data)

    def get_recorded_time(self):
        return len(self.data[0]) / self.rate

    def recognize(self, seconds=10):
        self.start_recording()
        for i in range(0, int(self.samplerate / self.chunksize * seconds)):
            self.process_recording()
        self.stop_recording()
        return self.recognize_recording()


class DoublonRecognizer(BaseRecognizer):
    def __init__(self, dejavu):
        super(DoublonRecognizer, self).__init__(dejavu)

    def recognize_doublons(self, filename, **kwargs):
        doublons = False
        if _is_video_media(filename):
            # logger.warning("Video recognition not supported (yet) !")
            # use the Decoder
            frames, fps, file_hash, length = decoder.read_video(filename, self.dejavu.limit)

            t = time.time()
            # On place la longueur (length) de la video input (a reconnaitre) dans le dictionnaire
            # des parametres/arguments.
            kwargs['length'] = length
            # On lance la recognition et on recupere le best match
            match, ordered_sid_counter = self._recognize_doublons_for_video(frames, **kwargs)
            logger.debug("ordered_fp_counter: {}".format(ordered_sid_counter))
            best_match_count = ordered_sid_counter[0][1]
            # doublons (potentiels) a une distance max de 20 du nombre de frames matchees par le meilleur
            # candidat (le match courant).
            # TODO: comme la liste est triee, on n'est pas oblige de la parcourir totalement
            threshold_doublon = 0.80
            doublons = filter(lambda fp_count: fp_count[1] >= best_match_count * threshold_doublon,
                              ordered_sid_counter)
            doublons = map(
                lambda sid_counter: (self.dejavu.extract_identification(sid_counter[0])[1],
                                     sid_counter[1]),
                doublons
            )
            t = time.time() - t
        elif _is_audio_media(filename):
            pass

        # if match:
        #     match['match_time'] = t
        #
        # return match
        return doublons

    def recognize(self, filename, **kwoptions):
        return self.recognize_doublons(filename, **kwoptions)


class NoRecordingError(Exception):
    pass
