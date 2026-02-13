import streamlit as st

from database_datasources.components.database_datasources_container import (
    render_database_datasources_container,
)
from database_datasources.services.data_loader_service import (
    load_database_connections,
    load_database_datasources,
)

load_database_connections(force=False)
load_database_datasources(force=False)

st.subheader("Datasets")
st.caption("Configure datasets from database connections.")
st.divider()

datasources = st.session_state.get("database_datasources", [])
connections = st.session_state.get("database_connections", [])

render_database_datasources_container(
    datasources if isinstance(datasources, list) else [],
    connections if isinstance(connections, list) else [],
)

