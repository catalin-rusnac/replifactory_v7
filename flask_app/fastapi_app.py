from fastapi import FastAPI
from fastapi_routes import experiment_routes, service_routes
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment_routes.router)
app.include_router(service_routes.router)