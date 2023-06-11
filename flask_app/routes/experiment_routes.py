# experiment_routes.py
import sys
import sqlalchemy

sys.path.insert(0, "../")
from flask import Blueprint, request, jsonify, current_app, send_file
from experiment.models import ExperimentModel, CultureData, db, PumpData, CultureGenerationData
from experiment.experiment import Experiment
from routes.device_routes import connect_device

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
    return jsonify({'id': experiment_model.id, 'name': experiment_model.name}), 201


@experiment_routes.route('/experiments/<string:id>', methods=['GET'])
def get_experiment(id):
    # When id is 0, return default response
    if id == "0":
        return jsonify({'id': 0, 'name': '-----', 'status': 'stopped'})

    # When id is current, return current experiment
    if id == 'current':
        if not hasattr(current_app, 'experiment'):
            return jsonify({'id': None})
        else:
            return jsonify(current_app.experiment.model.to_dict()), 200

    # Check if id can be converted to an integer
    try:
        id = int(id)
    except ValueError:
        return jsonify({'error': 'Invalid experiment ID'}), 400

    # Fetch experiment from database
    experiment_model = db.session.get(ExperimentModel, id)

    # Return 404 if experiment not found
    if not experiment_model:
        return jsonify({'error': 'Experiment not found'}), 404

    # Create a new experiment if not already present
    if not hasattr(current_app, 'experiment'):
        if not hasattr(current_app, 'dev'):
            connect_device()
        current_app.experiment = Experiment(current_app.device, experiment_model, db)

    # If current experiment is different from requested one
    if current_app.experiment.model.id != id:
        # If current experiment is running, stop it
        if current_app.experiment.model.status == 'running':
            current_app.experiment.stop()
            print("WARNING! Stopped existing running experiment", current_app.experiment.model.id)
        # Start the requested experiment
        current_app.experiment = Experiment(current_app.device, experiment_model, db)

    # Return the experiment data
    return jsonify(experiment_model.to_dict()), 200


@experiment_routes.route('/experiments/<int:id>/delete', methods=['GET'])
def delete_experiment(id):
    experiment_model = db.session.get(ExperimentModel, id)
    experiment_data = db.session.query(CultureData).filter(CultureData.experiment_id == id).all()
    pump_data = db.session.query(PumpData).filter(PumpData.experiment_id == id).all()
    culture_generation_data = db.session.query(CultureGenerationData).filter(CultureGenerationData.experiment_id == id).all()
    if experiment_model:
        db.session.delete(experiment_model)

        for culture_data in experiment_data:
            db.session.delete(culture_data)

        for pump_data in pump_data:
            db.session.delete(pump_data)

        for culture_generation_data in culture_generation_data:
            db.session.delete(culture_generation_data)

        db.session.commit()
        return jsonify({'message': 'Experiment deleted successfully'}), 200
    else:
        return jsonify({'error': 'Experiment not found'}), 404


@experiment_routes.route('/experiments', methods=['GET'])
def experiments():
    try:
        experiment_models = db.session.query(ExperimentModel).all()
    except sqlalchemy.exc.OperationalError:
        print("Database not initialized")
        return jsonify({'error': 'Database not initialized'}), 500
    experiments_clean = [{"id": 0, "name": "---- default template ----", "status": "stopped"}]
    for experiment_model in experiment_models:
        experiments_clean.append({'id': experiment_model.id, 'name': experiment_model.name, 'status': experiment_model.status})
    return jsonify(experiments_clean)


@experiment_routes.route('/experiments/current/parameters', methods=['PUT'])
def update_experiment_parameters():
    new_parameters = request.json['parameters']
    if current_app.experiment.model.status == 'running':
        print("Not updating volume parameters of current experiment")
        for k in new_parameters.keys():
            if k != 'cultures':
                new_parameters[k] = current_app.experiment.parameters[k]
    current_app.experiment.parameters = new_parameters
    for c in current_app.experiment.cultures.values():
        c.get_latest_data_from_db()
    return jsonify(current_app.experiment.model.to_dict()), 200

@experiment_routes.route('/experiments/stop_all', methods=['GET'])
def stop_all_experiments():
    experiment_models = db.session.query(ExperimentModel).all()
    for experiment_model in experiment_models:
        if experiment_model.status == 'running':
            experiment_model.status = 'stopped'
            db.session.commit()
    return jsonify({'message': 'All experiments stopped'}), 200


@experiment_routes.route('/experiments/current/status', methods=['PUT'])
def update_experiment_status():
    status = request.json['status']
    if status == 'running':
        running_experiment = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'running').first()
        if running_experiment:
            return jsonify({'error': 'Cannot start experiment, another experiment is already running'+str(running_experiment.__dict__)}), 400
        paused_experiment = db.session.query(ExperimentModel).filter(ExperimentModel.status == 'paused').first()
        if paused_experiment:
            if paused_experiment.id != current_app.experiment.model.id:
                return jsonify({'error': 'Cannot start experiment, another experiment is paused'+str(running_experiment.__dict__)}), 400

    if current_app.experiment:
        if status == 'stopped':
            current_app.experiment.stop()

        device = getattr(current_app, 'device', None)
        if device is None or not device.is_connected():
            try:
                connect_device()
            except Exception as e:
                return jsonify({'error': 'device not connected'}), 400

        if status == 'running':
            current_app.experiment.start()
        elif status == 'paused':
            current_app.experiment.pause_dilution_worker()
        return jsonify({'message': 'Experiment status updated successfully'})
    else:
        return jsonify({'error': 'Experiment not found'}), 404


@experiment_routes.route('/get_info', methods=['GET'])
def get_info():
    try:
        return current_app.experiment.get_info()
    except Exception as e:
        import traceback
        return traceback.format_exc()


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