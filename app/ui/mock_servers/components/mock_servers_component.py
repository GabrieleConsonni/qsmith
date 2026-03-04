import json

import streamlit as st

from mock_servers.services.data_loader_service import MOCK_SERVERS_KEY, load_mock_servers
from mock_servers.services.mock_server_api_service import (
    activate_mock_server,
    create_mock_server,
    deactivate_mock_server,
    delete_mock_server,
    update_mock_server,
)


DEFAULT_APIS_TEMPLATE = [
    {
        "order": 1,
        "code": "get-orders",
        "description": "Mock GET /orders",
        "cfg": {
            "method": "GET",
            "path": "/orders",
            "params": {},
            "headers": {},
            "body": None,
            "body_match": "contains",
            "response_status": 200,
            "response_headers": {"Content-Type": "application/json"},
            "response_body": {"status": "ok", "items": []},
            "priority": 0,
        },
        "operations": [],
    }
]

DEFAULT_QUEUES_TEMPLATE = [
    {
        "order": 1,
        "code": "orders-queue-trigger",
        "description": "Queue trigger",
        "queue_id": "replace-with-queue-id",
        "cfg": {
            "polling_interval_seconds": 1,
            "max_messages": 10,
        },
        "operations": [],
    }
]


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True)


def _api_for_editor(api_entry: dict) -> dict:
    if not isinstance(api_entry, dict):
        return {}
    operations = []
    for operation in api_entry.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        operations.append(
            {
                "order": int(operation.get("order") or 0),
                "code": str(operation.get("code") or ""),
                "description": str(operation.get("description") or ""),
                "cfg": (
                    operation.get("configuration_json")
                    if isinstance(operation.get("configuration_json"), dict)
                    else {}
                ),
            }
        )
    return {
        "order": int(api_entry.get("order") or 0),
        "code": str(api_entry.get("code") or ""),
        "description": str(api_entry.get("description") or ""),
        "cfg": (
            api_entry.get("configuration_json")
            if isinstance(api_entry.get("configuration_json"), dict)
            else {}
        ),
        "operations": operations,
    }


def _queue_for_editor(queue_entry: dict) -> dict:
    if not isinstance(queue_entry, dict):
        return {}
    operations = []
    for operation in queue_entry.get("operations") or []:
        if not isinstance(operation, dict):
            continue
        operations.append(
            {
                "order": int(operation.get("order") or 0),
                "code": str(operation.get("code") or ""),
                "description": str(operation.get("description") or ""),
                "cfg": (
                    operation.get("configuration_json")
                    if isinstance(operation.get("configuration_json"), dict)
                    else {}
                ),
            }
        )
    return {
        "order": int(queue_entry.get("order") or 0),
        "code": str(queue_entry.get("code") or ""),
        "description": str(queue_entry.get("description") or ""),
        "queue_id": str(queue_entry.get("queue_id") or ""),
        "cfg": (
            queue_entry.get("configuration_json")
            if isinstance(queue_entry.get("configuration_json"), dict)
            else {}
        ),
        "operations": operations,
    }


def _parse_list_json(raw_value: str, field_name: str) -> tuple[list[dict] | None, str | None]:
    value = str(raw_value or "").strip()
    if not value:
        return [], None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return None, f"{field_name}: JSON non valido ({str(exc)})."
    if not isinstance(parsed, list):
        return None, f"{field_name}: deve essere un array JSON."
    result = [item for item in parsed if isinstance(item, dict)]
    return result, None


