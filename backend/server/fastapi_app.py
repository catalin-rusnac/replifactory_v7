import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from fastapi import FastAPI
from routers.experiment_router import router as experiment_router
from routers.service_router import router as service_router
from routers.device_router import router as device_router
from fastapi.middleware.cors import CORSMiddleware
from experiment.experiment_manager import experiment_manager
from contextlib import asynccontextmanager
from logger.logger import logger

@asynccontextmanager
async def lifespan(app):
    # Startup logic
    try:
        experiment_manager.connect_device()
        device = experiment_manager.get_device()
    except Exception as e:
        logger.error(f"Error getting device: {e}")
        device = None
    yield
    # Shutdown logic
    experiment_manager.shutdown()
    
app = FastAPI(lifespan=lifespan, debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment_router)
app.include_router(service_router)
app.include_router(device_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, log_level="debug")