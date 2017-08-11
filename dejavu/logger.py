#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from colorlog import ColoredFormatter
import inspect
import logging
from tqdm import tqdm


__author__ = 'atty_l'


# https://github.com/tqdm/tqdm/issues/193
class TqdmHandler(logging.StreamHandler):
    def __init__(self):
        logging.StreamHandler.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        tqdm.write(msg)


# ---- LOG -----
LOGFORMAT = '%(log_color)s[%(asctime)s][%(levelname)s][%(filename)s][%(funcName)s] %(message)s'

formatter = ColoredFormatter(LOGFORMAT)
LOG_LEVEL = logging.DEBUG
# stream = logging.StreamHandler()
stream = TqdmHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
logger = logging.getLogger('pythonConfig')
logger.setLevel(LOG_LEVEL)
logger.addHandler(stream)
# --------------


# store builtin print
old_print = print


def new_print(*args, **kwargs):
    # if tqdm.tqdm.write raises error, use builtin print
    try:
        tqdm.write(*args, **kwargs)
    except Exception, e:
        old_print(*args, **kwargs)


# globaly replace print with new_print
inspect.__builtins__['print'] = new_print