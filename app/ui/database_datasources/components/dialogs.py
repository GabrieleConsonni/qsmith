import json

import pandas as pd
import streamlit as st

from api_client import api_delete, api_post, api_put
from database_datasources.services.data_loader_service import (
    invalidate_database_datasource_preview,
    load_database_connection_objects,
    load_database_connections,
    load_database_datasources,
    load_database_object_preview,
)

SELECTED_DATABASE_DATASOURCE_ID_KEY = "selected_database_datasource_id"
PERIMETER_OPERATORS = [
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "contains",
    "starts_with",
    "ends_with",
    "in",
    "not_in",
    "is_null",
    "is_not_null",
]


def _connection_label(connection_item: dict) -> str:
    description = str(connection_item.get("description") or connection_item.get("id") or "-")
    payload = connection_item.get("payload") or {}
    connection_type = str(payload.get("database_type") or "-")
    return f"{description} [{connection_type}]"


def _render_database_object_type_selector(
    key_prefix: str,
    current_object_type: str = "table",
) -> str:
    options = ["table", "view"]
    normalized = str(current_object_type or "table").strip().lower()
    index = options.index(normalized) if normalized in options else 0
    return st.selectbox(
        "Database object type",
        options=options,
        index=index,
        key=f"{key_prefix}_object_type_select",
    )


def _render_database_object_selector(
    objects_payload: dict,
    key_prefix: str,
    object_type: str,
    current_object_name: str = "",
) -> str:
    available_objects = (
        [str(item) for item in (objects_payload.get("tables") or []) if item]
        if str(object_type or "table").strip().lower() == "table"
        else [str(item) for item in (objects_payload.get("views") or []) if item]
    )
    options = [""] + available_objects
    index = options.index(current_object_name) if current_object_name in available_objects else 0
    return st.selectbox(
        "Database objects",
        options=options,
        index=index,
        key=f"{key_prefix}_object_name_select",
    )


def _render_connection_selector(
    key_prefix: str,
    connections: list[dict],
    current_connection_id: str = "",
) -> str:
    connection_ids = [str(item.get("id")) for item in connections if item.get("id")]
    if not connection_ids:
        st.info("Nessuna connessione database disponibile.")
        return ""

    index = 0
    if current_connection_id and current_connection_id in connection_ids:
        index = connection_ids.index(current_connection_id)

    return st.selectbox(
        "Connection",
        options=connection_ids,
        index=index,
        key=f"{key_prefix}_connection_select",
        format_func=lambda conn_id: _connection_label(
            next(
                (item for item in connections if str(item.get("id")) == str(conn_id)),
                {},
            )
        ),
    )


def _coerce_editor_rows(value: object) -> list[dict]:
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _normalize_editor_value(value: object):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return value


def _normalize_filter_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    for row in _coerce_editor_rows(rows):
        field = str(row.get("field") or "").strip()
        operator = str(row.get("operator") or "").strip()
        value = _normalize_editor_value(row.get("value"))
        if not field and not operator and value is None:
            continue
        if not field or not operator:
            continue
        item = {
            "field": field,
            "operator": operator,
        }
        if operator not in {"is_null", "is_not_null"}:
            item["value"] = value
        normalized_rows.append(item)
    return normalized_rows


def _normalize_sort_rows(rows: object) -> list[dict]:
    normalized_rows: list[dict] = []
    for row in _coerce_editor_rows(rows):
        field = str(row.get("field") or "").strip()
        direction = str(row.get("direction") or "").strip().lower()
        if not field and not direction:
            continue
        if not field:
            continue
        normalized_rows.append(
            {
                "field": field,
                "direction": direction or "asc",
            }
        )
    return normalized_rows


def _load_object_columns(
    connection_id: str,
    object_name: str,
    object_type: str,
    schema: str | None,
) -> list[str]:
    object_preview = load_database_object_preview(
        connection_id,
        object_name,
        object_type=object_type or "table",
        schema=schema,
        limit=1,
        force=False,
    )
    columns = object_preview.get("columns") if isinstance(object_preview, dict) else []
    return [str(column) for column in columns if column]


def _build_perimeter_payload(
    selected_columns: list[str],
    filter_logic: str,
    filter_rows: object,
    sort_rows: object,
) -> dict | None:
    perimeter: dict = {}
    normalized_columns = [str(column).strip() for column in selected_columns if str(column).strip()]
    normalized_filters = _normalize_filter_rows(filter_rows)
    normalized_sort = _normalize_sort_rows(sort_rows)

    if normalized_columns:
        perimeter["selected_columns"] = normalized_columns
    if normalized_filters:
        perimeter["filter"] = {
            "logic": str(filter_logic or "AND").strip().upper(),
            "conditions": normalized_filters,
        }
    if normalized_sort:
        perimeter["sort"] = normalized_sort

    return perimeter or None


