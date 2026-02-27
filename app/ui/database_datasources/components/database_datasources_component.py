import streamlit as st

from database_datasources.components.dialogs import (
    SELECTED_DATABASE_DATASOURCE_ID_KEY,
    add_database_datasource_dialog,
    delete_database_datasource_dialog,
    edit_database_datasource_dialog,
)
from database_datasources.services.data_loader_service import (
    invalidate_database_datasource_preview,
    load_database_datasource_preview,
)


def _resolve_selected_datasource_id(datasources: list[dict]) -> str | None:
    datasource_ids = [str(item.get("id")) for item in datasources if item.get("id")]
    selected_id = st.session_state.get(SELECTED_DATABASE_DATASOURCE_ID_KEY)
    if not datasource_ids:
        st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = None
        return None
    if not selected_id or str(selected_id) not in datasource_ids:
        st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = datasource_ids[0]
    return str(st.session_state.get(SELECTED_DATABASE_DATASOURCE_ID_KEY))


def _find_selected_datasource(datasources: list[dict], selected_id: str | None) -> dict | None:
    if not selected_id:
        return None
    return next(
        (
            item
            for item in datasources
            if isinstance(item, dict) and str(item.get("id")) == str(selected_id)
        ),
        None,
    )


@st.dialog("Datasource info")
def datasource_info_dialog(selected_item: dict, connection_label: str):
    payload = selected_item.get("payload") or {}
    st.metric(
        label="Connection",
        value=connection_label or "-",
    )
    st.metric(
        label="Schema",
        value=payload.get("schema") or "-",
    )
    st.metric(
        label=f"{payload.get('object_type', '-')}",
        value=f"{payload.get('object_name', '-')}",
    )



def render_database_datasources_component(
    datasources: list[dict],
    connections: list[dict],
):
    selected_id = _resolve_selected_datasource_id(datasources)
    selected_item = _find_selected_datasource(datasources, selected_id)
    connection_labels = {
        str(item.get("id")): (
            item.get("description") or item.get("code") or str(item.get("id"))
        )
        for item in connections
        if item.get("id")
    }

    list_col, preview_col = st.columns([2, 5], gap="medium", vertical_alignment="top")

    with list_col:
        with st.container(border=True):
            if datasources:
                for idx, datasource_item in enumerate(datasources):
                    datasource_id = str(datasource_item.get("id") or "")
                    description = (
                        datasource_item.get("description")
                        or datasource_item.get("code")
                        or datasource_id
                        or "-"
                    )
                    is_selected = str(selected_id) == datasource_id
                    row_cols = st.columns([6, 1], gap="small", vertical_alignment="center")
                    with row_cols[0]:
                        if st.button(
                            description,
                            key=f"select_database_datasource_btn_{datasource_id or idx}",
                            type="primary" if is_selected else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state[SELECTED_DATABASE_DATASOURCE_ID_KEY] = datasource_id
                            st.rerun()
                    with row_cols[1]:
                        if st.button(
                            "",
                            key=f"delete_database_datasource_btn_{datasource_id or idx}",
                            icon=":material/delete:",
                            help="Delete datasource",
                            use_container_width=True,
                            type="tertiary"
                        ):
                            delete_database_datasource_dialog(datasource_item)

        if st.button(
            "Add new dataset",
            key="add_database_datasource_btn",
            icon=":material/add:",
            help="Add database datasource",
            use_container_width=True,
            type="tertiary"
        ):
            add_database_datasource_dialog()


    with preview_col:
        with st.container(border=True):
            if not selected_item:
                st.info("Seleziona un dataset dalla lista a sinistra.")
            else:
                payload = selected_item.get("payload") or {}
                connection_id = str(payload.get("connection_id") or "")
                connection_label = connection_labels.get(connection_id, connection_id or "-")

                header_cols = st.columns([10, 1], gap="small", vertical_alignment="center")
                with header_cols[0]:
                    st.subheader(selected_item.get("description") or "-")
                with header_cols[1]:
                    if st.button(
                        "",
                        key=f"database_datasource_info_btn_{selected_id}",
                        icon=":material/info:",
                        help="Datasource info",
                        use_container_width=True,
                    ):
                        datasource_info_dialog(selected_item, connection_label)

                preview_payload = load_database_datasource_preview(selected_id, force=False)
                if isinstance(preview_payload, dict) and preview_payload.get("error"):
                    st.error(f"Errore preview: {preview_payload.get('error')}")
                else:
                    rows = (
                        preview_payload.get("rows")
                        if isinstance(preview_payload, dict)
                        else []
                    )
                    if rows:
                        st.dataframe(rows, use_container_width=True, height=420)
                    else:
                        st.info("Nessun dato disponibile per la preview.")

        tool_cols = st.columns([6, 2, 2], gap="small")
        with tool_cols[1]:
            if st.button(
                "Refresh preview",
                key="database_datasource_refresh_preview_btn",
                icon=":material/refresh:",
                type="secondary",
                use_container_width=True,
                disabled=not bool(selected_item),
            ):
                if selected_id:
                    invalidate_database_datasource_preview(selected_id)
                    load_database_datasource_preview(selected_id, force=True)
                st.rerun()
        with tool_cols[2]:
            if st.button(
                "Edit",
                key="database_datasource_edit_selected_btn",
                icon=":material/edit:",
                type="secondary",
                use_container_width=True,
                disabled=not bool(selected_item),
            ):
                if selected_item:
                    edit_database_datasource_dialog(selected_item)



