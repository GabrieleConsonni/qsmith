import streamlit as st

from brokers.services.data_loader_service import load_brokers

st.set_page_config(page_title="Qsmith", layout="wide", page_icon=":material/construction:")

home = st.Page("pages/Home.py", title="Home")
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
scenario_editor = st.Page("pages/ScenarioEditor.py", title="Scenario editor")
tools = st.Page("pages/Tools.py", title="Tools")
logs = st.Page("pages/Logs.py", title="Logs")


def _sidebar_nav_button(label: str, page_path: str, key: str, icon: str = ":material/check:"):
    _, label_col = st.sidebar.columns([1, 10], gap="small", vertical_alignment="center")
    with label_col:
        if st.button(label, key=key, icon=icon, type="tertiary"):
            st.switch_page(page_path)

load_brokers()
brokers = st.session_state.get("brokers", [])

st.sidebar.title("Qsmith")
_sidebar_nav_button(
    label="Home",
    page_path="pages/Home.py",
    key="nav_home_page",
    icon=":material/home:",
)
st.sidebar.subheader("Configurations")
_sidebar_nav_button(
    label="SQS broker connections",
    page_path="pages/Brokers.py",
    key="nav_brokers_page",
    icon=":material/cell_tower:",
)
_sidebar_nav_button(
    label="Database connections",
    page_path="pages/DatabaseConnections.py",
    key="nav_database_connections_page",
    icon=":material/database:",
)

st.sidebar.subheader("SQS brokers")
for broker in brokers:
    broker_id = broker.get("id")
    if broker_id:
        _, label_col = st.sidebar.columns([1, 10], gap="small", vertical_alignment="center")
        with label_col:
            if st.button(
                f"{broker.get('description') or broker.get('code') or broker_id}",
                key=f"open_queues_sidebar_{broker_id}",
                icon=":material/clear_all:",
                type="tertiary"
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
    icon=":material/file_json:",
)
_sidebar_nav_button(
    label="Datasets",
    page_path="pages/DatabaseDataSources.py",
    key="nav_database_datasources_page",
    icon=":material/table:",
)
st.sidebar.subheader("Test")
_sidebar_nav_button(
    label="Test scenarios",
    page_path="pages/Scenarios.py",
    key="nav_scenarios_page",
    icon=":material/experiment:",
)
st.sidebar.subheader("Logs & Tools")
_sidebar_nav_button(label="Logs", page_path="pages/Logs.py", key="nav_logs_page")
_sidebar_nav_button(label="Tools", page_path="pages/Tools.py", key="nav_tools_page")


pg = st.navigation(
    {
        "Home": [home],
        "Configurations": [brokers_page, database_connections_page],
        "Brokers & Queues": [queues_page, queue_details],
        "Data Sources": [json_array, database_datasources],
        "Scenarios": [scenarios, scenario_editor],
        "Logs & Tools": [logs, tools]
    },
    position="hidden",
)

pg.run()
