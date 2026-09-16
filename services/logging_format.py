import logging
from datetime import datetime, timezone

class WorkerFormatter(logging.Formatter):
    def format(self, record):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        worker = getattr(record, "worker", "supervisor")
        msg = super().format(record)
        return f"{ts} [{worker}] {record.levelname} {msg}"
