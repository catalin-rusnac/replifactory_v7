from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_routes import experiment_routes
from fastapi_routes import service_routes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or ["*"] for all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment_routes.router)
app.include_router(service_routes.router)