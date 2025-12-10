import logging, sys, json
from datetime import datetime
from core.config import settings

class JSONFormatter(logging.Formatter):
    def format(self, record):
        data={"timestamp":datetime.utcnow().isoformat()+"Z","level":record.levelname,
              "logger":record.name,"message":record.getMessage()}
        if hasattr(record,"run_id"): data["run_id"]=record.run_id
        if hasattr(record,"agent"): data["agent"]=record.agent
        return json.dumps(data)

def get_logger(name):
    logger=logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(settings.LOG_LEVEL)
        h=logging.StreamHandler(sys.stdout)
        if settings.ENV=="production":
            h.setFormatter(JSONFormatter())
        else:
            h.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(h)
    return logger
