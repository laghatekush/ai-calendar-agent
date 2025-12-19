import logging
import sys
import json
from datetime import datetime


def setup_logger(name: str) -> logging.Logger:
    """Setup simple JSON logger"""
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear any existing handlers
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Simple formatter - just output as is
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


class TimestampedLogger:
    """Logger wrapper that outputs JSON"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def info(self, message, **kwargs):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': message,
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
    
    def error(self, message, **kwargs):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': message,
            **kwargs
        }
        self.logger.error(json.dumps(log_data))
    
    def warning(self, message, **kwargs):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': 'WARNING',
            'message': message,
            **kwargs
        }
        self.logger.warning(json.dumps(log_data))