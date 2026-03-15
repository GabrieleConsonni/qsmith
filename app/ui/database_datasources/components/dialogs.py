import streamlit as st

from api_client import api_delete, api_post, api_put
from database_datasources.services.data_loader_service import (
    invalidate_database_datasource_preview,
    load_database_connection_objects,
    load_database_connections,
    load_database_datasources,
)

SELECTED_DATABASE_DATASOURCE_ID_KEY = "selected_database_datasource_id"


def _connection_label(connection_item: dict) -> str:
    description = str(connection_item.get("description") or connection_item.get("id") or "-")
    payload = connection_item.get("payload") or {}
    connection_type = str(payload.get("database_type") or "-")
    return f"{description} [{connection_type}]"


def _render_objects_tree(
    objects_payload: dict,
    key_prefix: str,
    current_object_name: str = "",
    current_object_type: str = "table",
) -> tuple[str, str]:
    tables = [str(item) for item in (objects_payload.get("tables") or []) if item]
    views = [str(item) for item in (objects_payload.get("views") or []) if item]

    selected_table = ""
    selected_view = ""
    with st.expander("Tables", expanded=True):
        table_options = [""] + tables
        table_index = 0
        if current_object_type == "table" and current_object_name in tables:
            table_index = table_options.index(current_object_name)
        selected_table = st.selectbox(
            "Select table",
            options=table_options,
            index=table_index,
            key=f"{key_prefix}_table_select",
        )
    with st.expander("Views", expanded=True):
        view_options = [""] + views
        view_index = 0
        if current_object_type == "view" and current_object_name in views:
            view_index = view_options.index(current_object_name)
        selected_view = st.selectbox(
            "Select view",
            options=view_options,
            index=view_index,
            key=f"{key_prefix}_view_select",
        )

    if selected_table:
        return "table", selected_table
    if selected_view:
        return "view", selected_view
    return "", ""


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


@st.dialog("Aggiungi database datasource", width="large")
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
    if st.button(
        "Refresh tree",
        key="add_database_datasource_refresh_objects",
        icon=":material/refresh:",
        type="secondary",
    ):
        objects_payload = load_database_connection_objects(selected_connection_id, force=True)

    selected_object_type, selected_object_name = _render_objects_tree(
        objects_payload,
        key_prefix=f"add_database_datasource_{selected_connection_id}",
    )

    if not st.button(
        "Add",
        key="add_database_datasource_save",
        icon=":material/add:",
        use_container_width=True,
    ):
        return

    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona una tabella o una view dal tree.")
        return

    payload = {
        "connection_id": selected_connection_id,
        "schema": objects_payload.get("schema"),
        "object_name": selected_object_name,
        "object_type": selected_object_type,
    }

    try:
        response = api_post(
            "/data-source/database",
            {
                "description": description,
                "payload": payload,
            },
        )
    except Exception as exc:
        st.error(f"Errore salvataggio database datasource: {str(exc)}")
        return

    load_database_datasources(force=True)
    invalidate_database_datasource_preview()
    new_id = response.get("id") if isinstance(response, dict) else None
    if new_id:
        st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = str(new_id)
    st.rerun()


@st.dialog("Modifica database datasource", width="large")
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
    if st.button(
        "Refresh tree",
        key=f"edit_database_datasource_refresh_objects_{datasource_id}",
        icon=":material/refresh:",
        type="secondary",
    ):
        objects_payload = load_database_connection_objects(selected_connection_id, force=True)

    selected_object_type, selected_object_name = _render_objects_tree(
        objects_payload,
        key_prefix=f"edit_database_datasource_{datasource_id}_{selected_connection_id}",
        current_object_name=current_object_name,
        current_object_type=current_object_type,
    )

    if not st.button(
        "Save changes",
        key=f"edit_database_datasource_save_{datasource_id}",
        icon=":material/save:",
        use_container_width=True,
    ):
        return

    if not datasource_id:
        st.error("Id datasource non valido.")
        return
    if not description.strip():
        st.error("Il campo Description e' obbligatorio.")
        return
    if not selected_object_name or not selected_object_type:
        st.error("Seleziona una tabella o una view dal tree.")
        return

    updated_payload = {
        "connection_id": selected_connection_id,
        "schema": objects_payload.get("schema"),
        "object_name": selected_object_name,
        "object_type": selected_object_type,
    }
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
        st.error(f"Errore aggiornamento database datasource: {str(exc)}")
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
    st.write(f"Eliminare il database datasource '{datasource_label}'?")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma", key=f"delete_database_datasource_confirm_{datasource_id}"):
            try:
                api_delete(f"/data-source/database/{datasource_id}")
            except Exception as exc:
                st.error(f"Errore cancellazione database datasource: {str(exc)}")
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
