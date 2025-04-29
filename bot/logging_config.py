import logging
import os
from pythonjsonlogger import jsonlogger
from datetime import datetime

def setup_logging():
    """Configure logging for the application"""
    logger = logging.getLogger()
    logHandler = logging.StreamHandler()
    
    # Use JSON formatter if on Render
    if os.environ.get('RENDER'):
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    
    # Create file handler if not on Render
    if not os.environ.get('RENDER'):
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler(
            f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def log_resource_usage():
    """Log system resource usage"""
    import psutil
    
    logger = logging.getLogger('resource-monitor')
    process = psutil.Process()
    
    memory = process.memory_info()
    cpu_percent = process.cpu_percent()
    
    logger.info(
        'Resource usage',
        extra={
            'memory_rss_mb': memory.rss / (1024 * 1024),
            'memory_vms_mb': memory.vms / (1024 * 1024),
            'cpu_percent': cpu_percent,
            'threads': len(process.threads())
        }
    )
