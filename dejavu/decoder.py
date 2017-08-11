import cv2
import os
import fnmatch
import numpy as np
from pydub import AudioSegment
from pydub.utils import audioop
import wavio
from hashlib import sha1
from dejavu.logger import logger, tqdm


def unique_hash(filepath, blocksize=2**20):
    """ Small function to generate a hash to uniquely generate
    a file. Inspired by MD5 version here:
    http://stackoverflow.com/a/1131255/712997

    Works with large files. 
    """
    s = sha1()
    with open(filepath, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            s.update(buf)
    return s.hexdigest().upper()


def find_files(path, extensions):
    # Allow both with ".mp3" and without "mp3" to be used for extensions
    extensions = [e.replace(".", "") for e in extensions]

    for dirpath, dirnames, files in os.walk(path):
        for extension in extensions:
            for f in fnmatch.filter(files, "*.%s" % extension):
                p = os.path.join(dirpath, f)
                yield (p, extension)


def read(filename, limit=None):
    """
    Reads any file supported by pydub (ffmpeg) and returns the data contained
    within. If file reading fails due to input being a 24-bit wav file,
    wavio is used as a backup.

    Can be optionally limited to a certain amount of seconds from the start
    of the file by specifying the `limit` parameter. This is the amount of
    seconds from the start of the file.

    returns: (channels, samplerate)
    """
    # pydub does not support 24-bit wav files, use wavio when this occurs
    try:
        audiofile = AudioSegment.from_file(filename)

        if limit:
            audiofile = audiofile[:limit * 1000]

        data = np.fromstring(audiofile._data, np.int16)

        channels = []
        for chn in xrange(audiofile.channels):
            channels.append(data[chn::audiofile.channels])

        fs = audiofile.frame_rate
    except audioop.error:
        fs, _, audiofile = wavio.readwav(filename)

        if limit:
            audiofile = audiofile[:limit * 1000]

        audiofile = audiofile.T
        audiofile = audiofile.astype(np.int16)

        channels = []
        for chn in audiofile:
            channels.append(chn)

    return channels, audiofile.frame_rate, unique_hash(filename)


class IterVideo:
    def __init__(self, cap, limit=None):
        self.current = 0
        self.high = limit or int(cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1)
        self.cap = cap

    def __iter__(self):
        return self

    def next(self):     # Python 3: def __next__(self)
        if not self.cap.isOpened() or self.current > self.high:
            raise StopIteration
        else:
            self.current += 1
            return self.cap.read() if self.cap.isOpened() else None


def read_video(filename, limit=None):
    """
    Reads any file supported by OpenCV and returns the data contained
    within.

    Can be optionally limited to a certain amount of seconds from the start
    of the file by specifying the `limit` parameter. This is the amount of
    seconds from the start of the file.

    returns: (channels, samplerate)

    ps: c'est un transfert (complet) en RAM ... ce n'est peut etre pas la meilleur strategie ...
    """
    channels = []
    frame_rate = None

    try:
        cap = cv2.VideoCapture(filename)

        # https://stackoverflow.com/questions/25359288/how-to-know-total-number-of-frame-in-a-file-with-cv2-in-python
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_rate = fps = cap.get(cv2.CAP_PROP_FPS)

        logger.debug("length: {}".format(length))
        logger.debug("width: {}".format(width))
        logger.debug("height: {}".format(height))
        logger.debug("fps: {}".format(fps))

        logger.debug("Read video: {} ...".format(filename))
        for ret, frame in tqdm(IterVideo(cap, limit), total=limit or length):
            channels.append(frame)
    except Exception, e:
        logger.error("Exception: {}".format(repr(e)))

    return channels, frame_rate, unique_hash(filename)


def path_to_songname(path):
    """
    Extracts song name from a filepath. Used to identify which songs
    have already been fingerprinted on disk.
    """
    return os.path.splitext(os.path.basename(path))[0]
