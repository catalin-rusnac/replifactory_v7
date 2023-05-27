#server.py

from waitress import serve
from flask import Flask
from routes.device_routes import device_routes
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import logging
import os
import signal

global dev

# cors
from experiment.models import db
from routes.experiment_routes import experiment_routes

base_dir = os.path.dirname(os.path.abspath(__file__))
pid_file_path = os.path.join(base_dir, "data/flask_app.pid")

def create_app():
    pid = os.getpid()
    with open(pid_file_path, "w+") as pid_file:
        pid_file.write(str(pid))

    app = Flask(__name__)
    app.register_blueprint(device_routes)
    app.register_blueprint(experiment_routes)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../db/replifactory.db'
    db.init_app(app)
    CORS(app)
    @app.route('/shutdown')
    def shutdown():
        print("Shutting down server...")
        with open(pid_file_path, "r") as pid_file:
            pid = int(pid_file.read())
        try:
            dev.disconnect_all()
        except:
            pass
        os.kill(pid, signal.SIGTERM)
    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        logging.info("Starting server...")
        app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
        # serve(app, host="0.0.0.0", port=5000, threads=1)
