import logging
import os
import threading

from elaborations.services.test_suite_schedules.test_suite_scheduler_service import (
    process_due_schedules,
)


_LOGGER = logging.getLogger("qsmith.scheduler")
_THREAD: threading.Thread | None = None
_STOP_EVENT = threading.Event()
_START_LOCK = threading.Lock()


def _scheduler_poll_seconds() -> float:
    raw_value = str(os.getenv("QSMITH_SCHEDULER_POLL_SECONDS", "15")).strip()
    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        return 15.0


def _scheduler_enabled() -> bool:
    return str(os.getenv("QSMITH_SCHEDULER_ENABLED", "true")).strip().lower() not in {
        "0",
        "false",
        "no",
    }


def _scheduler_loop():
    while not _STOP_EVENT.is_set():
        try:
            process_due_schedules()
        except Exception:
            _LOGGER.exception("scheduler loop iteration failed")
        _STOP_EVENT.wait(_scheduler_poll_seconds())


def bootstrap_scheduler_runtime():
    global _THREAD
    if not _scheduler_enabled():
        _LOGGER.info("scheduler runtime disabled by environment")
        return

    with _START_LOCK:
        if _THREAD and _THREAD.is_alive():
            return
        _STOP_EVENT.clear()
        _THREAD = threading.Thread(
            target=_scheduler_loop,
            name="qsmith-scheduler",
            daemon=True,
        )
        _THREAD.start()


def shutdown_scheduler_runtime():
    global _THREAD
    with _START_LOCK:
        _STOP_EVENT.set()
        if _THREAD and _THREAD.is_alive():
            _THREAD.join(timeout=2.0)
        _THREAD = None
