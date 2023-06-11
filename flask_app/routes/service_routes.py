import os
import socket
import sys
from flask import Blueprint, jsonify, send_file
import cv2
import io

sys.path.insert(0, "../")


service_routes = Blueprint('service_routes', __name__)




@service_routes.route("/capture")
def capture_image():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": "Failed to capture image"}), 500

    _, img_encoded = cv2.imencode('.jpg', frame)
    stream = io.BytesIO(img_encoded.tostring())
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)


@service_routes.route("/picapture")
def capture_image():
    stream = io.BytesIO()
    from picamera import PiCamera
    camera = PiCamera()
    camera.start_preview()
    camera.capture(stream, format='jpeg')
    camera.stop_preview()

    stream.seek(0)
    camera.close()
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)


@service_routes.route('/update_software', methods=['GET'])
def update_software():
    script_path = os.path.dirname(__file__)
    makefile_dir = os.path.join(script_path, "../../")
    import subprocess
    update_log = os.path.join(script_path, "../../logs/update.log")
    # open the log file in write mode, this will overwrite the old log each time
    with open(update_log, "w+") as f:
        command = ["make", "-C", makefile_dir, "update-replifactory"]
        # run the command and redirect stdout and stderr to the log file
        subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT, close_fds=True)

    return jsonify({'message': 'Software updated successfully'})


@service_routes.route('/update_log', methods=['GET'])
def update_log():
    try:
        script_path = os.path.dirname(__file__)
        update_log = os.path.join(script_path, "../../logs/update.log")
        with open(update_log, "r") as f:
            log_content = f.read()
        return jsonify({'update_log': log_content})
    except FileNotFoundError:
        return jsonify({'error': 'Log file not found'}), 404


@service_routes.route('/hostname', methods=['GET'])
def get_hostname():
    hostname = socket.gethostname()
    return jsonify({'hostname': hostname})


@service_routes.route('/download_db', methods=['GET'])
def download_file():
    script_dir = os.path.dirname(__file__)
    rel_path = "../../db/replifactory.db"
    abs_file_path = os.path.join(script_dir, rel_path)
    return send_file(abs_file_path, as_attachment=True)
