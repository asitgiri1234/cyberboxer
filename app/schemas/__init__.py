"""
app.schemas package
-------------------
Pydantic response models for the read APIs. Keeping response shapes in one
place gives us:

* automatic OpenAPI/Swagger documentation of every field, and
* a guarantee that endpoints return only the required fields (no accidental
  over-exposure of ORM internals).
"""
