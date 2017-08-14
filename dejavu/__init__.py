# coding: utf8
from dejavu.database import get_database, Database
import dejavu.decoder as decoder
import fingerprint
import multiprocessing
import numpy as np
import os
import traceback
import subprocess
import sys
from functools import partial
from collections import defaultdict
from itertools import groupby
from dejavu.logger import logger, tqdm


class Dejavu(object):

    SONG_ID = "song_id"
    SONG_NAME = 'song_name'
    CONFIDENCE = 'confidence'
    MATCH_TIME = 'match_time'
    OFFSET = 'offset'
    OFFSET_SECS = 'offset_seconds'

    EXTENSIONS_FOR_AUDIO = ('.mp3', '.wav')
    EXTENSIONS_FOR_VIDEO = ('.mp4', '.avi')

    def __init__(self, config):
        super(Dejavu, self).__init__()

        self.config = config

        # initialize db
        db_cls = get_database(config.get("database_type", None))

        self.db = db_cls(**config.get("database", {}))
        self.db.setup()

        # if we should limit seconds fingerprinted,
        # None|-1 means use entire track
        self.limit = self.config.get("fingerprint_limit", None)
        if self.limit == -1:  # for JSON compatibility
            self.limit = None
        self.get_fingerprinted_songs()

    def get_fingerprinted_songs(self):
        # get songs previously indexed
        self.songs = self.db.get_songs()
        self.songhashes_set = set()  # to know which ones we've computed before
        for song in self.songs:
            song_hash = song[Database.FIELD_FILE_SHA1]
            self.songhashes_set.add(song_hash)

    def fingerprint_directory(self, path, extensions, nprocesses=None):
        # Try to use the maximum amount of processes if not given.
        try:
            nprocesses = nprocesses or multiprocessing.cpu_count()
        except NotImplementedError:
            nprocesses = 1
        else:
            nprocesses = 1 if nprocesses <= 0 else nprocesses

        pool = multiprocessing.Pool(nprocesses)

        filenames_to_fingerprint = []
        for filename, _ in decoder.find_files(path, extensions):

            # don't refingerprint already fingerprinted files
            if decoder.unique_hash(filename) in self.songhashes_set:
                logger.debug("%s already fingerprinted, continuing..." % filename)
                continue

            filenames_to_fingerprint.append(filename)
        logger.debug("filenames_to_fingerprint: {}".format(filenames_to_fingerprint))

        # Prepare _fingerprint_worker input
        worker_input = zip(filenames_to_fingerprint,
                           [self.limit] * len(filenames_to_fingerprint))

        # Send off our tasks
        iterator = pool.imap_unordered(_fingerprint_worker, worker_input)

        # Loop till we have all of them
        while True:
            try:
                song_name, hashes, file_hash = iterator.next()
            except multiprocessing.TimeoutError:
                continue
            except StopIteration:
                break
            except:
                logger.error("Failed fingerprinting")
                # Print traceback because we can't reraise it here
                traceback.print_exc(file=sys.stdout)
            else:
                logger.debug("Insert in database ...")
                sid = self.db.insert_song(song_name, file_hash)

                self.db.insert_hashes(sid, hashes)
                self.db.set_song_fingerprinted(sid)
                self.get_fingerprinted_songs()

        pool.close()
        pool.join()

    def fingerprint_file(self, filepath, song_name=None):
        songname = decoder.path_to_songname(filepath)
        song_hash = decoder.unique_hash(filepath)
        song_name = song_name or songname
        # don't refingerprint already fingerprinted files
        if song_hash in self.songhashes_set:
            logger.debug("%s already fingerprinted, continuing..." % song_name)
        else:
            song_name, hashes, file_hash = _fingerprint_worker(
                filepath,
                self.limit,
                song_name=song_name
            )
            sid = self.db.insert_song(song_name, file_hash)

            self.db.insert_hashes(sid, hashes)
            self.db.set_song_fingerprinted(sid)
            self.get_fingerprinted_songs()

    def find_matches(self, samples, Fs=fingerprint.DEFAULT_FS):
        hashes = fingerprint.fingerprint(samples, Fs=Fs)
        return self.db.return_matches(hashes)

    def find_matches_for_video(self, frames, **kwargs):
        hashes = fingerprint.fingerprint_for_video(frames, **kwargs)
        # logger.debug("hashes: {}".format(list(hashes)))
        # return self.db.return_matches(hashes)
        return self.db.return_matches_with_split(hashes)

    def align_matches(self, matches, **kwargs):
        """
            Finds hash matches that align in time with other matches and finds
            consensus about which hashes are "true" signal from the audio.

            Returns a dictionary with match information.
        """
        length = kwargs.get('length', 0.0)
        threshold_matches = kwargs.get('threshold_matches', 1.0)
        threshold_matches = int(round(float(length) * threshold_matches))
        logger.debug("threshold for matches (in frames): {}/{}".format(threshold_matches, length))

        # https://stackoverflow.com/questions/5029934/python-defaultdict-of-defaultdict
        diff_counter = defaultdict(partial(defaultdict, int))

        largest = 0
        largest_count = 0
        song_id = -1

        logger.debug("Align matches ...")
        # infinite loop
        while True:
            try:
                # get the next item
                sid, diff = next(matches)

                # update counter dict
                diff_counter[diff][sid] += 1

                if diff_counter[diff][sid] > largest_count:
                    largest = diff
                    largest_count = diff_counter[diff][sid]
                    song_id = sid

                if largest_count > threshold_matches:
                    logger.debug("Break: largest_count > {}=threshold_matches".format(threshold_matches))
                    raise StopIteration
            except StopIteration:
                # if StopIteration is raised, break from loop
                break
        logger.debug("largest_count: {}".format(largest_count))
        # extract idenfication
        song = self.db.get_song_by_id(song_id)
        if song:
            # TODO: Clarify what `get_song_by_id` should return.
            songname = song.get(Dejavu.SONG_NAME, None)
        else:
            return None

        # return match info
        nseconds = round(float(largest) / fingerprint.DEFAULT_FS *
                         fingerprint.DEFAULT_WINDOW_SIZE *
                         fingerprint.DEFAULT_OVERLAP_RATIO, 5)
        song = {
            Dejavu.SONG_ID: song_id,
            Dejavu.SONG_NAME: songname,
            Dejavu.CONFIDENCE: largest_count,
            Dejavu.OFFSET: int(largest),
            Dejavu.OFFSET_SECS: nseconds,
            Database.FIELD_FILE_SHA1: song.get(Database.FIELD_FILE_SHA1, None), }
        return song

    def align_matches_for_video(self, matches, **kwargs):
        """
            Finds hash matches that align in time with other matches and finds
            consensus about which hashes are "true" signal from the audio.

            Returns a dictionary with match information.
        """
        length = kwargs.get('length', 0.0)
        threshold_matches = kwargs.get('threshold_matches', 1.0)
        threshold_matches = int(round(float(length) * threshold_matches))
        logger.debug("threshold for matches (in frames): {}/{}".format(threshold_matches, length))

        # https://stackoverflow.com/questions/5029934/python-defaultdict-of-defaultdict
        diff_counter = defaultdict(partial(defaultdict, int))

        largest = 0
        largest_count = 0
        song_id = -1

        logger.debug("Align matches ...")
        # infinite loop
        while True:
            try:
                # get the next item
                sid, diff = next(matches)

                # update counter dict
                diff_counter[diff][sid] += 1

                if diff_counter[diff][sid] > largest_count:
                    largest = diff
                    largest_count = diff_counter[diff][sid]
                    song_id = sid

                if largest_count > threshold_matches:
                    logger.debug("Break: largest_count > {}=threshold_matches".format(threshold_matches))
                    raise StopIteration
            except StopIteration:
                # if StopIteration is raised, break from loop
                break

        logger.debug("largest_count: {}".format(largest_count))

        # extract idenfication
        song = self.db.get_song_by_id(song_id)
        if song:
            # TODO: Clarify what `get_song_by_id` should return.
            songname = song.get(Dejavu.SONG_NAME, None)
        else:
            return None

        # return match info
        nseconds = largest

        song = {
            Dejavu.SONG_ID: song_id,
            Dejavu.SONG_NAME: songname,
            Dejavu.CONFIDENCE: largest_count,
            Dejavu.OFFSET: int(largest),
            Dejavu.OFFSET_SECS: nseconds,
            Database.FIELD_FILE_SHA1: song.get(Database.FIELD_FILE_SHA1, None), }
        return song

    def recognize(self, recognizer, *options, **kwoptions):
        r = recognizer(self)
        return r.recognize(*options, **kwoptions)


