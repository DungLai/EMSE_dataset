import logging
from builtins import object
from urllib.parse import urlparse

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


# Defines procedure for setting up a sessionmaker
def new_sessionmaker():
    # Turning on autocommit for Postgres, see
    # http://oddbird.net/2014/06/14/sqlalchemy-postgres-autocommit/
    # Otherwise any e.g. query starts a transaction, locking tables... very
    # bad for e.g. multiple notebooks open, multiple processes, etc.
    if Meta.postgres and Meta.ready:
        engine = create_engine(
            Meta.conn_string,
            client_encoding="utf8",
            use_batch_mode=True,
            isolation_level="AUTOCOMMIT",
        )
    else:
        raise ValueError(
            "Meta variables have not been initialized with "
            "a valid postgres connection string."
        )
    # New sessionmaker
    session = sessionmaker(bind=engine)
    return session


def _validate_conn_string(conn_string):
    """Check that the PostgreSQL connection string is valid."""
    logger.info("Validating {} as a connection string...".format(conn_string))
    url = urlparse(conn_string)
    Meta.conn_string = conn_string
    Meta.DBNAME = url.path[1:]
    Meta.DBUSER = url.username
    Meta.DBPWD = url.password
    Meta.DBHOST = url.hostname
    Meta.DBPORT = url.port
    Meta.postgres = url.scheme.startswith("postgres")
    # Actually try to connect to see if the connection string is valid
    try:
        con = psycopg2.connect(
            database=Meta.DBNAME,
            user=Meta.DBUSER,
            password=Meta.DBPWD,
            host=Meta.DBHOST,
        )
        con.close()
    except psycopg2.OperationalError as e:
        raise ValueError(
            "{} is an invalid connection string. Use the form {}".format(
                conn_string, "postgres://<user>:<pw>@<host>:<port>/<database_name>"
            )
        )
    return True


class Meta(object):
    """Singleton-like metadata class for all global variables.

    Adapted from the Unique Design Pattern:
    https://stackoverflow.com/questions/1318406/why-is-the-borg-pattern-better-than-the-singleton-pattern-in-python
    """

    # Static class variables
    conn_string = None
    DBNAME = None
    DBUSER = None
    DBHOST = None
    DBPORT = None
    DBPWD = None
    Session = None
    engine = None
    Base = declarative_base(name="Base", cls=object)
    postgres = False
    ready = False

    @classmethod
    def init(cls, conn_string=None):
        """Return the unique Meta class."""
        if conn_string:
            Meta.ready = _validate_conn_string(conn_string)
            # We initialize the engine within the models module because models'
            # schema can depend on which data types are supported by the engine
            Meta.Session = new_sessionmaker()
            Meta.engine = Meta.Session.kw["bind"]
            logger.info(
                "Connecting user:{} to {}:{}/{}".format(
                    Meta.DBUSER, Meta.DBHOST, Meta.DBPORT, Meta.DBNAME
                )
            )
            Meta._init_db()

        return cls

    @classmethod
    def _init_db(cls):
        """ Initialize the storage schema.

        This call must be performed after all classes that extend
        Base are declared to ensure the storage schema is initialized.
        """
        logger.info("Initializing the storage schema")
        Meta.Base.metadata.create_all(Meta.engine)
