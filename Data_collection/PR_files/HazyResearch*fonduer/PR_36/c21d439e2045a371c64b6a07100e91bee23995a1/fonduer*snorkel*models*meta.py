from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import object

import getpass
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Defines procedure for setting up a sessionmaker
def new_sessionmaker():
    # Turning on autocommit for Postgres, see
    # http://oddbird.net/2014/06/14/sqlalchemy-postgres-autocommit/
    # Otherwise any e.g. query starts a transaction, locking tables... very
    # bad for e.g. multiple notebooks open, multiple processes, etc.
    if Meta.postgres and Meta.ready:
        engine = create_engine(Meta.conn_string, isolation_level="AUTOCOMMIT")
    else:
        raise ValueError(
            "Meta variables have not been initialized with a postgres connection string."
        )

    # New sessionmaker
    session = sessionmaker(bind=engine)
    return session


class Meta(object):
    """Singleton-like metadata class for all global variables.

    Adapted from the Unique Design Pattern:
    https://stackoverflow.com/questions/1318406/why-is-the-borg-pattern-better-than-the-singleton-pattern-in-python
    """

    # Static class variables
    conn_string = None
    DBNAME = None
    DBUSER = None
    DBPORT = None
    Session = None
    engine = None
    Base = declarative_base(name='Base', cls=object)
    postgres = False
    ready = False

    @classmethod
    def init(cls, conn_string=None):
        """Return the unique Meta class."""
        if conn_string and not Meta.ready:
            Meta.conn_string = conn_string
            Meta.DBNAME = conn_string.split('/')[-1]
            Meta.DBUSER = getpass.getuser()
            Meta.DBPORT = urlparse(conn_string).port
            Meta.postgres = conn_string.startswith('postgres')
            # We initialize the engine within the models module because models'
            # schema can depend on which data types are supported by the engine
            Meta.ready = Meta.postgres
            Meta.Session = new_sessionmaker()
            Meta.engine = Meta.Session.kw['bind']
            if Meta.ready:
                Meta._init_db()
            else:
                raise ValueError(
                    "{} is not a valid postgres connection string.".format(
                        conn_string))

        return cls

    @classmethod
    def _init_db(cls):
        """ Initialize the storage schema.

        This call must be performed after all classes that extend
        Base are declared to ensure the storage schema is initialized.
        """
        if Meta.ready:
            logger.info("Initializing the storage schema")
            Meta.Base.metadata.create_all(Meta.engine)
        else:
            raise ValueError("The Meta variables haven't been initialized.")
