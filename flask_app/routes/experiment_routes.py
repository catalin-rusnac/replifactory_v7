# experiment_routes.py
import sys
sys.path.insert(0, "../")
from flask import Blueprint, request, jsonify
from experiment.models import Experiment, Culture, ExperimentParameterHistory, CultureParameterHistory, db
import datetime
experiment_routes = Blueprint('experiment_routes', __name__)


@experiment_routes.route('/experiments', methods=['POST'])
def create_experiment():
    experiment_data = request.json
    experiment = Experiment(name=experiment_data['name'], parameters=experiment_data['parameters'])
    db.session.add(experiment)
    db.session.commit()
    return jsonify({'id': experiment.id}), 201

@experiment_routes.route('/experiments/<int:id>', methods=['GET'])
def get_experiment(id):
    experiment = db.session.get(Experiment, id)
    if experiment:
        return jsonify(experiment.to_dict())
    else:
        return jsonify({'error': 'Experiment not found'}), 404

@experiment_routes.route('/experiments', methods=['GET'])
def get_experiments():
    experiments = Experiment.query.all()
    return jsonify([experiment.to_dict() for experiment in experiments])

@experiment_routes.route('/experiments/<int:id>/parameters', methods=['PUT'])
def update_experiment_parameters(id):
    parameters = request.json['parameters']
    experiment = db.session.get(Experiment, id)
    if experiment:
        experiment.parameters.update(parameters)
        db.session.commit()
        return jsonify({'message': 'Experiment parameters updated successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404

@experiment_routes.route('/experiments/<int:id>/status', methods=['PUT'])
def update_experiment_status(id):
    status = request.json['status']
    experiment = Experiment.query.get(id)
    if experiment:
        experiment.status = status
        db.session.commit()
        return jsonify({'message': 'Experiment status updated successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404

@experiment_routes.route('/experiments/<int:id>', methods=['DELETE'])
def delete_experiment(id):
    experiment = Experiment.query.get(id)
    if experiment:
        db.session.delete(experiment)
        db.session.commit()
        return jsonify({'message': 'Experiment deleted successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:id>', methods=['GET'])
def get_culture(experiment_id, id):
    culture = Culture.query.get(id)
    if culture and culture.experiment_id == experiment_id:
        return jsonify(culture.to_dict())
    else:
        return jsonify({'error': 'Culture not found'}), 404

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:id>/parameters', methods=['PUT'])
def update_culture_parameters(experiment_id, id):
    parameters = request.json['parameters']
    culture = Culture.query.get(id)
    if culture and culture.experiment_id == experiment_id:
        culture.parameters.update(parameters)
        db.session.commit()
        return jsonify({'message': 'Culture parameters updated successfully'})
    else:
        return jsonify({'error': 'Culture not found'}), 404

# Get all parameter histories for a particular experiment
@experiment_routes.route('/experiments/<int:id>/history', methods=['GET'])
def get_experiment_history(id):
    history = ExperimentParameterHistory.query.filter_by(experiment_id=id).all()
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
        timestamp=datetime.utcnow()  # Assuming timestamp is not supplied and should be 'now'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'id': history.id}), 201

# Similar routes for CultureParameterHistory...

@experiment_routes.route('/experiments/<int:experiment_id>/cultures/<int:culture_id>/history', methods=['GET'])
def get_culture_history(experiment_id, culture_id):
    history = CultureParameterHistory.query.filter_by(culture_id=culture_id).all()
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
        timestamp=datetime.utcnow()  # Assuming timestamp is not supplied and should be 'now'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'id': history.id}), 201