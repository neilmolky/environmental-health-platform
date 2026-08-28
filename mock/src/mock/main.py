from fastapi import FastAPI

from mock.met_office import met_office_app

app = FastAPI(
    title="Mock Services",
    description="Entrypoint for mock services",
    version="0.1.0",
    docs="/",
)


app.include_router(
    met_office_app.router,
    prefix="/met-office",
    tags=["met-office"],
)
