from fastapi import APIRouter
from fastapi.responses import JSONResponse
import socket

router = APIRouter()

@router.get("/hostname")
def get_hostname():
    hostname = socket.gethostname()
    return JSONResponse(content={"hostname": hostname}) 