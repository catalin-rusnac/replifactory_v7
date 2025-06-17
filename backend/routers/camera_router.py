# see deprecated_routes/camera_routes.py for the old camera routes

from fastapi import APIRouter, Response
import io
import time
from experiment.experiment_manager import experiment_manager
from logger.logger import logger

router = APIRouter()

@router.get("/camera/capture")
def capture_image():
    """Capture image with singleton lock to prevent concurrent camera access."""
    camera_lock = experiment_manager.get_camera_lock()
    
    with camera_lock:
        logger.info("Camera capture started (with lock)")
        start_time = time.time()
        
        # Try Picamera2
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            try:
                config = picam2.create_still_configuration()
                picam2.configure(config)
                picam2.start()
                time.sleep(0.1)  # Brief stabilization delay
                picam2.capture_file("img.jpg")
            finally:
                picam2.stop()
                picam2.close()
            with open("img.jpg", "rb") as f:
                img_bytes = f.read()
            elapsed = time.time() - start_time
            logger.info(f"Camera capture completed with Picamera2 in {elapsed:.2f}s")
            return Response(content=img_bytes, media_type="image/jpeg")
        except Exception as e:
            logger.warning(f"Picamera2 failed: {e}")
        
        # Try picamzero
        try:
            from picamzero import Camera
            stream = io.BytesIO()
            camera = Camera()
            camera.capture(stream, format='jpeg')
            camera.close()
            stream.seek(0)
            elapsed = time.time() - start_time
            logger.info(f"Camera capture completed with picamzero in {elapsed:.2f}s")
            return Response(content=stream.read(), media_type="image/jpeg")
        except Exception as e:
            logger.warning(f"picamzero failed: {e}")
        
        # Try OpenCV
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                logger.error("OpenCV failed to capture frame")
                return Response(content=b"Failed to capture image", status_code=500)
            _, img_encoded = cv2.imencode('.jpg', frame)
            elapsed = time.time() - start_time
            logger.info(f"Camera capture completed with OpenCV in {elapsed:.2f}s")
            return Response(content=img_encoded.tobytes(), media_type="image/jpeg")
        except Exception as e:
            logger.error(f"OpenCV failed: {e}")
            return Response(content=f"Camera error: {e}".encode(), status_code=500)

@router.post("/camera/reset")
def reset_camera():
    pass