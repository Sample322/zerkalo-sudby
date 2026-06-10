"""Pydantic v2 request/response schemas (the API contract surface).

ORM models map to these via ``model_config = ConfigDict(from_attributes=True)`` — never
return ORM objects directly so internal columns can't leak into responses.
"""
