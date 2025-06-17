from fastapi import APIRouter
from fastapi.responses import JSONResponse, FileResponse
import socket
import os

router = APIRouter()

@router.get("/hostname")
def get_hostname():
    hostname = socket.gethostname()
    return JSONResponse(content={"hostname": hostname})

@router.get("/download_db")
def download_database():
    """Download the experiment database file."""
    # Use the same path logic as experiment_manager.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'db', 'replifactory.db'))
    
    if not os.path.exists(db_path):
        return JSONResponse(content={"error": "Database file not found"}, status_code=404)
    
    return FileResponse(
        path=db_path,
        filename="replifactory.db",
        media_type="application/octet-stream"
    ) 