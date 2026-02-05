"""CRUD package: exposes database and config manager modules."""

from . import database
from . import config_manager

__all__ = ["database", "config_manager"]
