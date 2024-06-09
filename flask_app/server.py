#server.py

import sys
import os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))  # add dir to python path for flask-migrate

from waitress import serve
from flask import Flask, current_app
from routes.device_routes import device_routes, connect_device

from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import os
import signal

from experiment.database_models import db
from routes.experiment_routes import experiment_routes
from routes.service_routes import service_routes

base_dir = os.path.dirname(os.path.abspath(__file__))
pid_file_path = os.path.join(base_dir, "data/flask_app.pid")


def create_app():
    pid = os.getpid()
    with open(pid_file_path, "w+") as pid_file:
        pid_file.write(str(pid))

    app = Flask(__name__)
    app.register_blueprint(device_routes)
    app.register_blueprint(experiment_routes)
    app.register_blueprint(service_routes)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '../db/replifactory.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'


    db.init_app(app)
    migrate = Migrate(app, db)

    with app.app_context():
        db.create_all()
        # connect_device()  # connect to device on startup
    CORS(app)

    @app.route('/shutdown')
    def shutdown():
        print("Shutting down server...")
        with open(pid_file_path, "r") as pid_file:
            pid = int(pid_file.read())
        try:
            current_app.device.disconnect_all()
        except:
            pass
        os.kill(pid, signal.SIGTERM)
    return app


def main():
    development = len(sys.argv) > 1 and sys.argv[1] == 'develop'

    app = create_app()
    with app.app_context():
        logging.info("Starting server...")
        if development:
            app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=True)
        else:
            serve(app, host="0.0.0.0", port=5000, threads=4)


if __name__ == '__main__':
    main()

