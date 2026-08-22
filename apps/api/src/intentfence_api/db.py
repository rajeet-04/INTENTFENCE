from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_db_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def create_engine_from_url(database_url: str) -> Engine:
    return create_db_engine(database_url)


def init_db(engine: Engine) -> None:
    from . import db_models  # noqa: F401

    Base.metadata.create_all(engine)
