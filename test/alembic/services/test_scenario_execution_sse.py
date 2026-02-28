import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.elaborations.api.scenarios_api import (
    execute_scenario_api,
    execute_scenario_step_api,
)
from app.elaborations.models.dtos.execute_scenario_step_dto import ExecuteScenarioStepDto
from app.elaborations.services.scenarios.execution_event_bus import (
    publish_execution_event,
    stream_execution_events,
)
from app.elaborations.services.scenarios.scenario_executor_thread import (
    _resolve_steps_to_execute,
)
from exceptions.app_exception import QsmithAppException


def _step(step_id: str):
    return SimpleNamespace(id=step_id)


def test_resolve_steps_to_execute_single_step():
    steps = [_step("s1"), _step("s2"), _step("s3")]
    resolved = _resolve_steps_to_execute(
        steps,
        target_scenario_step_id="s2",
        include_previous=False,
    )
    assert [item.id for item in resolved] == ["s2"]


def test_resolve_steps_to_execute_with_previous_steps():
    steps = [_step("s1"), _step("s2"), _step("s3")]
    resolved = _resolve_steps_to_execute(
        steps,
        target_scenario_step_id="s2",
        include_previous=True,
    )
    assert [item.id for item in resolved] == ["s1", "s2"]


def test_resolve_steps_to_execute_raises_when_missing_target():
    steps = [_step("s1"), _step("s2")]
    with pytest.raises(QsmithAppException, match="Scenario step with id 'missing-step' not found"):
        _resolve_steps_to_execute(
            steps,
            target_scenario_step_id="missing-step",
            include_previous=False,
        )


def test_stream_execution_events_replays_history_and_finishes():
    execution_id = f"exec-{uuid4().hex[:8]}"
    publish_execution_event(execution_id, "execution_started", {"scenario_id": "sc-1"})
    publish_execution_event(execution_id, "execution_finished", {"status": "success"})

    stream = stream_execution_events(execution_id)
    first = next(stream)
    second = next(stream)
    stream.close()

    assert "event: execution_started" in first
    assert "event: execution_finished" in second


def test_execute_scenario_api_returns_execution_id(monkeypatch):
    monkeypatch.setattr(
        "app.elaborations.api.scenarios_api.execute_scenario_by_id",
        lambda _scenario_id: "exec-123",
    )
    response = asyncio.run(execute_scenario_api("scenario-1"))
    assert response == {"message": "Scenario started", "execution_id": "exec-123"}


def test_execute_scenario_step_api_returns_execution_id(monkeypatch):
    calls: list[dict] = []

    def _fake_execute_scenario_step_by_id(scenario_id: str, scenario_step_id: str, include_previous: bool):
        calls.append(
            {
                "scenario_id": scenario_id,
                "scenario_step_id": scenario_step_id,
                "include_previous": include_previous,
            }
        )
        return "exec-step-456"

    monkeypatch.setattr(
        "app.elaborations.api.scenarios_api.execute_scenario_step_by_id",
        _fake_execute_scenario_step_by_id,
    )
    response = asyncio.run(
        execute_scenario_step_api(
            "scenario-1",
            "scenario-step-10",
            ExecuteScenarioStepDto(include_previous=True),
        )
    )
    assert response == {"message": "Scenario step started", "execution_id": "exec-step-456"}
    assert calls == [
        {
            "scenario_id": "scenario-1",
            "scenario_step_id": "scenario-step-10",
            "include_previous": True,
        }
    ]
