import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from docker.errors import DockerException
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.mssql import SqlServerContainer
from testcontainers.oracle import OracleDbContainer
from testcontainers.postgres import PostgresContainer

from app._alembic.models.json_payload_entity import JsonPayloadEntity
from app._alembic.services.alembic_config_service import url_from_env
from app._alembic.services.session_context_manager import managed_session
from app.elaborations.api.operations_api import insert_operation_api
from app.elaborations.models.dtos.configuration_operation_dto import (
    AssertConfigurationOperationDto,
    PublishConfigurationOperationDto,
    RunScenarioConfigurationOperationDto,
    SaveInternalDBConfigurationOperationDto,
    SaveToExternalDBConfigurationOperationDto,
)
from app.elaborations.models.dtos.create_operation_dto import CreateOperationDto
from app.elaborations.services.alembic.operation_service import OperationService
from app.elaborations.services.operations.operation_executor_composite import (
    execute_operations,
)
from app.elaborations.services.operations.assert_operation_executor import (
    AssertOperationExecutor,
)
from app.elaborations.services.operations.publish_to_queue_operation_executor import (
    PublishToQueueOperationExecutor,
)
from app.elaborations.services.operations.save_to_external_db_operation_executor import (
    SaveToExternalDbOperationExecutor,
)
from app.elaborations.services.operations.save_to_internal_db_operation_executor import (
    SaveInternalDbOperationExecutor,
)
from app.elaborations.services.operations.run_scenario_operation_executor import (
    RunScenarioOperationExecutor,
)
from app.data_sources.models.database_connection_config_types import (
    convert_database_connection_config,
)
from app.json_utils.models.enums.json_type import JsonType
from app.json_utils.services.alembic.json_files_service import JsonFilesService
from app.sqlalchemy_utils.engine_factory.sqlalchemy_engine_factory_composite import (
    create_sqlalchemy_engine,
)


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


@pytest.fixture(scope="module")
def external_sqlserver_container():
    container = SqlServerContainer("mcr.microsoft.com/mssql/server:2022-latest")
    started_container = _start_container_or_skip(container, "sqlserver")
    try:
        yield started_container
    finally:
        started_container.stop()


@pytest.fixture(scope="module")
def external_oracle_container():
    container = OracleDbContainer(
        image="gvenzl/oracle-free:slim",
        oracle_password="1Secure*Password1",
    )
    started_container = _start_container_or_skip(container, "oracle")
    try:
        yield started_container
    finally:
        started_container.stop()


