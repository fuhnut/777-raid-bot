from logging import (
    getLogRecordFactory,
    setLogRecordFactory
)
from os import getpid
from psutil import Process
from coloredlogs import install

def setup():
    factory = getLogRecordFactory()

    def create_record(*args, **kwargs):
        record = factory(*args, **kwargs)
        proc = Process(getpid())
        ram = proc.memory_info().rss / 1024 / 1024
        record.ram = f"{ram:.2f} MB"
        return record

    setLogRecordFactory(create_record)
    styles = {
        "info": {"color": "green"},
        "warning": {"color": "yellow"},
        "error": {"color": "red"}
    }
    install(
        level="INFO",
        fmt="[%(ram)s] %(levelname)s: %(message)s",
        level_styles=styles
    )
