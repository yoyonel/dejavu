from __future__ import absolute_import
from itertools import izip_longest
import Queue
from collections import defaultdict
import MySQLdb as mysql
from MySQLdb.cursors import DictCursor

from dejavu.database import Database
from dejavu.logger import logger


class SQLDatabase(Database):
    """
    Queries:

    1) Find duplicates (shouldn't be any, though):

        select `hash`, `song_id`, `offset`, count(*) cnt
        from fingerprints
        group by `hash`, `song_id`, `offset`
        having cnt > 1
        order by cnt asc;

    2) Get number of hashes by song:

        select song_id, song_name, count(song_id) as num
        from fingerprints
        natural join songs
        group by song_id
        order by count(song_id) desc;

    3) get hashes with highest number of collisions

        select
            hash,
            count(distinct song_id) as n
        from fingerprints
        group by `hash`
        order by n DESC;

    => 26 different songs with same fingerprint (392 times):

        select songs.song_name, fingerprints.offset
        from fingerprints natural join songs
        where fingerprints.hash = "08d3c833b71c60a7b620322ac0c0aba7bf5a3e73";

    4) size of tables
        SELECT
            table_schema as `Database`,
            table_name AS `Table`,
            round(((data_length + index_length) / 1024 / 1024), 2) `Size in MB`
        FROM information_schema.TABLES;
    """

    type = "mysql"

    # tables
    FINGERPRINTS_TABLENAME = "fingerprints"
    SONGS_TABLENAME = "songs"

    # fields
    FIELD_FINGERPRINTED = "fingerprinted"

    # creates
    CREATE_FINGERPRINTS_TABLE = """
        CREATE TABLE IF NOT EXISTS `%s` (
             `%s` binary(10) not null,
             `%s` mediumint unsigned not null,
             `%s` int unsigned not null,
         INDEX (%s),
         UNIQUE KEY `unique_constraint` (%s, %s, %s),
         FOREIGN KEY (%s) REFERENCES %s(%s) ON DELETE CASCADE
    ) ENGINE=INNODB;""" % (
        FINGERPRINTS_TABLENAME, Database.FIELD_HASH,
        Database.FIELD_SONG_ID, Database.FIELD_OFFSET, Database.FIELD_HASH,
        Database.FIELD_SONG_ID, Database.FIELD_OFFSET, Database.FIELD_HASH,
        Database.FIELD_SONG_ID, SONGS_TABLENAME, Database.FIELD_SONG_ID
    )

    CREATE_SONGS_TABLE = """
        CREATE TABLE IF NOT EXISTS `%s` (
            `%s` mediumint unsigned not null auto_increment,
            `%s` varchar(250) not null,
            `%s` tinyint default 0,
            `%s` binary(20) not null,
        PRIMARY KEY (`%s`),
        UNIQUE KEY `%s` (`%s`)
    ) ENGINE=INNODB;""" % (
        SONGS_TABLENAME, Database.FIELD_SONG_ID, Database.FIELD_SONGNAME, FIELD_FINGERPRINTED,
        Database.FIELD_FILE_SHA1,
        Database.FIELD_SONG_ID, Database.FIELD_SONG_ID, Database.FIELD_SONG_ID,
    )

    # inserts (ignores duplicates)
    INSERT_FINGERPRINT = """
        INSERT IGNORE INTO %s (%s, %s, %s) values
            (UNHEX(%%s), %%s, %%s);
    """ % (FINGERPRINTS_TABLENAME, Database.FIELD_HASH, Database.FIELD_SONG_ID, Database.FIELD_OFFSET)

    INSERT_SONG = "INSERT INTO %s (%s, %s) values (%%s, UNHEX(%%s));" % (
        SONGS_TABLENAME, Database.FIELD_SONGNAME, Database.FIELD_FILE_SHA1)

    # selects
    SELECT = """
        SELECT %s, %s FROM %s WHERE %s = UNHEX(%%s);
    """ % (Database.FIELD_SONG_ID, Database.FIELD_OFFSET, FINGERPRINTS_TABLENAME, Database.FIELD_HASH)

    SELECT_MULTIPLE = """
        SELECT HEX(%s), %s, %s FROM %s WHERE %s IN (%%s);
    """ % (Database.FIELD_HASH, Database.FIELD_SONG_ID, Database.FIELD_OFFSET,
           FINGERPRINTS_TABLENAME, Database.FIELD_HASH)

    SELECT_ALL = """
        SELECT %s, %s FROM %s;
    """ % (Database.FIELD_SONG_ID, Database.FIELD_OFFSET, FINGERPRINTS_TABLENAME)

    SELECT_SONG = """
        SELECT %s, HEX(%s) as %s FROM %s WHERE %s = %%s;
    """ % (Database.FIELD_SONGNAME, Database.FIELD_FILE_SHA1, Database.FIELD_FILE_SHA1, SONGS_TABLENAME, Database.FIELD_SONG_ID)

    SELECT_NUM_FINGERPRINTS = """
        SELECT COUNT(*) as n FROM %s
    """ % FINGERPRINTS_TABLENAME

    SELECT_UNIQUE_SONG_IDS = """
        SELECT COUNT(DISTINCT %s) as n FROM %s WHERE %s = 1;
    """ % (Database.FIELD_SONG_ID, SONGS_TABLENAME, FIELD_FINGERPRINTED)

    SELECT_SONGS = """
        SELECT %s, %s, HEX(%s) as %s FROM %s WHERE %s = 1;
    """ % (Database.FIELD_SONG_ID, Database.FIELD_SONGNAME, Database.FIELD_FILE_SHA1, Database.FIELD_FILE_SHA1,
           SONGS_TABLENAME, FIELD_FINGERPRINTED)

    # drops
    DROP_FINGERPRINTS = "DROP TABLE IF EXISTS %s;" % FINGERPRINTS_TABLENAME
    DROP_SONGS = "DROP TABLE IF EXISTS %s;" % SONGS_TABLENAME

    # update
    UPDATE_SONG_FINGERPRINTED = """
        UPDATE %s SET %s = 1 WHERE %s = %%s
    """ % (SONGS_TABLENAME, FIELD_FINGERPRINTED, Database.FIELD_SONG_ID)

    # delete
    DELETE_UNFINGERPRINTED = """
        DELETE FROM %s WHERE %s = 0;
    """ % (SONGS_TABLENAME, FIELD_FINGERPRINTED)

    def __init__(self, **options):
        super(SQLDatabase, self).__init__()
        self.cursor = cursor_factory(**options)
        self._options = options

        self._grouper_options = {
            'DB_REQUEST': options.get("grouper_db_request", 100),
            'SPLIT_HASHES': options.get("grouper_return_matches", 25)
        }

    def after_fork(self):
        # Clear the cursor cache, we don't want any stale connections from
        # the previous process.
        Cursor.clear_cache()

    def setup(self):
        """
        Creates any non-existing tables required for dejavu to function.

        This also removes all songs that have been added but have no
        fingerprints associated with them.
        """
        with self.cursor() as cur:
            cur.execute(self.CREATE_SONGS_TABLE)
            cur.execute(self.CREATE_FINGERPRINTS_TABLE)
            cur.execute(self.DELETE_UNFINGERPRINTED)

    def empty(self):
        """
        Drops tables created by dejavu and then creates them again
        by calling `SQLDatabase.setup`.

        .. warning:
            This will result in a loss of data
        """
        logger.debug("empty database ...")
        with self.cursor() as cur:
            cur.execute(self.DROP_FINGERPRINTS)
            cur.execute(self.DROP_SONGS)

        self.setup()

    def delete_unfingerprinted_songs(self):
        """
        Removes all songs that have no fingerprints associated with them.
        """
        with self.cursor() as cur:
            cur.execute(self.DELETE_UNFINGERPRINTED)

    def get_num_songs(self):
        """
        Returns number of songs the database has fingerprinted.
        """
        with self.cursor() as cur:
            cur.execute(self.SELECT_UNIQUE_SONG_IDS)

            for count, in cur:
                return count
            return 0

    def get_num_fingerprints(self):
        """
        Returns number of fingerprints the database has fingerprinted.
        """
        with self.cursor() as cur:
            cur.execute(self.SELECT_NUM_FINGERPRINTS)

            for count, in cur:
                return count
            return 0

    def set_song_fingerprinted(self, sid):
        """
        Set the fingerprinted flag to TRUE (1) once a song has been completely
        fingerprinted in the database.
        """
        with self.cursor() as cur:
            cur.execute(self.UPDATE_SONG_FINGERPRINTED, (sid,))

    def get_songs(self):
        """
        Return songs that have the fingerprinted flag set TRUE (1).
        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_SONGS)
            for row in cur:
                yield row

    def get_song_by_id(self, sid):
        """
        Returns song by its ID.
        """
        with self.cursor(cursor_type=DictCursor) as cur:
            cur.execute(self.SELECT_SONG, (sid,))
            return cur.fetchone()

    def insert(self, hash, sid, offset):
        """
        Insert a (sha1, song_id, offset) row into database.
        """
        with self.cursor() as cur:
            cur.execute(self.INSERT_FINGERPRINT, (hash, sid, offset))

    def insert_song(self, songname, file_hash):
        # type: (str, str) -> str
        """
        Inserts song in the database and returns the ID of the inserted record.
        """
        with self.cursor() as cur:
            cur.execute(self.INSERT_SONG, (songname, file_hash))
            return cur.lastrowid

    def query(self, hash):
        """
        Return all tuples associated with hash.

        If hash is None, returns all entries in the
        database (be careful with that one!).
        """
        # select all if no key
        query = self.SELECT_ALL if hash is None else self.SELECT

        with self.cursor() as cur:
            cur.execute(query)
            for sid, offset in cur:
                yield (sid, offset)

    def get_iterable_kv_pairs(self):
        """
        Returns all tuples in database.
        """
        return self.query(None)

    def insert_hashes(self, sid, hashes):
        """
        Insert series of hash => song_id, offset
        values into the database.
        """
        values = []
        for hash, offset in hashes:
            values.append((hash, sid, offset))

        with self.cursor() as cur:
            for split_values in grouper(values, self._grouper_options['DB_REQUEST']):
                # logger.debug("split_values: {}".format(split_values))
                cur.executemany(self.INSERT_FINGERPRINT, split_values)

    def return_matches(self, hashes):
        """
        Return the (song_id, offset_diff) tuples associated with
        a list of (sha1, sample_offset) values.
        """
        # TODO: il peut avoir plusieurs offset pour un meme hash !
        # Create a dictionary of hash => offset pairs for later lookups
        mapper = defaultdict(list)

        # WARNING: On consomme (tout) l'iteratable !
        for h, offset in hashes:
            # logger.debug("hash.upper(): {}".format(hash.upper()))
            mapper[h.upper()].append(offset)

        # Get an iteratable of all the hashes we need
        values = mapper.keys()
        # logger.debug("len(mapper.keys()): {}".format(len(mapper.keys())))

        with self.cursor() as cur:
            for split_values in grouper(values, self._grouper_options['DB_REQUEST']):
                # logger.debug("split_values: {}".format(split_values))

                # Create our IN part of the query
                query = self.SELECT_MULTIPLE
                query %= ', '.join(['UNHEX(%s)'] * len(split_values))

                # logger.debug("query: {}".format(query))
                # logger.debug("split_values: {}".format(split_values))
                cur.execute(query, split_values)

                for h, sid, offset in cur:
                    # logger.debug("hash: {}".format(hash, offset))
                    # (sid, db_offset - song_sampled_offset)
                    for offset_from_mapper in mapper[h]:
                        yield (sid, offset - offset_from_mapper)

    def return_matches_with_split(self, hashes):
        """
        Return the (song_id, offset_diff) tuples associated with
        a list of (sha1, sample_offset) values.
        """
        option_split_hashes = self._grouper_options['SPLIT_HASHES']
        logger.debug("option_split_hashes: {}".format(option_split_hashes))
        for split_hashes in grouper(hashes, option_split_hashes):
            mapper = defaultdict(list)
            values = []

            for h, offset in split_hashes:
                mapper_hash = h.upper()
                mapper[mapper_hash].append(offset)
                values.append(mapper_hash)

            with self.cursor() as cur:
                for split_values in grouper(values, self._grouper_options['DB_REQUEST']):
                    # Create our IN part of the query
                    query = self.SELECT_MULTIPLE
                    query %= ', '.join(['UNHEX(%s)'] * len(split_values))

                    cur.execute(query, split_values)

                    for h, sid, offset in cur:
                        for offset_from_mapper in mapper[h]:
                            yield (sid, offset - offset_from_mapper)

    def __getstate__(self):
        return self._options,

    def __setstate__(self, state):
        self._options, = state
        self.cursor = cursor_factory(**self._options)


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return (filter(None, values) for values
            in izip_longest(fillvalue=fillvalue, *args))


def cursor_factory(**factory_options):
    def cursor(**options):
        options.update(factory_options)
        return Cursor(**options)
    return cursor


class Cursor(object):
    """
    Establishes a connection to the database and returns an open cursor.


    ```python
    # Use as context manager
    with Cursor() as cur:
        cur.execute(query)
    ```
    """
    _cache = Queue.Queue(maxsize=5)

    def __init__(self, cursor_type=mysql.cursors.Cursor, **options):
        super(Cursor, self).__init__()

        try:
            conn = self._cache.get_nowait()
        except Queue.Empty:
            conn = mysql.connect(**options)
        else:
            # Ping the connection before using it from the cache.
            conn.ping(True)

        self.conn = conn
        self.conn.autocommit(False)
        self.cursor_type = cursor_type

    @classmethod
    def clear_cache(cls):
        cls._cache = Queue.Queue(maxsize=5)

    def __enter__(self):
        self.cursor = self.conn.cursor(self.cursor_type)
        return self.cursor

    def __exit__(self, extype, exvalue, traceback):
        # if we had a MySQL related error we try to rollback the cursor.
        if extype is mysql.MySQLError:
            self.cursor.rollback()

        self.cursor.close()
        self.conn.commit()

        # Put it back on the queue
        try:
            self._cache.put_nowait(self.conn)
        except Queue.Full:
            self.conn.close()
