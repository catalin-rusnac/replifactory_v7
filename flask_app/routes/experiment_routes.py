# experiment_routes.py
import sys
import time

import sqlalchemy

sys.path.insert(0, "../")
from flask import Blueprint, request, jsonify, current_app
from experiment.models import ExperimentModel, Culture, ExperimentParameterHistory, CultureParameterHistory, db
from experiment.experiment import default_parameters, Experiment

experiment_routes = Blueprint('experiment_routes', __name__)

@experiment_routes.route('/experiments', methods=['POST'])
def create_experiment():
    experiment_data = request.json
    parameters = experiment_data.get('parameters', {})
    print("got parameters", parameters, "from request" )
    if parameters is None or parameters == {}:
        parameters = default_parameters

    experiment_model = ExperimentModel(name=experiment_data['name'], parameters=parameters)
    db.session.add(experiment_model)
    db.session.commit()
    return jsonify({'id': experiment_model.id}), 201

@experiment_routes.route('/experiments/<int:id>', methods=['GET'])
def get_experiment(id):
    experiment_model = db.session.get(ExperimentModel, id)

    try:
        if current_app.experiment.model.id != id:
            current_app.experiment = Experiment(current_app.dev, experiment_model)
    except Exception:
        current_app.experiment = Experiment(current_app.dev, experiment_model)

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

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:id>', methods=['GET'])
def get_culture(experiment_id, id):
    culture = db.session.get(Culture, id)
    if culture and culture.experiment_id == experiment_id:
        return jsonify(culture.to_dict())
    else:
        return jsonify({'error': 'Culture not found'}), 404

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:id>/parameters', methods=['PUT'])
def update_culture_parameters(experiment_id, id):
    parameters = request.json['parameters']
    culture = db.session.get(Culture, id)
    if culture and culture.experiment_id == experiment_id:
        culture.parameters.update(parameters)
        db.session.commit()
        return jsonify({'message': 'Culture parameters updated successfully'})
    else:
        return jsonify({'error': 'Culture not found'}), 404

# Get all parameter histories for a particular experiment
@experiment_routes.route('/experiments/<int:id>/history', methods=['GET'])
def get_experiment_history(id):
    history = db.session.query(ExperimentParameterHistory).filter_by(experiment_id=id).all()
    if history:
        return jsonify([h.to_dict() for h in history])
    else:
        return jsonify({'error': 'Experiment history not found'}), 404

# Add a new parameter history entry for a particular experiment
@experiment_routes.route('/experiments/<int:id>/history', methods=['POST'])
def add_experiment_history(id):
    history_data = request.json
    history = ExperimentParameterHistory(
        experiment_id=id,
        parameters=history_data['parameters'],
        timestamp=int(time.time())  # Assuming timestamp is not supplied and should be 'now'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'id': history.id}), 201

# Similar routes for CultureParameterHistory...

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:culture_id>/history', methods=['GET'])
def get_culture_history(experiment_id, culture_id):
    history = db.session.query(CultureParameterHistory).filter_by(culture_id=culture_id).all()
    if history:
        return jsonify([h.to_dict() for h in history])
    else:
        return jsonify({'error': 'Culture history not found'}), 404

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:culture_id>/history', methods=['POST'])
def add_culture_history(experiment_id, culture_id):
    history_data = request.json
    history = CultureParameterHistory(
        culture_id=culture_id,
        parameters=history_data['parameters'],
        active_parameters=history_data['active_parameters'],
        timestamp=int(time.time())  # Assuming timestamp is not supplied and should be 'now'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'id': history.id}), 201