def _is_media(filename, search_pattern):
    """

    :param filename:
    :param search_pattern:
    :return:

    """
    # https://stackoverflow.com/questions/13332268/python-subprocess-command-with-pipe
    cmd = "ffprobe -v error -show_streams {} | grep codec_type".format(filename)
    ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ps.communicate()[0].split("\n")
    return search_pattern in output


def _is_audio_media(filename):
    # problem: les audios contiennent aussi des vidéos (image fixe)
    # return _is_media(filename, 'codec_type=audio')

    songname, extension = os.path.splitext(os.path.basename(filename))
    return extension in Dejavu.EXTENSIONS_FOR_AUDIO


def _is_video_media(filename):
    # return _is_media(filename, 'codec_type=video')

    songname, extension = os.path.splitext(os.path.basename(filename))
    return extension in Dejavu.EXTENSIONS_FOR_VIDEO


def _fingerprint_worker(filename, limit=None, song_name=None):
    # Pool.imap sends arguments as tuples so we have to unpack
    # them ourself.
    try:
        filename, limit = filename
    except ValueError:
        pass

    # extract songname extension
    songname, extension = os.path.splitext(os.path.basename(filename))
    song_name = song_name or songname
    logger.debug("songname, extension: '{}', '{}'".format(songname, extension))

    if _is_video_media(filename):
        logger.debug("{}{} is a video file".format(song_name, extension))

        # use the Decoder
        frames, fps, file_hash, length = decoder.read_video(filename, limit)

        result = set()
        kwoptions = {'length': length}
        hashes = fingerprint.fingerprint_for_video(frames, **kwoptions)
        result |= set(hashes)

        # logger.debug("result: {}".format(result))
        return song_name, result, file_hash
        # return song_name, hashes, file_hash
    elif _is_audio_media(filename):
        logger.debug("{}{} is a audio file".format(song_name, extension))

        # use the Decoder
        frames, fps, file_hash = decoder.read(filename, limit)

        result = set()
        channel_amount = len(frames)

        for channeln, channel in enumerate(frames):
            logger.debug("Fingerprinting channel %d/%d for %s" % (channeln + 1,
                                                                  channel_amount,
                                                                  filename))
            hashes = fingerprint.fingerprint(channel, Fs=fps)
            logger.debug("Finished channel %d/%d for %s" % (channeln + 1, channel_amount, filename))
            result |= set(hashes)

        # logger.debug("result: {}".format(result))

        return song_name, result, file_hash


def chunkify(lst, n):
    """
    Splits a list into roughly n equal parts.
    http://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    """
    return [lst[i::n] for i in xrange(n)]
