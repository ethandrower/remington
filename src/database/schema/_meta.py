"""
Shared SQLAlchemy MetaData instance.

All table definitions import from here so that metadata.create_all(engine)
can create every table in one call, and all tables belong to the same namespace.
"""

from sqlalchemy import MetaData

metadata = MetaData()
