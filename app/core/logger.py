import os
import logging
from logging.handlers import RotatingFileHandler

# Create log directory
os.makedirs("logs", exist_ok=True)

# Configure log format
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create file handler
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Configure uvicorn access log
access_logger = logging.getLogger("uvicorn.access")
access_logger.handlers = [file_handler]

# Configure uvicorn error log
error_logger = logging.getLogger("uvicorn.error")
error_logger.handlers = [file_handler]

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger.

    Args:
        name: Logger name.

    Returns:
        Named logger instance.
    """
    return logging.getLogger(name)

# Create default application logger
logger = get_logger("app")