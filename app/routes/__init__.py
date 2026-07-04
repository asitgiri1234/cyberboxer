"""
app.routes package
------------------
Contains the API routers. Each feature (health, claims, users, ...) gets its
own module exposing an `APIRouter`, which is then mounted in `app.main`.
This keeps the routing layer thin and organised by domain concern.
"""
