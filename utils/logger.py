import logging
import coloredlogs
import psutil
import os

def setup():
    factory = logging.getLogRecordFactory()

    def create_record(*args, **kwargs):
        record = factory(*args, **kwargs)
        proc = psutil.Process(os.getpid())
        ram = proc.memory_info().rss / 1024 / 1024
        record.ram = f"{ram:.2f} MB"
        return record

    logging.setLogRecordFactory(create_record)
    styles = {
        "info": {"color": "green"},
        "warning": {"color": "yellow"},
        "error": {"color": "red"}
    }
    coloredlogs.install(
        level="INFO",
        fmt="[%(ram)s] %(levelname)s: %(message)s",
        level_styles=styles
    )