def _server_payload_from_form(dialog_suffix: str, server_id: str | None) -> tuple[dict | None, str | None]:
    code = str(st.session_state.get(f"mock_server_code_{dialog_suffix}") or "").strip()
    description = str(st.session_state.get(f"mock_server_description_{dialog_suffix}") or "")
    endpoint = str(st.session_state.get(f"mock_server_endpoint_{dialog_suffix}") or "").strip()
    is_active = bool(st.session_state.get(f"mock_server_is_active_{dialog_suffix}", False))
    apis_raw = str(st.session_state.get(f"mock_server_apis_{dialog_suffix}") or "[]")
    queues_raw = str(st.session_state.get(f"mock_server_queues_{dialog_suffix}") or "[]")

    if not code:
        return None, "Il campo Code e' obbligatorio."
    if not endpoint:
        return None, "Il campo Endpoint e' obbligatorio."

    apis, apis_error = _parse_list_json(apis_raw, "APIs")
    if apis_error:
        return None, apis_error
    queues, queues_error = _parse_list_json(queues_raw, "Queues")
    if queues_error:
        return None, queues_error

    payload = {
        "code": code,
        "description": description,
        "cfg": {"endpoint": endpoint},
        "apis": apis or [],
        "queues": queues or [],
        "is_active": is_active,
    }
    if server_id:
        payload["id"] = server_id
    return payload, None


@st.dialog("Add mock server", width="large")
def add_mock_server_dialog():
    dialog_suffix = "create"
    st.text_input("Code", key=f"mock_server_code_{dialog_suffix}")
    st.text_input("Description", key=f"mock_server_description_{dialog_suffix}")
    st.text_input(
        "Endpoint",
        key=f"mock_server_endpoint_{dialog_suffix}",
        help="Runtime route: /mock/{endpoint}/...",
    )
    st.checkbox("Active", key=f"mock_server_is_active_{dialog_suffix}", value=False)

    if f"mock_server_apis_{dialog_suffix}" not in st.session_state:
        st.session_state[f"mock_server_apis_{dialog_suffix}"] = _pretty_json(
            DEFAULT_APIS_TEMPLATE
        )
    if f"mock_server_queues_{dialog_suffix}" not in st.session_state:
        st.session_state[f"mock_server_queues_{dialog_suffix}"] = _pretty_json(
            DEFAULT_QUEUES_TEMPLATE
        )

    st.text_area(
        "APIs JSON",
        key=f"mock_server_apis_{dialog_suffix}",
        height=240,
    )
    st.text_area(
        "Queues JSON",
        key=f"mock_server_queues_{dialog_suffix}",
        height=240,
    )
    if st.button(
        "Save",
        key="mock_server_create_save_btn",
        icon=":material/save:",
        use_container_width=True,
    ):
        payload, validation_error = _server_payload_from_form(dialog_suffix, None)
        if validation_error:
            st.error(validation_error)
            return
        try:
            create_mock_server(payload or {})
        except Exception as exc:
            st.error(f"Errore creazione mock server: {str(exc)}")
            return
        load_mock_servers(force=True)
        st.rerun()


@st.dialog("Edit mock server", width="large")
def edit_mock_server_dialog(server_item: dict):
    server_id = str(server_item.get("id") or "")
    dialog_suffix = f"edit_{server_id}"
    st.text_input(
        "Code",
        key=f"mock_server_code_{dialog_suffix}",
        value=str(server_item.get("code") or ""),
    )
    st.text_input(
        "Description",
        key=f"mock_server_description_{dialog_suffix}",
        value=str(server_item.get("description") or ""),
    )
    st.text_input(
        "Endpoint",
        key=f"mock_server_endpoint_{dialog_suffix}",
        value=str(server_item.get("endpoint") or ""),
        help="Runtime route: /mock/{endpoint}/...",
    )
    st.checkbox(
        "Active",
        key=f"mock_server_is_active_{dialog_suffix}",
        value=bool(server_item.get("is_active")),
    )

    if f"mock_server_apis_{dialog_suffix}" not in st.session_state:
        apis_for_editor = [_api_for_editor(item) for item in (server_item.get("apis") or [])]
        st.session_state[f"mock_server_apis_{dialog_suffix}"] = _pretty_json(apis_for_editor)
    if f"mock_server_queues_{dialog_suffix}" not in st.session_state:
        queues_for_editor = [
            _queue_for_editor(item) for item in (server_item.get("queues") or [])
        ]
        st.session_state[f"mock_server_queues_{dialog_suffix}"] = _pretty_json(
            queues_for_editor
        )

    st.text_area(
        "APIs JSON",
        key=f"mock_server_apis_{dialog_suffix}",
        height=240,
    )
    st.text_area(
        "Queues JSON",
        key=f"mock_server_queues_{dialog_suffix}",
        height=240,
    )
    if st.button(
        "Save",
        key=f"mock_server_edit_save_btn_{server_id}",
        icon=":material/save:",
        use_container_width=True,
    ):
        payload, validation_error = _server_payload_from_form(dialog_suffix, server_id)
        if validation_error:
            st.error(validation_error)
            return
        try:
            update_mock_server(payload or {})
        except Exception as exc:
            st.error(f"Errore aggiornamento mock server: {str(exc)}")
            return
        load_mock_servers(force=True)
        st.rerun()


