import os
import socket
import io

import sys

sys.path.insert(0, "../")

from flask import Blueprint, jsonify, send_file

service_routes = Blueprint('service_routes', __name__)



@service_routes.route("/capture")
def capture_image():
    stream = io.BytesIO()
    from picamera import PiCamera
    camera = PiCamera()
    camera.start_preview()
    camera.capture(stream, format='jpeg')
    camera.stop_preview()

    stream.seek(0)
    camera.close()
    return send_file(stream, mimetype='image/jpeg')


@service_routes.route('/update_software', methods=['GET'])
def update_software():
    script_path = os.path.dirname(__file__)
    makefile_dir = os.path.join(script_path, "../../")
    import subprocess

    command = ["make", "-C", makefile_dir, "update-replifactory"]
    subprocess.Popen(command, close_fds=True)
    return jsonify({'message': 'Software updated successfully'})


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
