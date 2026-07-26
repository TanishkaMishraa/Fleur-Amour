"""AuraFit — Virtual Try-On service logging."""
import structlog

def get_logger(name: str):
    return structlog.get_logger(name)
