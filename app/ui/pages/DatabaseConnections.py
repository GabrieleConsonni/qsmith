import streamlit as st

from database_connections.components.database_connections_container import (
    render_database_connections_container,
)
from database_connections.services.data_loader_service import load_database_connections

load_database_connections()

st.subheader("Database connections")
st.caption("Configure database connections for scenarios and database datasources.")
st.divider()

connections = st.session_state.get("database_connections", [])
render_database_connections_container(connections if isinstance(connections, list) else [])

