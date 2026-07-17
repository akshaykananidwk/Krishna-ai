"""Data-access layer (Repository pattern).

Repositories own all SQLAlchemy query logic so that services depend on a small,
testable interface rather than on the ORM directly.
"""
