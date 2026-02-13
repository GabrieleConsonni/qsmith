import streamlit as st

from brokers.services.data_loader_service import load_brokers

st.set_page_config(page_title="Qsmith UI", layout="wide")

st.sidebar.title("Qsmith")

brokers_page = st.Page("pages/Brokers.py", title="Brokers")
database_connections_page = st.Page(
    "pages/DatabaseConnections.py",
    title="Database Connections",
)
queues_page = st.Page("pages/Queues.py", title="Queues", url_path="queues")
queue_details = st.Page("pages/QueueDetails.py", title="Queue details")
json_array = st.Page("pages/JsonArray.py", title="Json Array")
database_datasources = st.Page(
    "pages/DatabaseDataSources.py",
    title="Database Datasources",
)
scenarios = st.Page("pages/Scenarios.py", title="Scenarios")
tools = st.Page("pages/Tools.py", title="Tools")
logs = st.Page("pages/Logs.py", title="Logs")


def _sidebar_nav_button(label: str, page_path: str, key: str):
    if st.sidebar.button(label, key=key, use_container_width=True):
        st.switch_page(page_path)


load_brokers()
brokers = st.session_state.get("brokers", [])

st.sidebar.subheader("Configurations")
_sidebar_nav_button(
    label="SQS broker connections",
    page_path="pages/Brokers.py",
    key="nav_brokers_page",
)
_sidebar_nav_button(
    label="Database connections",
    page_path="pages/DatabaseConnections.py",
    key="nav_database_connections_page",
)

st.sidebar.subheader("SQS brokers")
for broker in brokers:
    broker_id = broker.get("id")
    if broker_id:
        if st.sidebar.button(
            f"{broker.get('description') or broker.get('code') or broker_id}",
            key=f"open_queues_sidebar_{broker_id}",
            use_container_width=True,
        ):
            st.session_state["selected_broker_id"] = broker_id
            st.session_state["queues_filter_broker_id"] = broker_id
            st.session_state["nav_broker_id"] = broker_id
            st.switch_page("pages/Queues.py")
            
st.sidebar.subheader("Datasources")
_sidebar_nav_button(
    label="Json Array",
    page_path="pages/JsonArray.py",
    key="nav_json_array_page",
)
_sidebar_nav_button(
    label="Datasets",
    page_path="pages/DatabaseDataSources.py",
    key="nav_database_datasources_page",
)
st.sidebar.subheader("Scenarios")
_sidebar_nav_button(
    label="Scenarios",
    page_path="pages/Scenarios.py",
    key="nav_scenarios_page",
)
st.sidebar.subheader("Logs & Tools")
_sidebar_nav_button(label="Logs", page_path="pages/Logs.py", key="nav_logs_page")
_sidebar_nav_button(label="Tools", page_path="pages/Tools.py", key="nav_tools_page")


pg = st.navigation(
    {
        "Configurations": [brokers_page, database_connections_page],
        "Brokers & Queues": [queues_page, queue_details],
        "Data Sources": [json_array, database_datasources],
        "Scenarios": [scenarios],
        "Logs & Tools": [logs, tools]
    },
    position="hidden",
)

pg.run()
