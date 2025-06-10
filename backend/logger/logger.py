import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s %(funcName)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

logger = logging.getLogger("backend")  # Use a project-wide name

# logger to file with max limit of 10mb
simulation_logger = logging.getLogger("simulation")
# simulation_logger.setLevel(logging.INFO)
# simulation_logger.addHandler(logging.handlers.RotatingFileHandler("simulation.log", maxBytes=10*1024*1024, backupCount=10))







