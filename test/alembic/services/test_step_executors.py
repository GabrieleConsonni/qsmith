import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from docker.errors import DockerException
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.postgres import PostgresContainer

from app._alembic.models.json_payload_entity import JsonPayloadEntity
from app._alembic.models.scenario_entity import ScenarioEntity
from app._alembic.models.scenario_step_entity import ScenarioStepEntity
from app._alembic.models.step_entity import StepEntity
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.api.scenarios_step_api import (
    delete_scenario_step_api,
    find_all_by_scenario_api,
)
from app.elaborations.api.steps_api import insert_step_api, update_step_api
from app.elaborations.models.dtos.configuration_step_dtos import (
    DataConfigurationStepDTO,
    DataFromDbConfigurationStepDto,
    DataFromJsonArrayConfigurationStepDto,
    DataFromQueueConfigurationStepDto,
    SleepConfigurationStepDto,
)
from app.elaborations.models.dtos.create_step_dto import CreateStepDto
from app.elaborations.models.dtos.update_step_dto import UpdateStepDto
from app.elaborations.models.enums.step_type import StepType
from app.elaborations.services.alembic.scenario_service import ScenarioService
from app.elaborations.services.alembic.scenario_step_service import ScenarioStepService
from app.elaborations.services.alembic.step_service import StepService
from app.elaborations.services.operations.operation_executor import ExecutionResultDto
from app.elaborations.services.steps.data_from_db_step_executor import (
    DataFromDbStepExecutor,
)
from app.elaborations.services.steps.data_from_json_array_step_executor import (
    DataFromJsonArrayStepExecutor,
)
from app.elaborations.services.steps.data_from_queue_step_executor import (
    DataFromQueueStepExecutor,
)
from app.elaborations.services.steps.data_step_executor import DataStepExecutor
from app.elaborations.services.steps.sleep_step_executor import SleepStepExecutor
from app.json_utils.models.enums.json_type import JsonType
from app.json_utils.services.alembic.json_files_service import JsonFilesService


def _start_container_or_skip(container, name: str):
    try:
        return container.start()
    except (DockerException, ContainerStartException) as exc:
        pytest.skip(f"Cannot start {name} test container: {exc}")


@pytest.fixture(scope="module")
def external_postgres_container():
    container = PostgresContainer("postgres:16-alpine")
    started_container = _start_container_or_skip(container, "postgres")
    try:
        yield started_container
    finally:
        started_container.stop()


def _new_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _insert_json_payload(
    session,
    json_type: JsonType,
    payload: dict | list[dict],
    code_prefix: str,
) -> str:
    entity = JsonPayloadEntity(
        code=_new_name(code_prefix),
        description=f"{code_prefix} test payload",
        json_type=json_type.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _patch_execute_operations_for_class(monkeypatch, clazz, captured: dict):
    def _fake_execute_operations(cls, session, step_id, data):
        captured["step_id"] = step_id
        captured["data"] = data
        return [{"message": "ok"}]

    monkeypatch.setattr(clazz, "execute_operations", classmethod(_fake_execute_operations))


def test_sleep_step_executor_returns_slept_status(monkeypatch, alembic_container):
    import app.elaborations.services.steps.sleep_step_executor as sleep_module

    sleep_calls: list[int] = []
    monkeypatch.setattr(sleep_module.time, "sleep", lambda duration: sleep_calls.append(duration))

    scenario_step = SimpleNamespace(code="step-1", id="sc-step-0")
    cfg = SleepConfigurationStepDto(duration=2)

    with managed_session() as session:
        result = SleepStepExecutor().execute(session, scenario_step, cfg)

    assert sleep_calls == [2]
    assert result == [{"status": "slept", "duration": "2"}]


def test_data_step_executor_forwards_cfg_data(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataStepExecutor, captured)

    scenario_step = SimpleNamespace(id="sc-step-1", code="step-1")
    cfg = DataConfigurationStepDTO(data=[{"id": 1}, {"id": 2}])

    with managed_session() as session:
        result = DataStepExecutor().execute(session, scenario_step, cfg)

    assert captured["step_id"] == "sc-step-1"
    assert captured["data"] == [{"id": 1}, {"id": 2}]
    assert result == [{"message": "ok"}]


def test_data_from_json_array_step_executor_uses_list_payload(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromJsonArrayStepExecutor, captured)

    with managed_session() as session:
        json_array_id = _insert_json_payload(
            session,
            JsonType.JSON_ARRAY,
            [{"id": 1}, {"id": 2}],
            "json_arr",
        )
        scenario_step = SimpleNamespace(id="sc-step-2", code="step-2")
        cfg = DataFromJsonArrayConfigurationStepDto(json_array_id=json_array_id)

        result = DataFromJsonArrayStepExecutor().execute(session, scenario_step, cfg)

    assert captured["step_id"] == "sc-step-2"
    assert captured["data"] == [{"id": 1}, {"id": 2}]
    assert result == [{"message": "ok"}]


def test_data_from_json_array_step_executor_wraps_single_object(monkeypatch, alembic_container):
    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromJsonArrayStepExecutor, captured)

    with managed_session() as session:
        json_array_id = _insert_json_payload(
            session,
            JsonType.JSON_ARRAY,
            {"id": 10, "name": "single"},
            "json_obj",
        )
        scenario_step = SimpleNamespace(id="sc-step-3", code="step-3")
        cfg = DataFromJsonArrayConfigurationStepDto(json_array_id=json_array_id)

        result = DataFromJsonArrayStepExecutor().execute(session, scenario_step, cfg)

    assert captured["data"] == [{"id": 10, "name": "single"}]
    assert result == [{"message": "ok"}]