def render_mock_servers_component():
    load_mock_servers(force=False)
    servers = st.session_state.get(MOCK_SERVERS_KEY, [])
    if not isinstance(servers, list):
        servers = []

    header_cols = st.columns([9, 1], gap="small", vertical_alignment="center")
    with header_cols[1]:
        if st.button(
            "",
            key="mock_server_add_btn",
            icon=":material/add:",
            help="Add mock server",
            use_container_width=True,
        ):
            add_mock_server_dialog()

    if not servers:
        st.info("Nessun mock server configurato.")
        return

    for idx, server_item in enumerate(servers):
        server_id = str(server_item.get("id") or "")
        endpoint = str(server_item.get("endpoint") or "-")
        label = str(server_item.get("description") or server_item.get("code") or "-")
        is_active = bool(server_item.get("is_active"))
        apis_count = len(server_item.get("apis") or [])
        queues_count = len(server_item.get("queues") or [])
        with st.container(border=True):
            row = st.columns([5, 1, 1, 1, 1], gap="small", vertical_alignment="center")
            with row[0]:
                st.write(label)
                st.caption(
                    f"/mock/{endpoint} - apis: {apis_count}, queues: {queues_count} - "
                    f"{'active' if is_active else 'inactive'}"
                )
            with row[1]:
                if st.button(
                    "",
                    key=f"mock_server_toggle_{server_id or idx}",
                    icon=":material/pause_circle:"
                    if is_active
                    else ":material/play_circle:",
                    use_container_width=True,
                    help="Deactivate" if is_active else "Activate",
                ):
                    try:
                        if is_active:
                            deactivate_mock_server(server_id)
                        else:
                            activate_mock_server(server_id)
                    except Exception as exc:
                        st.error(f"Errore aggiornamento stato mock server: {str(exc)}")
                    else:
                        load_mock_servers(force=True)
                        st.rerun()
            with row[2]:
                if st.button(
                    "",
                    key=f"mock_server_edit_{server_id or idx}",
                    icon=":material/settings:",
                    use_container_width=True,
                    help="Edit",
                ):
                    edit_mock_server_dialog(server_item)
            with row[3]:
                if st.button(
                    "",
                    key=f"mock_server_delete_{server_id or idx}",
                    icon=":material/delete:",
                    use_container_width=True,
                    help="Delete",
                    disabled=not bool(server_id),
                ):
                    try:
                        delete_mock_server(server_id)
                    except Exception as exc:
                        st.error(f"Errore cancellazione mock server: {str(exc)}")
                    else:
                        load_mock_servers(force=True)
                        st.rerun()
            with row[4]:
                if st.button(
                    "",
                    key=f"mock_server_refresh_{server_id or idx}",
                    icon=":material/refresh:",
                    use_container_width=True,
                    help="Refresh",
                ):
                    load_mock_servers(force=True)
                    st.rerun()
