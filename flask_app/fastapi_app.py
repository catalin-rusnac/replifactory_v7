import logging
from fastapi import FastAPI
from fastapi_routes import experiment_routes, service_routes, device_routes
from fastapi.middleware.cors import CORSMiddleware
from experiment.experiment_manager import experiment_manager
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s %(funcName)s %(message)s',
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    # Startup logic
    logger.info("Connecting to device...")
    experiment_manager.connect_device()
    logger.info("Device connected.")
    yield
    # Shutdown logic
    try:
        logger.info("Shutting down")
        device = experiment_manager.get_device()
        if hasattr(device, 'eeprom') and hasattr(device.eeprom, 'writer'):
            device.eeprom.writer.stop()
            logger.info("EEPROM writer stopped cleanly.")
        if hasattr(device, 'od_worker') and device.od_worker is not None:
            logger.info("Stopping od_worker thread...")
            device.od_worker.stop()
            logger.info("od_worker stopped cleanly.")
        if hasattr(device, 'dilution_worker') and device.dilution_worker is not None:
            logger.info("Stopping dilution_worker thread...")
            device.dilution_worker.stop()
            logger.info("dilution_worker stopped cleanly.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment_routes.router)
app.include_router(service_routes.router)
app.include_router(device_routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000)