def _new_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _insert_database_connection_payload(session, payload: dict) -> str:
    entity = JsonPayloadEntity(
        code=_new_name("conn"),
        description="test database connection",
        json_type=JsonType.DATABASE_CONNECTION.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _insert_database_datasource_payload(session, payload: dict) -> str:
    entity = JsonPayloadEntity(
        code=_new_name("ds"),
        description="test database datasource",
        json_type=JsonType.DATABASE_TABLE.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _insert_json_array_payload(session, payload: list[dict] | dict) -> str:
    entity = JsonPayloadEntity(
        code=_new_name("json_arr"),
        description="test json array",
        json_type=JsonType.JSON_ARRAY.value,
        payload=payload,
    )
    return JsonFilesService().insert(session, entity)


def _count_rows(url: str, table_name: str, query: str | None = None) -> int:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            count_query = query or f"SELECT COUNT(*) FROM {table_name}"
            return int(connection.execute(text(count_query)).scalar_one())
    finally:
        engine.dispose()


def _count_rows_from_connection_payload(payload: dict, table_name: str) -> int:
    connection_cfg = convert_database_connection_config(payload)
    engine = create_sqlalchemy_engine(connection_cfg)
    try:
        with engine.connect() as connection:
            return int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    finally:
        engine.dispose()


def test_publish_operation_executor_sends_flat_messages(monkeypatch, alembic_container):
    import app.elaborations.services.operations.publish_to_queue_operation_executor as publish_module

    published_calls: list[dict] = []

    class FakeQueueConnectionService:
        def publish_messages(self, connection_config, queue_id, messages):
            published_calls.append(
                {
                    "connection_config": connection_config,
                    "queue_id": queue_id,
                    "messages": messages,
                }
            )
            return [{"status": "ok"}]

    fake_connection_cfg = object()
    fake_queue = SimpleNamespace(code="orders", broker_id="broker-1")

    monkeypatch.setattr(
        publish_module.QueueService,
        "get_by_id",
        lambda _self, _session, _queue_id: fake_queue,
    )
    monkeypatch.setattr(
        publish_module,
        "load_broker_connection",
        lambda _broker_id: fake_connection_cfg,
    )
    monkeypatch.setattr(
        publish_module.QueueConnectionServiceFactory,
        "get_service",
        lambda _self, _cfg: FakeQueueConnectionService(),
    )

    data = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
    cfg = PublishConfigurationOperationDto(queue_id="queue-1")

    with managed_session() as session:
        result = PublishToQueueOperationExecutor().execute(
            session,
            "op-publish",
            cfg,
            data,
        )

    assert len(published_calls) == 1
    assert published_calls[0]["queue_id"] == "queue-1"
    assert published_calls[0]["messages"] == data
    assert result.result == [{"message": "Published 2 message(s) to queue 'orders'"}]


def test_save_internal_db_operation_executor_inserts_rows(alembic_container):
    table_name = _new_name("internal_op")
    data = [
        {"id": 1, "name": "first"},
        {"id": 2, "name": "second"},
    ]
    cfg = SaveInternalDBConfigurationOperationDto(table_name=table_name)

    with managed_session() as session:
        result = SaveInternalDbOperationExecutor().execute(
            session,
            "op-internal",
            cfg,
            data,
        )

    inserted_rows = _count_rows(url_from_env(), table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_save_external_db_operation_executor_postgres(alembic_container, external_postgres_container):
    table_name = _new_name("ext_pg")
    data = [
        {"id": 10, "name": "pg-row-1"},
        {"id": 11, "name": "pg-row-2"},
    ]

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
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = SaveToExternalDBConfigurationOperationDto(
            connection_id=connection_id,
            table_name=table_name,
        )
        result = SaveToExternalDbOperationExecutor().execute(
            session,
            "op-external-postgres",
            cfg,
            data,
        )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, f"public.{table_name}")

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_save_external_db_operation_executor_sqlserver(alembic_container, external_sqlserver_container):
    table_name = _new_name("ext_sqls")
    data = [
        {"id": 20, "name": "sql-row-1"},
        {"id": 21, "name": "sql-row-2"},
    ]

    connection_payload = {
        "database_type": "sqlserver",
        "host": external_sqlserver_container.get_container_host_ip(),
        "port": int(external_sqlserver_container.get_exposed_port(1433)),
        "database": external_sqlserver_container.dbname,
        "db_schema": "dbo",
        "user": external_sqlserver_container.username,
        "password": external_sqlserver_container.password,
    }

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = SaveToExternalDBConfigurationOperationDto(
            connection_id=connection_id,
            table_name=table_name,
        )
        result = SaveToExternalDbOperationExecutor().execute(
            session,
            "op-external-sqlserver",
            cfg,
            data,
        )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_run_scenario_operation_executor_starts_execution(monkeypatch, alembic_container):
    import elaborations.services.scenarios.scenario_executor_service as scenario_service_module

    captured: dict[str, str] = {}

    def _fake_execute_scenario_by_id(scenario_id: str):
        captured["scenario_id"] = scenario_id
        return "exec-run-scenario-1"

    monkeypatch.setattr(
        scenario_service_module,
        "execute_scenario_by_id",
        _fake_execute_scenario_by_id,
    )

    cfg = RunScenarioConfigurationOperationDto(scenario_id="scenario-123")

    with managed_session() as session:
        result = RunScenarioOperationExecutor().execute(
            session,
            "op-run-scenario",
            cfg,
            [{"id": 1}],
        )

    assert captured["scenario_id"] == "scenario-123"
    assert result.result[0]["scenario_id"] == "scenario-123"
    assert result.result[0]["execution_id"] == "exec-run-scenario-1"


def test_save_external_db_operation_executor_oracle(alembic_container, external_oracle_container):
    table_name = _new_name("ext_orcl")
    data = [
        {"id": 30, "name": "ora-row-1"},
        {"id": 31, "name": "ora-row-2"},
    ]
    service_name = external_oracle_container.dbname or "FREEPDB1"

    connection_payload = {
        "database_type": "oracle",
        "host": external_oracle_container.get_container_host_ip(),
        "port": int(external_oracle_container.get_exposed_port(1521)),
        "database": service_name,
        "db_schema": "SYSTEM",
        "user": "system",
        "password": external_oracle_container.oracle_password,
    }

    with managed_session() as session:
        connection_id = _insert_database_connection_payload(session, connection_payload)
        cfg = SaveToExternalDBConfigurationOperationDto(
            connection_id=connection_id,
            table_name=table_name,
        )
        result = SaveToExternalDbOperationExecutor().execute(
            session,
            "op-external-oracle",
            cfg,
            data,
        )

    inserted_rows = _count_rows_from_connection_payload(connection_payload, table_name)

    assert inserted_rows == 2
    assert result.result == [{"message": f"Created 2 rows in {table_name} table"}]


def test_assert_not_empty_operation_executor_passes(alembic_container):
    cfg = AssertConfigurationOperationDto(
        evaluated_object_type="json-data",
        assert_type="not-empty",
    )
    data = [{"id": 1, "name": "first"}]

    with managed_session() as session:
        result = AssertOperationExecutor().execute(
            session,
            "op-assert-not-empty",
            cfg,
            data,
        )

    assert result.data == data
    assert result.result == [{"message": "Assert 'not-empty' passed for 'json-data' data."}]


def test_assert_empty_operation_executor_fails_with_custom_message(alembic_container):
    cfg = AssertConfigurationOperationDto(
        evaluated_object_type="json-data",
        assert_type="empty",
        error_message="Expected no rows.",
    )

    with managed_session() as session:
        with pytest.raises(ValueError, match="Expected no rows."):
            AssertOperationExecutor().execute(
                session,
                "op-assert-empty",
                cfg,
                [{"id": 1}],
            )


def test_assert_schema_validation_operation_executor_validates_rows(alembic_container):
    cfg = AssertConfigurationOperationDto(
        evaluated_object_type="json-data",
        assert_type="schema-validation",
        json_schema={
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
            "additionalProperties": True,
        },
    )

    with managed_session() as session:
        ok_result = AssertOperationExecutor().execute(
            session,
            "op-assert-schema-ok",
            cfg,
            [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
        )
        assert ok_result.result == [
            {"message": "Assert 'schema-validation' passed for 'json-data' data."}
        ]

        with pytest.raises(ValueError, match="does not match json schema"):
            AssertOperationExecutor().execute(
                session,
                "op-assert-schema-ko",
                cfg,
                [{"id": "wrong", "name": "a"}],
            )


def test_assert_contains_operation_executor_uses_expected_json_array(alembic_container):
    with managed_session() as session:
        expected_json_array_id = _insert_json_array_payload(
            session,
            [
                {"id": 1, "code": "A"},
                {"id": 2, "code": "B"},
            ],
        )
        cfg = AssertConfigurationOperationDto(
            evaluated_object_type="json-data",
            assert_type="contains",
            expected_json_array_id=expected_json_array_id,
            compare_keys=["id", "code"],
        )

        ok_result = AssertOperationExecutor().execute(
            session,
            "op-assert-contains-ok",
            cfg,
            [{"id": 2, "code": "B"}],
        )
        assert ok_result.result == [
            {"message": "Assert 'contains' passed for 'json-data' data."}
        ]

        with pytest.raises(ValueError, match="not contained in expected json-array"):
            AssertOperationExecutor().execute(
                session,
                "op-assert-contains-ko",
                cfg,
                [{"id": 3, "code": "C"}],
            )


def test_assert_json_array_equals_operation_executor_is_order_insensitive(alembic_container):
    with managed_session() as session:
        expected_json_array_id = _insert_json_array_payload(
            session,
            [
                {"id": 1, "code": "A"},
                {"id": 2, "code": "B"},
            ],
        )
        cfg = AssertConfigurationOperationDto(
            evaluated_object_type="json-data",
            assert_type="json-array-equals",
            expected_json_array_id=expected_json_array_id,
            compare_keys=["id", "code"],
        )

        ok_result = AssertOperationExecutor().execute(
            session,
            "op-assert-equals-ok",
            cfg,
            [{"id": 2, "code": "B"}, {"id": 1, "code": "A"}],
        )
        assert ok_result.result == [
            {"message": "Assert 'json-array-equals' passed for 'json-data' data."}
        ]

        with pytest.raises(ValueError, match="not equal to expected json-array"):
            AssertOperationExecutor().execute(
                session,
                "op-assert-equals-ko",
                cfg,
                [{"id": 1, "code": "A"}],
            )


def test_execute_operations_raises_when_operation_not_found(alembic_container):
    with managed_session() as session:
        with pytest.raises(ValueError, match="Operation with id 'missing-op' not found"):
            execute_operations(session, ["missing-op"], [{"id": 1}])


def test_insert_operation_api_persists_scalar_fields(alembic_container):
    dto = CreateOperationDto(
        code=_new_name("op"),
        description="api operation",
        cfg={
            "operationType": "save-internal-db",
            "table_name": _new_name("api_tbl"),
        },
    )

    created_operation_id = asyncio.run(insert_operation_api(dto))["id"]

    with managed_session() as session:
        entity = OperationService().get_by_id(session, created_operation_id)
        assert entity is not None
        assert entity.code == dto.code
        assert entity.description == dto.description
        assert entity.operation_type == dto.cfg.operationType


def test_insert_operation_api_persists_assert_configuration(alembic_container):
    dto = CreateOperationDto(
        code=_new_name("op_assert"),
        description="api assert operation",
        cfg={
            "operationType": "assert",
            "evaluated_object_type": "json-data",
            "assert_type": "contains",
            "expected_json_array_id": "json-arr-id",
            "compare_keys": ["id", "code"],
            "error_message": "Assertion failed.",
        },
    )

    created_operation_id = asyncio.run(insert_operation_api(dto))["id"]

    with managed_session() as session:
        entity = OperationService().get_by_id(session, created_operation_id)
        assert entity is not None
        assert entity.operation_type == "assert"
        assert entity.configuration_json["assert_type"] == "contains"
        assert entity.configuration_json["evaluated_object_type"] == "json-data"
        assert entity.configuration_json["compare_keys"] == ["id", "code"]