def _render_perimeter_editor(
    key_prefix: str,
    connection_id: str,
    object_name: str,
    object_type: str,
    schema: str | None,
    perimeter: dict | None = None,
) -> dict | None:
    st.divider()
    st.markdown("### Perimeter")

    available_columns = _load_object_columns(connection_id, object_name, object_type, schema)
    object_scope_key = f"{key_prefix}_{connection_id}_{schema or 'noschema'}_{object_type}_{object_name}"

    if not available_columns:
        st.info("Seleziona una tabella o view valida per configurare il perimetro.")
        return None

    perimeter_payload = perimeter if isinstance(perimeter, dict) else {}
    default_selected_columns = [
        str(column)
        for column in (perimeter_payload.get("selected_columns") or [])
        if str(column) in available_columns
    ]
    selected_columns_key = f"{object_scope_key}_selected_columns"
    if selected_columns_key not in st.session_state:
        st.session_state[selected_columns_key] = default_selected_columns

    col_actions = st.columns(2, gap="small")
    with col_actions[0]:
        if st.button(
            "Select all columns",
            key=f"{object_scope_key}_select_all_columns_btn",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[selected_columns_key] = list(available_columns)
    with col_actions[1]:
        if st.button(
            "Reset columns",
            key=f"{object_scope_key}_reset_columns_btn",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[selected_columns_key] = []

    selected_columns = st.multiselect(
        "Selected columns",
        options=available_columns,
        key=selected_columns_key,
        help="Lascia vuoto per leggere tutte le colonne.",
    )

    filter_logic_key = f"{object_scope_key}_filter_logic"
    default_filter_logic = str(
        (perimeter_payload.get("filter") or {}).get("logic") or "AND"
    ).strip().upper()
    if filter_logic_key not in st.session_state:
        st.session_state[filter_logic_key] = default_filter_logic

    st.markdown("**Filters**")
    filter_editor_key = f"{object_scope_key}_filter_editor"
    default_filter_rows = (perimeter_payload.get("filter") or {}).get("conditions") or [{"field": "", "operator": "eq", "value": ""}]
    filter_editor = st.data_editor(
        pd.DataFrame(default_filter_rows),
        key=filter_editor_key,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "field": st.column_config.SelectboxColumn(
                "Field",
                options=available_columns,
                required=False,
            ),
            "operator": st.column_config.SelectboxColumn(
                "Operator",
                options=PERIMETER_OPERATORS,
                required=False,
            ),
            "value": st.column_config.TextColumn("Value"),
        },
    )
    filter_logic = st.selectbox(
        "Filter logic",
        options=["AND", "OR"],
        index=0 if st.session_state.get(filter_logic_key, "AND") == "AND" else 1,
        key=filter_logic_key,
    )

    st.markdown("**Sort**")
    sort_editor_key = f"{object_scope_key}_sort_editor"
    default_sort_rows = perimeter_payload.get("sort") or [{"field": "", "direction": "asc"}]
    sort_editor = st.data_editor(
        pd.DataFrame(default_sort_rows),
        key=sort_editor_key,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "field": st.column_config.SelectboxColumn(
                "Field",
                options=available_columns,
                required=False,
            ),
            "direction": st.column_config.SelectboxColumn(
                "Direction",
                options=["asc", "desc"],
                required=False,
            ),
        },
    )

    return _build_perimeter_payload(selected_columns, filter_logic, filter_editor, sort_editor)


def _build_dataset_payload(
    connection_id: str,
    schema: str | None,
    object_name: str,
    object_type: str,
) -> dict:
    return {
        "connection_id": connection_id,
        "schema": schema,
        "object_name": object_name,
        "object_type": object_type,
    }


@st.dialog("Aggiungi dataset", width="large")
def add_database_datasource_dialog():
    load_database_connections(force=False)
    connections = st.session_state.get("database_connections", [])
    if not connections:
        st.info("Configura prima almeno una connessione database.")
        return

    description = st.text_input("Description", key="add_database_datasource_description")
    selected_connection_id = _render_connection_selector(
        "add_database_datasource",
        connections,
    )
    if not selected_connection_id:
        return

    objects_payload = load_database_connection_objects(selected_connection_id, force=False)

    selected_object_type = _render_database_object_type_selector(
        f"add_database_datasource_{selected_connection_id}",
        "table",
    )
    selected_object_name = _render_database_object_selector(
        objects_payload,
        key_prefix=f"add_database_datasource_{selected_connection_id}_{selected_object_type}",
        object_type=selected_object_type,
    )

    if not st.button(
        "Save",
        key="add_database_datasource_save",
        icon=":material/add:",
        use_container_width=True,
        disabled=not bool(str(selected_object_name or "").strip()),
    ):
        return

    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona un database object valido.")
        return

    payload = _build_dataset_payload(
        selected_connection_id,
        objects_payload.get("schema"),
        selected_object_name,
        selected_object_type,
    )

    try:
        response = api_post(
            "/data-source/database",
            {
                "description": description,
                "payload": payload,
            },
        )
    except Exception as exc:
        st.error(f"Errore salvataggio dataset: {str(exc)}")
        return

    load_database_datasources(force=True)
    invalidate_database_datasource_preview()
    new_id = response.get("id") if isinstance(response, dict) else None
    if new_id:
        st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = str(new_id)
    st.rerun()