def test_data_from_queue_step_executor_reads_until_max_messages(monkeypatch, alembic_container):
    import app.elaborations.services.steps.data_from_queue_step_executor as queue_module

    captured: dict = {}
    _patch_execute_operations_for_class(monkeypatch, DataFromQueueStepExecutor, captured)

    queue = SimpleNamespace(code="queue-code", broker_id="broker-1")
    fake_connection_cfg = object()
    sleep_calls: list[int] = []
    receive_max_arguments: list[int] = []
    responses = [[], [{"id": 1}], [{"id": 2}], [{"id": 3}]]

    class FakeQueueConnectionService:
        def receive_messages(self, connection_config, queue_id, max_messages=10):
            receive_max_arguments.append(max_messages)
            if responses:
                return responses.pop(0)
            return []

    monkeypatch.setattr(
        queue_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: queue,
    )
    monkeypatch.setattr(queue_module, "load_broker_connection", lambda _broker_id: fake_connection_cfg)
    monkeypatch.setattr(
        queue_module.QueueConnectionServiceFactory,
        "get_service",
        classmethod(lambda _cls, _cfg: FakeQueueConnectionService()),
    )
    monkeypatch.setattr(queue_module.time, "sleep", lambda duration: sleep_calls.append(duration))

    scenario_step = SimpleNamespace(id="sc-step-4", code="step-4")
    cfg = DataFromQueueConfigurationStepDto(
        queue_id="queue-1",
        retry=4,
        wait_time_seconds=1,
        max_messages=3,
    )

    with managed_session() as session:
        result = DataFromQueueStepExecutor().execute(session, scenario_step, cfg)

    assert captured["step_id"] == "sc-step-4"
    assert captured["data"] == [{"id": 1}, {"id": 2}, {"id": 3}]
    assert sleep_calls == [1]
    assert receive_max_arguments == [3, 3, 2, 1]
    assert result == [{"message": "ok"}]


def test_data_from_queue_step_executor_raises_when_queue_not_found(alembic_container):
    import app.elaborations.services.steps.data_from_queue_step_executor as queue_module

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(queue_module.QueueService, "get_by_id", lambda _self, _session, _queue_id: None)
    try:
        scenario_step = SimpleNamespace(id="sc-step-5", code="step-5")
        cfg = DataFromQueueConfigurationStepDto(queue_id="missing-queue")
        with managed_session() as session:
            with pytest.raises(ValueError, match="Queue 'missing-queue' not found"):
                DataFromQueueStepExecutor().execute(session, scenario_step, cfg)
    finally:
        monkeypatch.undo()


