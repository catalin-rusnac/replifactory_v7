import os
import time
from datetime import datetime
from flask import Blueprint, jsonify, send_file, current_app, Response
import io
import subprocess
# import cv2
# import torch
import site
from picamera2 import Picamera2
# from picamera2.encoders import H264Encoder
# from repleye.vial_detection import detect_vial
# from repleye.volume_estimation.src import estimate
# from repleye.volume_estimation.src.model import VolumeEstimator
from .vision import capture_and_process_image, process_frame
import numpy as np

camera_routes = Blueprint('camera_routes', __name__)

# Global camera instances
camera = None
stream_camera = None

# Load models
site_packages = site.getsitepackages()[0]
YOLO_WEIGHTS = os.path.join(site_packages, 'repleye', 'vial_detection', 'models', 'model_03_05_25.pt')
VOLUME_WEIGHTS = os.path.join(site_packages, 'repleye', 'volume_estimation', 'models', 'model_2024_11_24.pth')

'''
try:
    print(f"Loading YOLO model from: {YOLO_WEIGHTS}")
    yolo_model = torch.hub.load('ultralytics/yolov5', 'custom', path=YOLO_WEIGHTS, force_reload=True)
    print("YOLO model loaded successfully")
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    raise

try:
    print(f"Loading volume model from: {VOLUME_WEIGHTS}")
    volume_model = VolumeEstimator()
    volume_model.load_state_dict(torch.load(VOLUME_WEIGHTS))
    volume_model.eval()
    print("Volume model loaded successfully")
except Exception as e:
    print(f"Error loading volume model: {e}")
    raise
'''

def init_camera():
    global camera
    if camera is None:
        try:
            camera = Picamera2()
            config = camera.create_still_configuration()
            camera.configure(config)
            camera.start()
            time.sleep(2)  # Give camera time to start
            return True
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    return True

def init_stream_camera():
    global stream_camera
    if stream_camera is None:
        try:
            stream_camera = Picamera2()
            config = stream_camera.create_preview_configuration(
                raw={"size": (2592, 1944)},  # Full sensor size
                main={"size": (1920, 1080)}  # Output at 1080p
            )
            stream_camera.configure(config)
            stream_camera.start()
            time.sleep(2)  # Give camera time to start
            return True
        except Exception as e:
            print(f"Error initializing stream camera: {e}")
            return False
    return True

def get_frame():
    global camera
    if not init_camera():
        return None
    
    try:
        # Capture frame
        camera.capture_file("frame.jpg")
        frame = cv2.imread("frame.jpg")
        
        # Convert frame to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()
    except Exception as e:
        print(f"Error capturing frame: {e}")
        return None

def get_stream_frame():
    global stream_camera
    if not init_stream_camera():
        return None
    
    try:
        # Capture frame using the main stream for full resolution
        frame = stream_camera.capture_array("main")
        
        # Convert frame to JPEG with high quality
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buffer.tobytes()
    except Exception as e:
        print(f"Error capturing stream frame: {e}")
        return None

@camera_routes.route('/camera/stream')
def stream():
    def generate():
        while True:
            frame = get_stream_frame()
            if frame is not None:
                # Convert bytes to numpy array
                nparr = np.frombuffer(frame, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Process frame with segmentation - commented out since it uses PyTorch
                # try:
                #     frame = process_frame(frame)
                # except Exception as e:
                #     print(f"Error processing frame: {e}")
                
                # Convert back to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)  # Limit to ~10 FPS
            
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@camera_routes.route("/camera/capture")
def capture_image():
    try:
        return capture_image_pi()
    except:
        try:
            return capture_image_picamzero()
        except:
            return capture_image_cv2()

@camera_routes.route("/camera/capture_picamzero")
def capture_image_picamzero():
    from picamzero import Camera
    stream = io.BytesIO()
    camera = Camera()
    camera.capture(stream, format='jpeg')
    camera.close()
    stream.seek(0)
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)

