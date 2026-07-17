"""Business-logic layer.

Services orchestrate repositories, security primitives and domain rules. They
raise domain exceptions (see :mod:`app.core.exceptions`) rather than HTTP errors
so they stay transport-agnostic.
"""