def test_data_from_db_step_executor_reads_from_external_postgres(
    monkeypatch,
    alembic_container,
    external_postgres_container,
):
    import app.elaborations.services.steps.data_from_db_step_executor as db_module

    table_name = _new_name("step_db")
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"CREATE TABLE {table_name} (id INTEGER, name TEXT)"))
            conn.execute(
                text(f"INSERT INTO {table_name} (id, name) VALUES (1, 'row-1'), (2, 'row-2')")
            )
    finally:
        external_engine.dispose()

    captured: dict = {}

    def _fake_execute_operations(session, operation_ids, data):
        captured["operation_ids"] = operation_ids
        captured["data"] = data
        return [{"message": "db-forwarded"}]

    monkeypatch.setattr(
        db_module.DataFromDbStepExecutor,
        "execute_operations",
        classmethod(lambda _cls, session, step_id, data: _fake_execute_operations(session, [], data)),
    )

    connection_payload = {
        "database_type": "postgres",
        "host": external_postgres_container.get_container_host_ip(),
        "port": int(external_postgres_container.get_exposed_port(5432)),
        "database": external_postgres_container.dbname,
        "db_schema": "public",
        "user": external_postgres_container.username,
        "password": external_postgres_container.password,
    }

    with managed_session() as session:
        connection_id = _insert_json_payload(
            session,
            JsonType.DATABASE_CONNECTION,
            connection_payload,
            "db_conn",
        )
        datasource_id = _insert_json_payload(
            session,
            JsonType.DATABASE_TABLE,
            {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
            },
            "db_ds",
        )

    with managed_session() as session:
        scenario_step = SimpleNamespace(id="sc-step-6", code="step-6", configuration_json={})
        cfg = DataFromDbConfigurationStepDto(dataset_id=datasource_id)
        result = DataFromDbStepExecutor().execute(session, scenario_step, cfg)

    assert captured["operation_ids"] == []
    assert len(captured["data"]) == 2
    assert {row["id"] for row in captured["data"]} == {1, 2}
    assert result == [{"message": "db-forwarded"}]


def test_insert_and_update_step_api(alembic_container):
    create_dto = CreateStepDto(
        code=_new_name("step"),
        description="step create",
        cfg={
            "stepType": StepType.SLEEP.value,
            "duration": 1,
        },
    )
    created_step_id = asyncio.run(insert_step_api(create_dto))["id"]

    with managed_session() as session:
        created_step = StepService().get_by_id(session, created_step_id)
        assert created_step is not None
        assert created_step.code == create_dto.code
        assert created_step.description == create_dto.description

    update_dto = UpdateStepDto(
        id=created_step_id,
        code=f"{create_dto.code}_updated",
        description="step updated",
        cfg={
            "stepType": StepType.DATA.value,
            "data": [{"id": 1}],
        },
    )
    asyncio.run(update_step_api(update_dto))

    with managed_session() as session:
        updated_step = StepService().get_by_id(session, created_step_id)
        assert updated_step is not None
        assert updated_step.code == f"{create_dto.code}_updated"
        assert updated_step.description == "step updated"
        assert updated_step.step_type == StepType.DATA.value
        assert updated_step.configuration_json == {"stepType": "data", "data": [{"id": 1}]}


def test_delete_scenario_steps_api_deletes_only_scenario_steps(alembic_container):
    with managed_session() as session:
        scenario_id = ScenarioService().insert(
            session,
            ScenarioEntity(code=_new_name("sc"), description="scenario"),
        )
        step_id = StepService().insert(
            session,
            StepEntity(
                code=_new_name("step"),
                step_type=StepType.SLEEP.value,
                configuration_json={"stepType": "sleep", "duration": 0},
            ),
        )
        ScenarioStepService().insert(
            session,
            ScenarioStepEntity(
                scenario_id=scenario_id,
                code=_new_name("step"),
                step_type=StepType.SLEEP.value,
                configuration_json={"stepType": "sleep", "duration": 0},
                order=0,
            ),
        )

    asyncio.run(delete_scenario_step_api(scenario_id))

    with managed_session() as session:
        assert ScenarioService().get_by_id(session, scenario_id) is not None
        assert ScenarioStepService().get_all_by_scenario_id(session, scenario_id) == []

    response = asyncio.run(find_all_by_scenario_api(scenario_id))
    assert isinstance(response, list)
