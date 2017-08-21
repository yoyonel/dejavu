#!/usr/bin/python

import os
import sys
import json
import warnings
import argparse
from pprint import pformat

from dejavu import Dejavu
from dejavu.recognize import DoublonRecognizer
from dejavu.recognize import FileRecognizer
from dejavu.recognize import MicrophoneRecognizer
from dejavu.logger import logger
from argparse import RawTextHelpFormatter

warnings.filterwarnings("ignore")

DEFAULT_CONFIG_FILE = "dejavu.cnf.SAMPLE"


def init(configpath):
    """
    Load config from a JSON file
    """
    try:
        with open(configpath) as f:
            config = json.load(f)
    except IOError as err:
        print("Cannot open configuration: %s. Exiting" % (str(err)))
        sys.exit(1)

    # create a Dejavu instance
    return Dejavu(config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Dejavu: Audio Fingerprinting library",
        formatter_class=RawTextHelpFormatter)
    parser.add_argument('-c', '--config', nargs='?',
                        help='Path to configuration file\n'
                             'Usages: \n'
                             '--config /path/to/config-file\n')
    parser.add_argument('-f', '--fingerprint', nargs='*',
                        help='Fingerprint files in a directory\n'
                             'Usages: \n'
                             '--fingerprint /path/to/directory extension\n'
                             '--fingerprint /path/to/directory')
    parser.add_argument('-r', '--recognize', nargs=2,
                        help='Recognize what is '
                             'playing through the microphone\n'
                             'Usage: \n'
                             '--recognize mic number_of_seconds \n'
                             '--recognize file path/to/file \n')
    parser.add_argument('-d', '--doublon', nargs=2,
                        help='Find (potential) doublons '
                             'for a media\n'
                             'Usage: \n'
                             '--doublon file path/to/file \n')
    parser.add_argument('--empty_database', action='store_true', default=False)

    args = parser.parse_args()

    if not args.fingerprint and not args.recognize and not args.doublon:
        parser.print_help()
        sys.exit(0)

    config_file = args.config
    if config_file is None:
        config_file = DEFAULT_CONFIG_FILE
        # print "Using default config file: %s" % (config_file)

    djv = init(config_file)
    if args.empty_database:
        djv.db.empty()
    if args.fingerprint:
        # Fingerprint all files in a directory
        if len(args.fingerprint) == 2:
            directory = args.fingerprint[0]
            extension = args.fingerprint[1]
            logger.info("Fingerprinting all .%s files in the %s directory" % (extension, directory))
            djv.fingerprint_directory(directory, ["." + extension], 4)

        elif len(args.fingerprint) == 1:
            filepath = args.fingerprint[0]
            if os.path.isdir(filepath):
                print("Please specify an extension if you'd like to fingerprint a directory!")
                sys.exit(1)
            djv.fingerprint_file(filepath)

    elif args.recognize:
        # Recognize audio source
        song = None
        source = args.recognize[0]
        opt_arg = args.recognize[1]

        if source in ('mic', 'microphone'):
            song = djv.recognize(MicrophoneRecognizer, seconds=opt_arg)
        elif source == 'file':
            song = djv.recognize(FileRecognizer, opt_arg, threshold_matches=1.0)
        print(song)

    elif args.doublon:
        # Find (potentials) doublons for a media
        doublons = None
        source = args.doublon[0]
        opt_arg = args.doublon[1]

        if source == 'file':
            doublons = djv.recognize(DoublonRecognizer, opt_arg)
        print("doublons: {}".format(pformat(doublons)))

    sys.exit(0)
