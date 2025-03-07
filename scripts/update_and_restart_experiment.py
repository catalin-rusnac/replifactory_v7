import time
import requests
import logging
import subprocess
import threading

# Setup logging with timestamp
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
log_file = logging.FileHandler("logs/update_and_restart.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file.setFormatter(formatter)
logger.addHandler(log_file)

current_experiment_id = None
current_experiment_status = None

def get_current_experiment_status():
    url = "http://localhost:5000/experiments/current"
    response = requests.get(url)
    data = response.json()
    if "status" not in data:
        logger.error(f"Error getting experiment status: {data}")
        return None, None
    experiment_status = data["status"]
    experiment_id = data["id"]
    if experiment_status == "running" or experiment_status == "paused":
        global current_experiment_id
        global current_experiment_status
        current_experiment_id = experiment_id
        current_experiment_status = experiment_status
    logger.debug(f"Experiment {experiment_id} is {experiment_status}")
    return experiment_status, experiment_id

def stop_experiment():
    url = "http://localhost:5000/experiments/current/status"
    response = requests.put(url, json={"status": "stopped"})
    print(current_experiment_id)
    logger.debug(f"Stop experiment response: {response.json()}")

def fully_stop_if_running():
    experiment_status, experiment_id = get_current_experiment_status()
    if experiment_status == "running" or experiment_status == "paused":
        logger.info(f"Stopping experiment {experiment_id}")
        stop_experiment()
        time.sleep(2)
        while experiment_status != "stopped":
            experiment_status, experiment_id = get_current_experiment_status()
            time.sleep(2)
            logger.info(f"Experiment {experiment_id} status: {experiment_status}. waiting 2s for it to stop")
        logger.info(f"Experiment {experiment_id} stopped")
    else:
        logger.info("No experiment running")
    return True


def git_pull():
    command = "git reset --hard; git pull"
    logger.debug(f"Running command:\n{command}")
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug(f"Pull result:\n{result.stdout.decode()}\n{result.stderr.decode()}")


def restart_flask_service():
    command = "ps -eo comm,etime,args | grep flask | grep -v grep | head -n 1 | awk '{print $2}'"
    logger.debug(f"Running command:\n{command}")
    result2 = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time_running = result2.stdout.decode().strip()
    logger.debug(f"Time flask service running:\n{time_running}")

#     check if systemctl status flask.service is active
    command = "sudo systemctl status flask.service"
    logger.debug(f"Running command:\n{command}")
    result3 = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.debug(f"Systemctl status result:\n{result3.stdout.decode()}\n{result3.stderr.decode()}")
    # check if systemctl status flask.service is active
    if "active (running)" in result3.stdout.decode():
        command = "sudo systemctl restart flask.service"
        logger.debug(f"Running command:\n{command}")
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.debug("Flask service restarted")
    time.sleep(5)

    for i in range(10):
        command = "sudo systemctl status flask.service"
        logger.debug(f"Running command:\n{command}")
        result5 = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.debug(f"Systemctl status result:\n{result5.stdout.decode()}\n{result5.stderr.decode()}")
        if "active (running)" in result5.stdout.decode():
            logger.info("Flask service restarted successfully")
            return True
        time.sleep(5)

def flask_backend_is_running():
    url = "http://localhost:5000/experiments"
    for attempt in range(20):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                logger.info("Flask backend is running")
                return True
            logger.warning(f"Flask backend is not running yet, attempt: {attempt + 1}")
        except requests.RequestException as e:
            logger.warning(f"Flask backend is not running yet, attempt: {attempt + 1}. Error: {e}")
        time.sleep(2)

    logger.error("Flask backend is not running after 20 attempts")
    return False


def select_experiment(experiment_id=None):
    if experiment_id is None:
        experiment_id = current_experiment_id
    # check that no experiment is running
    existing_experiment_status, existing_experiment_id = get_current_experiment_status() # should be none after flask service restart
    if existing_experiment_status == "running" or existing_experiment_status == "paused":
        logger.error(f"Experiment {existing_experiment_id} is still running")
        return False
    url = f"http://localhost:5000/experiments/{experiment_id}"
    logger.debug(f"Selecting experiment {experiment_id}")
    response = requests.get(url)
    data = response.json()
    logger.debug(f"Selected experiment {data}")
    time.sleep(1)
    return True


def start_current_experiment():
    url = f"http://localhost:5000/experiments/current/status"
    response = requests.put(url, json={"status": "running"})
    if current_experiment_status == "paused":
        response = requests.put(url, json={"status": "paused"})
        logger.info(f"Resume experiment response: {response.json()}")
    logger.info(f"Start experiment response: {response.json()}")

def update_and_restart():
    git_pull()
    fully_stop_if_running()
    restart_flask_service()
    logger.info("Flask service restarted. Waiting for flask backend to start")
    if flask_backend_is_running():
        logger.info("Flask backend is running. Selecting experiment")
        select_experiment()
        logger.info("Experiment selected. Starting experiment")
        start_current_experiment()
    else:
        logger.error("Flask backend is not running. restarting experiment failed")
    logger.info("Update and restart complete")

if __name__ == "__main__":
    update_and_restart()