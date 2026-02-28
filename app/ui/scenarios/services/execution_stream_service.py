import json
import threading

import requests

from api_client import API_BASE_URL

_LOCK = threading.RLock()
_EXECUTION_STATES: dict[str, dict] = {}
_LATEST_EXECUTION_BY_SCENARIO: dict[str, str] = {}
_LISTENER_THREADS: dict[str, threading.Thread] = {}


def _new_execution_state(execution_id: str, scenario_id: str) -> dict:
    return {
        "execution_id": execution_id,
        "scenario_id": scenario_id,
        "running": True,
        "status": "running",
        "executed_steps": 0,
        "total_steps": 0,
        "step_status": {},
        "operation_status": {},
        "events": [],
        "error": None,
    }


def _operation_key(scenario_step_id: str, operation_id: str) -> str:
    return f"{scenario_step_id}:{operation_id}"


def _append_event(execution_id: str, event_name: str, data: dict):
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id)
        if not state:
            return
        state["events"].append({"event": event_name, "data": data})
        if len(state["events"]) > 1000:
            state["events"] = state["events"][-1000:]


def _apply_event(execution_id: str, event_name: str, data: dict):
    _append_event(execution_id, event_name, data)
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id)
        if not state:
            return

        if event_name == "execution_started":
            state["running"] = True
            state["status"] = "running"
            state["executed_steps"] = 0
            state["total_steps"] = 0
            return

        if event_name == "execution_progress":
            state["executed_steps"] = int(data.get("executed_steps") or 0)
            state["total_steps"] = int(data.get("total_steps") or 0)
            return

        if event_name == "step_started":
            scenario_step_id = str(data.get("scenario_step_id") or "").strip()
            if scenario_step_id:
                state["step_status"][scenario_step_id] = "running"
            return

        if event_name == "step_finished":
            scenario_step_id = str(data.get("scenario_step_id") or "").strip()
            status = str(data.get("status") or "").strip() or "idle"
            if scenario_step_id:
                state["step_status"][scenario_step_id] = status
            return

        if event_name == "operation_finished":
            scenario_step_id = str(data.get("scenario_step_id") or "").strip()
            operation_id = str(data.get("operation_id") or "").strip()
            status = str(data.get("status") or "").strip() or "idle"
            if scenario_step_id and operation_id:
                state["operation_status"][_operation_key(scenario_step_id, operation_id)] = status
            return

        if event_name == "execution_finished":
            state["running"] = False
            state["status"] = str(data.get("status") or "finished")
            state["executed_steps"] = int(data.get("executed_steps") or state["executed_steps"])
            state["total_steps"] = int(data.get("total_steps") or state["total_steps"])
            return


def _iter_sse_events(response) -> list[tuple[str, dict]]:
    event_name = "message"
    data_lines: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        line = (raw_line or "").strip()
        if not line:
            if data_lines:
                payload_raw = "\n".join(data_lines)
                try:
                    payload = json.loads(payload_raw)
                except json.JSONDecodeError:
                    payload = {"raw": payload_raw}
                yield event_name, payload
            event_name = "message"
            data_lines = []
            continue

        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())


def _listen_execution_events(execution_id: str):
    stream_url = f"{API_BASE_URL}/elaborations/execution/{execution_id}/events"
    try:
        with requests.get(stream_url, timeout=120, stream=True) as response:
            response.raise_for_status()
            for event_name, payload in _iter_sse_events(response):
                _apply_event(execution_id, event_name, payload)
                if event_name == "execution_finished":
                    break
    except Exception as exc:
        with _LOCK:
            state = _EXECUTION_STATES.get(execution_id)
            if state:
                state["running"] = False
                state["status"] = "error"
                state["error"] = str(exc)
    finally:
        with _LOCK:
            _LISTENER_THREADS.pop(execution_id, None)


def register_execution_listener(execution_id: str, scenario_id: str):
    execution_id_value = str(execution_id or "").strip()
    scenario_id_value = str(scenario_id or "").strip()
    if not execution_id_value or not scenario_id_value:
        return

    with _LOCK:
        _LATEST_EXECUTION_BY_SCENARIO[scenario_id_value] = execution_id_value
        if execution_id_value not in _EXECUTION_STATES:
            _EXECUTION_STATES[execution_id_value] = _new_execution_state(
                execution_id=execution_id_value,
                scenario_id=scenario_id_value,
            )
        if execution_id_value in _LISTENER_THREADS:
            return
        listener_thread = threading.Thread(
            target=_listen_execution_events,
            args=(execution_id_value,),
            name=f"execution-sse-{execution_id_value}",
            daemon=True,
        )
        _LISTENER_THREADS[execution_id_value] = listener_thread
    listener_thread.start()


def get_latest_execution_id_for_scenario(scenario_id: str) -> str:
    scenario_id_value = str(scenario_id or "").strip()
    if not scenario_id_value:
        return ""
    with _LOCK:
        return str(_LATEST_EXECUTION_BY_SCENARIO.get(scenario_id_value) or "")


def get_execution_state(execution_id: str) -> dict:
    execution_id_value = str(execution_id or "").strip()
    if not execution_id_value:
        return {}
    with _LOCK:
        state = _EXECUTION_STATES.get(execution_id_value)
        if not state:
            return {}
        return {
            **state,
            "step_status": dict(state.get("step_status") or {}),
            "operation_status": dict(state.get("operation_status") or {}),
            "events": list(state.get("events") or []),
        }


def get_latest_execution_state_for_scenario(scenario_id: str) -> dict:
    execution_id = get_latest_execution_id_for_scenario(scenario_id)
    if not execution_id:
        return {}
    return get_execution_state(execution_id)
