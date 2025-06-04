from fastapi import FastAPI
from fastapi_routes import experiment_routes, service_routes, device_routes
from fastapi.middleware.cors import CORSMiddleware
from experiment.experiment_manager import experiment_manager
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
app.include_router(device_routes.router)

@app.on_event("shutdown")
def shutdown_event():
    try:
        print("Shutting down")
        device = experiment_manager.get_device()
        if hasattr(device, 'eeprom') and hasattr(device.eeprom, 'writer'):
            device.eeprom.writer.stop()
            print("EEPROM writer stopped cleanly.")
        if hasattr(device, 'od_worker') and device.od_worker is not None:
            print("Stopping od_worker thread...")
            device.od_worker.stop()
            print("od_worker stopped cleanly.")
        if hasattr(device, 'dilution_worker') and device.dilution_worker is not None:
            print("Stopping dilution_worker thread...")
            device.dilution_worker.stop()
            print("dilution_worker stopped cleanly.")
    except Exception as e:
        print(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000, reload=True)
