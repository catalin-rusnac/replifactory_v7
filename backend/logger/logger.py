import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s %(funcName)s %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

logger = logging.getLogger("backend")  # Use a project-wide name
