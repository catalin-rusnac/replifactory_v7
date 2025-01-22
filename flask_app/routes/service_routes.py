import os
import socket
import sys
import time

from flask import Blueprint, jsonify, send_file
import io

sys.path.insert(0, "../")


service_routes = Blueprint('service_routes', __name__)


@service_routes.route("/capture")
def capture_image():
    try:
        return capture_image_pi()
    except:
        try:
            return capture_image_picamzero()
        except:
            return capture_image_cv2()

@service_routes.route("/capture_picamzero")
def capture_image_picamzero():
    from picamzero import Camera
    stream = io.BytesIO()
    camera = Camera()
    camera.capture(stream, format='jpeg')
    camera.close()
    stream.seek(0)
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)

@service_routes.route("/capture_cv2")
def capture_image_cv2():
    import cv2
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify({"error": "Failed to capture image"}), 500

    _, img_encoded = cv2.imencode('.jpg', frame)
    stream = io.BytesIO(img_encoded.tostring())
    return send_file(stream, mimetype='image/jpeg', as_attachment=False)

@service_routes.route("/capturehires")
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


@service_routes.route("/picapture")
def capture_image_pi():
    from picamera2 import Picamera2
    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)

    picam2.start()
    picam2.capture_file("img.jpg")
    picam2.stop()
    return send_file("img.jpg", mimetype='image/jpeg', as_attachment=False)


from flask import abort

allowed_updates = {"frontend", "backend", "full"}

@service_routes.route('/update/<string:update_type>', methods=['GET'])
def update(update_type):
    if update_type not in allowed_updates:
        abort(400, 'Invalid update type. Must be one of: {}'.format(", ".join(allowed_updates)))

    script_path = os.path.dirname(__file__)
    makefile_dir = os.path.join(script_path, "../../")
    import subprocess
    update_log = os.path.join(script_path, "../../logs/update-{}.log".format(update_type))

    with open(update_log, "w+") as f:
        command = ["make", "-C", makefile_dir, "update-{}".format(update_type)]
        subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT, close_fds=True)

    return jsonify({'message': 'Software update initialized'})

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

@service_routes.route('/download_flask_err', methods=['GET'])
def download_flask_err():
    script_dir = os.path.dirname(__file__)
    rel_path = "../../logs/flask-error.log"
    abs_file_path = os.path.join(script_dir, rel_path)
    return send_file(abs_file_path, as_attachment=True)

@service_routes.route('/download_flask_log', methods=['GET'])
def download_flask():
    script_dir = os.path.dirname(__file__)
    rel_path = "../../logs/flask.log"
    abs_file_path = os.path.join(script_dir, rel_path)
    return send_file(abs_file_path, as_attachment=True)


@service_routes.route('/log/<int:lines>/', methods=['GET'])
def get_log_tail(lines=100):
    script_path = os.path.dirname(__file__)
    log_flask_error = os.path.join(script_path, "../../logs/flask-error.log")
    log_flask = os.path.join(script_path, "../../logs/flask.log")
    log_express = os.path.join(script_path, "../../logs/express_server.log")
    log_express_error = os.path.join(script_path, "../../logs/express_server-error.log")
    import subprocess
    d={}
    for file in [log_flask_error, log_flask, log_express, log_express_error]:
        try:
            command = ["tail", "-n", str(lines), file]
            result = subprocess.run(command, stdout=subprocess.PIPE)
            if result.returncode == 0:
                d[file] = result.stdout.decode('utf-8')
        except:
            # windows
            command = ["powershell", "Get-Content", file, "-Tail", str(lines)]
            result = subprocess.run(command, stdout=subprocess.PIPE)
            if result.returncode == 0:
                d[file] = result.stdout.decode('utf-8')
            else:
                d[file] = "Error reading file"
    return jsonify(d)


# route to export csv of current experiment database
@service_routes.route('/export_csv', methods=['GET'])
def export_csv():
    return jsonify(current_app.experiment.model.to_dict()), 200

    # get all experiments from database
    experiments = db_session.query(Experiment).all()

    # create dataframe from experiments
    df = pd.DataFrame([exp.to_dict() for exp in experiments])

    # convert dataframe to csv
    csv = df.to_csv(index=False)

    # create response object
    response = Response(csv, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=export.csv'

    return response


@service_routes.route('/exec/<string:command>', methods=['GET'])
def execute_command(command):
    import subprocess
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, shell=True)
        if result.returncode == 0:
            return jsonify({'output': result.stdout.decode('utf-8')}), 200
        else:
            return jsonify({'error running '+command: result.stdout.decode('utf-8')}), 500
    except:
        return jsonify({'error': 'Failed to execute command: '+command}), 500


@service_routes.route('/update_and_restart_experiment', methods=['PUT'])
def update_and_restart_experiment():
    import subprocess
    command = "make update_and_restart_experiment &"
    result = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 0:
        return jsonify({'output': result.stdout.decode('utf-8')}), 200
    else:
        return jsonify({'error running '+command: result.stdout.decode('utf-8')}), 500
    return jsonify({'message': 'Update and restart initialized'})