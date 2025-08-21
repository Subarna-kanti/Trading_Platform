import logging
from logging.handlers import RotatingFileHandler
import os


# ---- Logging setup ----
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# File paths
info_log_file = os.path.join(LOG_DIR, "app_info.log")
error_log_file = os.path.join(LOG_DIR, "app_error.log")

# Create handlers
info_handler = RotatingFileHandler(info_log_file, maxBytes=5*1024*1024, backupCount=5)
info_handler.setLevel(logging.DEBUG)   # will include DEBUG + INFO + WARNING

error_handler = RotatingFileHandler(error_log_file, maxBytes=5*1024*1024, backupCount=5)
error_handler.setLevel(logging.ERROR)  # only ERROR + CRITICAL

console_handler = logging.StreamHandler()  # keep showing in terminal
console_handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
info_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Root logger
logger = logging.getLogger("backend")
logger.setLevel(logging.DEBUG)  # capture everything
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

