from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Model = declarative_base()


class Database:
    """
        An object to hold convenient db stuff
    """

    def __init__(self, db_url=None, scoped_session=None):
        self.db_url = db_url
        self.engine = None
        self._session = None
        self.session_factory = sessionmaker()

        if self.db_url is not None:
            self.engine = create_engine(self.db_url)
            self.session_factory.configure(bind=self.engine)
            if scoped_session:
                self._session = scoped_session(self.session_factory)
                Model.query = self._session.query_property()

    @property
    def metadata(self):
        """ To allow compatibility with Flask-Migrate"""
        return Model.metadata

    @contextmanager
    def session(self):
        """
        A context manager that uses a scoped_session if
        one exists, otherwise ensures the session gets closed with
        the context. Keeps code that uses it the same while allowing
        for session reuse inside of web and other contexts.
        """
        session = self._session or self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if not self._session:
                session.close()

    def save(self, model):
        with self.session() as session:
            session.add(model)

    def delete(self, model):
        with self.session() as session:
            session.delete(model)

    def create_if_not_exists(self):
        """
        Create database tables if they are missing
        """
        Model.metadata.create_all(self.engine)