@camera_routes.route("/camera/capture_cv2")
def capture_image_cv2():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": "Failed to capture image"}), 500

    _, img_encoded = cv2.imencode('.jpg', frame)
    stream = io.BytesIO(img_encoded.tostring())
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)

@camera_routes.route("/camera/capturehires")
def capture_image_hq():
    from picamera import PiCamera
    stream = io.BytesIO()
    camera = PiCamera()
    camera.resolution = (2592, 1944)
    camera.start_preview()
    time.sleep(2)
    camera.capture(stream, format='jpeg')
    camera.stop_preview()

    stream.seek(0)
    camera.close()
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)

@camera_routes.route("/camera/picapture")
def capture_image_pi():
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
    return send_file("img.jpg", mimetype='image/jpeg', as_attachment=False)

@camera_routes.route('/camera/video/<int:duration>', methods=['GET'])
def capture_video(duration):
    camera = None
    try:
        # Initialize the camera
        camera = Picamera2()
        
        # Configure with full raw sensor size and 1920x1080 output
        camera.configure(camera.create_video_configuration(
            raw={"size": (2592, 1944)},  # Full sensor size
            main={"size": (1920, 1080)}  # Output at 1920x1080
        ))
        
        # Generate filenames
        timestamp = datetime.now().strftime('%d_%m_%Y')
        h264_filename = f"video_{timestamp}.h264"
        mp4_filename = f"video_{timestamp}.mp4"
        h264_path = os.path.join(current_app.root_path, h264_filename)
        mp4_path = os.path.join(current_app.root_path, mp4_filename)
        
        # Create encoder and start recording
        encoder = H264Encoder(bitrate=20000000)  # 20Mbps for high quality
        camera.start_recording(encoder, h264_path)
        
        # Record for specified duration
        time.sleep(duration)
        
        # Stop recording
        camera.stop_recording()
        
        # Convert to MP4
        subprocess.run(['ffmpeg', '-y', '-i', h264_path, '-c:v', 'copy', mp4_path], check=True)
        os.remove(h264_path)  # Clean up H264 file
        
        # Send the MP4 file
        return send_file(
            mp4_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=mp4_filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if camera:
            camera.stop()
            camera.close()
        # Clean up MP4 file
        try:
            if 'mp4_path' in locals():
                os.remove(mp4_path)
        except:
            pass

@camera_routes.route("/camera/video/stop", methods=['POST'])
def stop_video():
    try:
        picam2 = Picamera2()
        picam2.stop_recording()
        picam2.close()
        return jsonify({'message': 'Recording stopped successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@camera_routes.route('/camera/reset', methods=['POST'])
def reset_camera():
    try:
        # Force camera cleanup
        subprocess.run(['sudo', 'systemctl', 'restart', 'camera'], check=True)
        time.sleep(2)  # Wait for camera to restart
        return jsonify({'message': 'Camera reset successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@camera_routes.route("/camera/segment", methods=['GET'])
def segment_image():
    return jsonify({'error': 'Segmentation is currently disabled'})
    '''
    try:
        # Capture and process image using vision module
        frame = capture_and_process_image()
        
        # Convert to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        stream = io.BytesIO(buffer.tobytes())
        stream.seek(0)
        
        return send_file(stream, mimetype='image/jpeg', as_attachment=False)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    '''

@camera_routes.route('/camera/force_reset', methods=['POST'])
def force_reset_camera():
    global picam2, is_streaming
    try:
        # First try to stop any existing camera
        cleanup_camera()
        
        # Stop camera service
        subprocess.run(['sudo', 'systemctl', 'stop', 'camera'], check=False)
        time.sleep(1)
        
        # Kill any remaining camera processes
        subprocess.run(['sudo', 'pkill', '-f', 'camera'], check=False)
        time.sleep(1)
        
        # Restart camera service
        subprocess.run(['sudo', 'systemctl', 'restart', 'camera'], check=True)
        time.sleep(2)
        
        # Try to initialize camera
        if init_camera():
            return jsonify({'message': 'Camera force reset successful'})
        else:
            return jsonify({'error': 'Camera initialization failed after reset'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Camera force reset failed: {str(e)}'}), 500 