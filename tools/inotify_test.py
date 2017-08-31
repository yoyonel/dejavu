import logging
import argparse


import inotify.adapters

_DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

_LOGGER = logging.getLogger(__name__)


def _configure_logging():
    _LOGGER.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()

    formatter = logging.Formatter(_DEFAULT_LOG_FORMAT)
    ch.setFormatter(formatter)

    _LOGGER.addHandler(ch)


def process(args):
    i = inotify.adapters.Inotify()

    _LOGGER.debug("add watch on: {}".format(args.directory_to_watch))
    i.add_watch(args.directory_to_watch)

    try:
        for event in i.event_gen():
            if event is not None:
                (header, type_names, watch_path, filename) = event
                if type_names == ['IN_CLOSE_WRITE']:
                    _LOGGER.info("WD=(%d) MASK=(%d) COOKIE=(%d) LEN=(%d) MASK->NAMES=%s "
                                 "WATCH-PATH=[%s] FILENAME=[%s]",
                                 header.wd, header.mask, header.cookie, header.len, type_names,
                                 watch_path.decode('utf-8'), filename.decode('utf-8'))
    except KeyboardInterrupt:
        _LOGGER.warning("Keyboard interruption!")
    finally:
        i.remove_watch(args.directory_to_watch)
        _LOGGER.debug("watch on: {} removed".format(args.directory_to_watch))


def build_parser(parser=None, **argparse_options):
    """

    :param parser:
    :param argparse_options:
    :return:
    """
    if parser is None:
        parser = argparse.ArgumentParser(**argparse_options)

    # config file
    parser.add_argument('directory_to_watch',
                        type=str,
                        help="")
    #
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                        help="increase output verbosity")
    # return parsing
    return parser


def parse_arguments():
    """

    :return:
    """
    # return parsing
    return build_parser().parse_args()


def main():
    args = parse_arguments()
    process(args)


if __name__ == '__main__':
    _configure_logging()
    main()
