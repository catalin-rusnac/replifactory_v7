# experiment_routes.py
import os
import socket
import sys
import time

import sqlalchemy

sys.path.insert(0, "../")
from flask import Blueprint, request, jsonify, current_app, send_file
from experiment.models import ExperimentModel, CultureData, db
from experiment.experiment import Experiment

experiment_routes = Blueprint('experiment_routes', __name__)


@experiment_routes.route('/experiments', methods=['POST'])
def create_experiment():
    experiment_data = request.json
    parameters = experiment_data.get('parameters', {})
    if parameters == {} or parameters is None:
        experiment_model = ExperimentModel(name=experiment_data['name'])
    else:
        experiment_model = ExperimentModel(name=experiment_data['name'], parameters=parameters)
    db.session.add(experiment_model)
    db.session.commit()
    return jsonify({'id': experiment_model.id}), 201

@experiment_routes.route('/experiments/<int:id>', methods=['GET'])
def get_experiment(id):
    experiment_model = db.session.get(ExperimentModel, id)
    try:
        if current_app.experiment.model.id != id:
            if current_app.experiment.model.status == 'running':
                current_app.experiment.stop()
                print("WARNING! Stopped existing running experiment", current_app.experiment.model.id)
            current_app.experiment = Experiment(current_app.dev, experiment_model, db)
    except Exception:
        current_app.experiment = Experiment(current_app.dev, experiment_model, db)

    if experiment_model:
        return jsonify(experiment_model.to_dict())
    else:
        return jsonify({'error': 'Experiment not found'}), 404

@experiment_routes.route('/experiments', methods=['GET'])
def get_experiments():
    try:
        experiment_models = db.session.query(ExperimentModel).all()
    except sqlalchemy.exc.OperationalError:
        print("Database not initialized")
        return jsonify([])
    experiments_clean = []
    for experiment_model in experiment_models:
        experiments_clean.append({'id': experiment_model.id, 'name': experiment_model.name, 'status': experiment_model.status})
    return jsonify(experiments_clean)


@experiment_routes.route('/experiments/current', methods=['GET'])
def get_current_experiment():
    experiment_model = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'running').first()
    if not experiment_model:
        experiment_model = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'paused').first()
    if experiment_model:
        return jsonify(experiment_model.to_dict())
    else:
        return jsonify({"id": None})


@experiment_routes.route('/experiments/<int:id>/parameters', methods=['PUT'])
def update_experiment_parameters(id):
    parameters = request.json['parameters']
    experiment_model = db.session.get(ExperimentModel, id)
    print("Updating experiment_model parameters", id, parameters)
    if experiment_model:
        experiment_model.parameters = parameters
        db.session.commit()
        return jsonify({'message': 'Experiment parameters updated successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404


@experiment_routes.route('/experiments/<int:id>/status', methods=['PUT'])
def update_experiment_status(id):
    status = request.json['status']
    if status == 'running':
        running_experiment = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'running').first()
        if running_experiment:
            return jsonify({'error': 'Cannot start experiment, another experiment is already running'}), 400
        paused_experiment = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'paused').first()
        if paused_experiment:
            if paused_experiment.id != id:
                return jsonify({'error': 'Cannot start experiment, another experiment is paused'}), 400
    experiment_model = db.session.get(ExperimentModel, id)

    if experiment_model:
        experiment_model.status = status
        db.session.commit()

        if current_app.experiment.model.id == id:
            if status == 'running':
                current_app.experiment.start()
            elif status == 'paused':
                current_app.experiment.pause_dilution_worker()
            elif status == 'stopped':
                current_app.experiment.stop()

        return jsonify({'message': 'Experiment status updated successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404


@experiment_routes.route('/experiments/<int:id>', methods=['DELETE'])
def delete_experiment(id):
    experiment_model = db.session.get(ExperimentModel, id)
    if experiment_model:
        db.session.delete(experiment_model)
        db.session.commit()
        return jsonify({'message': 'Experiment deleted successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404


@experiment_routes.route('/hostname', methods=['GET'])
def get_hostname():
    hostname = socket.gethostname()
    return jsonify({'hostname': hostname})


@experiment_routes.route('/download_db', methods=['GET'])
def download_file():
    script_dir = os.path.dirname(__file__)
    rel_path = "../../db/replifactory.db"
    abs_file_path = os.path.join(script_dir, rel_path)
    return send_file(abs_file_path, as_attachment=True)


@experiment_routes.route('/update_software', methods=['GET'])
def update_software():
    os.system("git pull")
    script_path = os.path.dirname(__file__)
    makefile_dir = os.path.join(script_path, "../../")
    os.system("make -C " + makefile_dir + " install")
    os.system("make -C " + makefile_dir + " kill")
    return jsonify({'message': 'Software updated successfully'})


@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:id>', methods=['GET'])
def get_culture_data(experiment_id, id):
    culture = db.session.get(CultureData, id)
    if culture and culture.experiment_id == experiment_id:
        return jsonify(culture.to_dict())
    else:
        return jsonify({'error': 'Culture not found'}), 404


@experiment_routes.route('/plot/<int:vial>', methods=['GET'])
def get_culture_plot(vial):
    fig=current_app.experiment.cultures[vial].plot()
    fig_json = fig.to_json()
    return jsonify(fig_json)