@st.dialog("Modifica dataset", width="large")
def edit_database_datasource_dialog(datasource_item: dict):
    datasource_id = str(datasource_item.get("id") or "")
    payload = datasource_item.get("payload") or {}
    current_connection_id = str(payload.get("connection_id") or "")
    current_object_name = str(payload.get("object_name") or "")
    current_object_type = str(payload.get("object_type") or "table")

    load_database_connections(force=False)
    connections = st.session_state.get("database_connections", [])
    if not connections:
        st.info("Nessuna connessione database disponibile.")
        return

    description = st.text_input(
        "Description",
        value=str(datasource_item.get("description") or ""),
        key=f"edit_database_datasource_description_{datasource_id}",
    )

    selected_connection_id = _render_connection_selector(
        f"edit_database_datasource_{datasource_id}",
        connections,
        current_connection_id=current_connection_id,
    )
    if not selected_connection_id:
        return

    objects_payload = load_database_connection_objects(selected_connection_id, force=False)

    selected_object_type = _render_database_object_type_selector(
        f"edit_database_datasource_{datasource_id}_{selected_connection_id}",
        current_object_type=current_object_type,
    )
    selected_object_name = _render_database_object_selector(
        objects_payload,
        key_prefix=f"edit_database_datasource_{datasource_id}_{selected_connection_id}_{selected_object_type}",
        object_type=selected_object_type,
        current_object_name=current_object_name if selected_object_type == current_object_type else "",
    )

    if not st.button(
        "Save changes",
        key=f"edit_database_datasource_save_{datasource_id}",
        icon=":material/save:",
        use_container_width=True,
        disabled=not bool(str(selected_object_name or "").strip()),
    ):
        return

    if not datasource_id:
        st.error("Id datasource non valido.")
        return
    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona un database object valido.")
        return

    updated_payload = _build_dataset_payload(
        selected_connection_id,
        objects_payload.get("schema"),
        selected_object_name,
        selected_object_type,
    )
    try:
        api_put(
            "/data-source/database",
            {
                "id": datasource_id,
                "description": description,
                "payload": updated_payload,
            },
        )
    except Exception as exc:
        st.error(f"Errore aggiornamento dataset: {str(exc)}")
        return

    load_database_datasources(force=True)
    invalidate_database_datasource_preview(datasource_id)
    st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = datasource_id
    st.rerun()


@st.dialog("Conferma eliminazione")
def delete_database_datasource_dialog(datasource_item: dict):
    datasource_id = str(datasource_item.get("id") or "")
    datasource_label = (
        datasource_item.get("description")
        or datasource_id
        or "-"
    )
    st.write(f"Eliminare il dataset '{datasource_label}'?")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_database_datasource_confirm_{datasource_id}"):
            try:
                api_delete(f"/data-source/database/{datasource_id}")
            except Exception as exc:
                st.error(f"Errore cancellazione dataset: {str(exc)}")
                return

            load_database_datasources(force=True)
            invalidate_database_datasource_preview(datasource_id)
            datasource_list = st.session_state.get("database_datasources", [])
            if datasource_list:
                st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = str(
                    datasource_list[0].get("id")
                )
            else:
                st.session_state.pop(SELECTED_DATABASE_DATASOURCE_ID_KEY, None)
            st.rerun()
    with col_cancel:
        st.button("Annulla", key=f"delete_database_datasource_cancel_{datasource_id}")


@st.dialog("Perimeter dataset", width="large")
def edit_dataset_perimeter_dialog(datasource_item: dict):
    datasource_id = str(datasource_item.get("id") or "")
    description = str(datasource_item.get("description") or "")
    payload = (
        datasource_item.get("payload")
        if isinstance(datasource_item.get("payload"), dict)
        else {}
    )
    perimeter = (
        datasource_item.get("perimeter")
        if isinstance(datasource_item.get("perimeter"), dict)
        else None
    )

    connection_id = str(payload.get("connection_id") or "").strip()
    object_name = str(payload.get("object_name") or "").strip()
    object_type = str(payload.get("object_type") or "table").strip().lower() or "table"
    schema = payload.get("schema")

    st.caption(f"{description or datasource_id} | {object_type}: {object_name or '-'}")
    perimeter_payload = _render_perimeter_editor(
        f"dataset_perimeter_{datasource_id}",
        connection_id,
        object_name,
        object_type,
        schema,
        perimeter=perimeter,
    )

    if not st.button(
        "Save perimeter",
        key=f"dataset_perimeter_save_{datasource_id}",
        icon=":material/save:",
        use_container_width=True,
        disabled=not bool(datasource_id and connection_id and object_name),
    ):
        return

    try:
        api_put(
            "/data-source/database",
            {
                "id": datasource_id,
                "description": description,
                "payload": payload,
                "perimeter": perimeter_payload,
            },
        )
    except Exception as exc:
        st.error(f"Errore aggiornamento perimetro dataset: {str(exc)}")
        return

    load_database_datasources(force=True)
    invalidate_database_datasource_preview(datasource_id)
    st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = datasource_id
    st.rerun()
