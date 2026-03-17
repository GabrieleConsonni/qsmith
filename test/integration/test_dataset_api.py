import importlib
import os
import sys

import pytest
from docker.errors import DockerException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from testcontainers.core.exceptions import ContainerStartException
from testcontainers.postgres import PostgresContainer

from app.alembic_runner import run_alembic_migrations


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
def alembic_container():
    container = PostgresContainer("postgres:16-alpine").with_exposed_ports(5432)
    started_container = _start_container_or_skip(container, "postgres")
    previous_database_url = None
    try:
        previous_database_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = started_container.get_connection_url()
        run_alembic_migrations()
        yield started_container
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        started_container.stop()


def _load_main_app(monkeypatch):
    import alembic_runner
    import elasticmq.elasticmq_config as elasticmq_config
    import elaborations.services.test_suite_schedules.scheduler_runtime as scheduler_runtime
    from mock_servers.services.runtime.mock_server_runtime_registry import (
        MockServerRuntimeRegistry,
    )

    monkeypatch.setattr(alembic_runner, "run_alembic_migrations", lambda: None)
    monkeypatch.setattr(elasticmq_config, "init_elasticmq", lambda: None)
    monkeypatch.setattr(
        MockServerRuntimeRegistry,
        "bootstrap_active_servers",
        lambda: None,
    )
    monkeypatch.setattr(scheduler_runtime, "bootstrap_scheduler_runtime", lambda: None)
    monkeypatch.setattr(scheduler_runtime, "shutdown_scheduler_runtime", lambda: None)

    sys.modules.pop("main", None)
    return importlib.import_module("main").app


def test_dataset_api_roundtrip_and_preview(monkeypatch, alembic_container, external_postgres_container):
    table_name = "dataset_api_orders"
    external_engine = create_engine(external_postgres_container.get_connection_url())
    try:
        with external_engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            conn.execute(
                text(
                    f"""
                    CREATE TABLE {table_name} (
                        id INTEGER,
                        status TEXT,
                        created_at TIMESTAMP
                    )
                    """
                )
            )
            conn.execute(
                text(
                    f"""
                    INSERT INTO {table_name} (id, status, created_at)
                    VALUES
                        (1, 'READY', NOW() - INTERVAL '2 day'),
                        (2, 'READY', NOW() - INTERVAL '1 day'),
                        (3, 'PENDING', NOW())
                    """
                )
            )
    finally:
        external_engine.dispose()

    app = _load_main_app(monkeypatch)
    client = TestClient(app)
    connection_payload = {
        "description": "api dataset connection",
        "payload": {
            "database_type": "postgres",
            "host": external_postgres_container.get_container_host_ip(),
            "port": int(external_postgres_container.get_exposed_port(5432)),
            "database": external_postgres_container.dbname,
            "db_schema": "public",
            "user": external_postgres_container.username,
            "password": external_postgres_container.password,
        },
    }
    connection_response = client.post("/database/connection", json=connection_payload)
    assert connection_response.status_code == 200
    connection_id = connection_response.json()["id"]

    dataset_response = client.post(
        "/data-source/database",
        json={
            "description": "orders-ready",
            "payload": {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            "perimeter": {
                "selected_columns": ["id", "status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "eq", "value": "READY"},
                    ],
                },
                "sort": [{"field": "id", "direction": "desc"}],
            },
        },
    )
    assert dataset_response.status_code == 200
    dataset_id = dataset_response.json()["id"]

    get_response = client.get(f"/data-source/database/{dataset_id}")
    assert get_response.status_code == 200
    assert get_response.json()["perimeter"]["selected_columns"] == ["id", "status"]

    preview_response = client.get(f"/data-source/database/{dataset_id}/preview")
    assert preview_response.status_code == 200
    preview_payload = preview_response.json()
    assert preview_payload["columns"] == ["id", "status"]
    assert preview_payload["rows"] == [
        {"id": 2, "status": "READY"},
        {"id": 1, "status": "READY"},
    ]

    update_response = client.put(
        "/data-source/database",
        json={
            "id": dataset_id,
            "description": "orders-pending",
            "payload": {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": table_name,
                "object_type": "table",
            },
            "perimeter": {
                "selected_columns": ["status"],
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "id", "operator": "gt", "value": 1},
                    ],
                },
                "sort": [{"field": "id", "direction": "asc"}],
            },
        },
    )
    assert update_response.status_code == 200

    preview_response = client.get(f"/data-source/database/{dataset_id}/preview")
    assert preview_response.status_code == 200
    assert preview_response.json()["rows"] == [
        {"status": "READY"},
        {"status": "PENDING"},
    ]


def test_dataset_api_rejects_invalid_perimeter(monkeypatch, alembic_container, external_postgres_container):
    app = _load_main_app(monkeypatch)
    client = TestClient(app)
    connection_response = client.post(
        "/database/connection",
        json={
            "description": "api invalid perimeter connection",
            "payload": {
                "database_type": "postgres",
                "host": external_postgres_container.get_container_host_ip(),
                "port": int(external_postgres_container.get_exposed_port(5432)),
                "database": external_postgres_container.dbname,
                "db_schema": "public",
                "user": external_postgres_container.username,
                "password": external_postgres_container.password,
            },
        },
    )
    assert connection_response.status_code == 200
    connection_id = connection_response.json()["id"]

    response = client.post(
        "/data-source/database",
        json={
            "description": "invalid perimeter",
            "payload": {
                "connection_id": connection_id,
                "schema": "public",
                "object_name": "missing_table",
                "object_type": "table",
            },
            "perimeter": {
                "filter": {
                    "logic": "AND",
                    "conditions": [
                        {"field": "status", "operator": "boom", "value": "READY"},
                    ],
                },
            },
        },
    )

    assert response.status_code == 500
    assert "not supported" in response.json()["detail"]
