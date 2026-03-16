import importlib
import sys

from fastapi.testclient import TestClient


def _load_main_app(monkeypatch):
    import alembic_runner
    import elasticmq.elasticmq_config as elasticmq_config
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

    sys.modules.pop("main", None)
    main_module = importlib.import_module("main")
    return main_module.app


def test_elaborations_openapi_exposes_only_supported_routes(monkeypatch):
    app = _load_main_app(monkeypatch)
    client = TestClient(app)

    response = client.get("/openapi.json")
    assert response.status_code == 200

    paths = set(response.json()["paths"].keys())

    supported_paths = {
        "/elaborations/test-suite",
        "/elaborations/test-suite/{_id}",
        "/elaborations/test-suite/{_id}/execute",
        "/elaborations/test-suite/{test_suite_id}/test/{suite_item_id}/execute",
        "/elaborations/test-suite-execution",
        "/elaborations/test-suite-execution/{execution_id}",
        "/elaborations/execution/{execution_id}/events",
    }
    removed_paths = {
        "/elaborations/suite",
        "/elaborations/suite/{_id}",
        "/elaborations/suite/{_id}/execute",
        "/elaborations/suite/{suite_id}/test/{suite_test_id}/execute",
        "/elaborations/test",
        "/elaborations/test/{_id}",
        "/elaborations/suite-execution",
        "/elaborations/suite-execution/{execution_id}",
        "/elaborations/suite/{suite_id}/test",
        "/elaborations/suite/test/{test_id}/operation",
        "/elaborations/operation",
        "/elaborations/operation/{_id}",
    }

    assert supported_paths.issubset(paths)
    assert removed_paths.isdisjoint(paths)


def test_removed_suite_endpoints_return_404(monkeypatch):
    app = _load_main_app(monkeypatch)
    client = TestClient(app)

    assert client.get("/elaborations/suite").status_code == 404
    assert client.get("/elaborations/test").status_code == 404
    assert client.get("/elaborations/suite-execution").status_code == 404
    assert client.get("/elaborations/operation").status_code == 404
    assert client.get("/elaborations/operation/legacy-id").status_code == 404
