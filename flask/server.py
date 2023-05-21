from waitress import serve
from flask import Flask, request, jsonify, render_template, make_response, current_app
from routes.device_routes import device_routes
from routes.experiment_routes import experiment_routes

# cors
from flask_cors import CORS
import logging
import os
import signal

app = Flask(__name__)
app.register_blueprint(device_routes)

CORS(app)
global dev

pid = os.getpid()
with open("data/flask_app.pid", "w") as pid_file:
    pid_file.write(str(pid))


def shutdown_server():
    with open("data/flask_app.pid", "r") as pid_file:
        pid = int(pid_file.read())
    try:
        dev.disconnect_all()
    except:
        pass
    os.kill(pid, signal.SIGTERM)

@app.get('/shutdown')
def shutdown():
    print("Shutting down server...")
    shutdown_server()


if __name__ == '__main__':
    logging.info("Starting server...")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    # serve(app, host="0.0.0.0", port=5000, threads=1)