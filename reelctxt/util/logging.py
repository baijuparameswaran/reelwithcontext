import logging

_DEF_FORMAT = "[%(levelname)s] %(asctime)s %(name)s: %(message)s"


def setup_logging(level: str = "INFO"):
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format=_DEF_FORMAT)
