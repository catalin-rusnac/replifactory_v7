# see deprecated_routes/camera_routes.py for the old camera routes

from fastapi import APIRouter, Response
import io

router = APIRouter()

@router.get("/camera/capture")
def capture_image():
    # Try Picamera2
    try:
        from picamera2 import Picamera2
        picam2 = Picamera2()
        try:
            config = picam2.create_still_configuration()
            picam2.configure(config)
            picam2.start()
            picam2.capture_file("img.jpg")
        finally:
            picam2.stop()
            picam2.close()
        with open("img.jpg", "rb") as f:
            img_bytes = f.read()
        return Response(content=img_bytes, media_type="image/jpeg")
    except Exception:
        pass
    # Try picamzero
    try:
        from picamzero import Camera
        stream = io.BytesIO()
        camera = Camera()
        camera.capture(stream, format='jpeg')
        camera.close()
        stream.seek(0)
        return Response(content=stream.read(), media_type="image/jpeg")
    except Exception:
        pass
    # Try OpenCV
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return Response(content=b"Failed to capture image", status_code=500)
        _, img_encoded = cv2.imencode('.jpg', frame)
        return Response(content=img_encoded.tobytes(), media_type="image/jpeg")
    except Exception as e:
        return Response(content=f"Camera error: {e}".encode(), status_code=500)
