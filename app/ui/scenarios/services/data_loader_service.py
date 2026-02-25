import streamlit as st

from scenarios.services.scenario_api_service import (
    get_all_brokers,
    get_all_database_datasources,
    get_all_json_arrays,
    get_all_operations,
    get_queues_by_broker_id,
    get_all_scenarios,
    get_all_steps,
)
from scenarios.services.state_keys import (
    OPERATIONS_CATALOG_KEY,
    SCENARIOS_KEY,
    STEP_EDITOR_BROKERS_KEY,
    STEP_EDITOR_DATABASE_DATASOURCES_KEY,
    STEP_EDITOR_JSON_ARRAYS_KEY,
    STEP_EDITOR_QUEUES_BY_BROKER_KEY,
    STEPS_CATALOG_KEY,
)


def load_scenarios(force: bool = False):
    if force or SCENARIOS_KEY not in st.session_state:
        try:
            st.session_state[SCENARIOS_KEY] = get_all_scenarios()
        except Exception:
            st.session_state[SCENARIOS_KEY] = []
            st.error("Errore caricamento scenari.")


def load_steps_catalog(force: bool = False):
    if force or STEPS_CATALOG_KEY not in st.session_state:
        try:
            st.session_state[STEPS_CATALOG_KEY] = get_all_steps()
        except Exception:
            st.session_state[STEPS_CATALOG_KEY] = []
            st.error("Errore caricamento steps.")


def load_operations_catalog(force: bool = False):
    if force or OPERATIONS_CATALOG_KEY not in st.session_state:
        try:
            st.session_state[OPERATIONS_CATALOG_KEY] = get_all_operations()
        except Exception:
            st.session_state[OPERATIONS_CATALOG_KEY] = []
            st.error("Errore caricamento operations.")


def load_step_editor_json_arrays(force: bool = False):
    if force or STEP_EDITOR_JSON_ARRAYS_KEY not in st.session_state:
        try:
            st.session_state[STEP_EDITOR_JSON_ARRAYS_KEY] = get_all_json_arrays()
        except Exception:
            st.session_state[STEP_EDITOR_JSON_ARRAYS_KEY] = []
            st.error("Errore caricamento json-array per step.")


def load_step_editor_database_datasources(force: bool = False):
    if force or STEP_EDITOR_DATABASE_DATASOURCES_KEY not in st.session_state:
        try:
            st.session_state[STEP_EDITOR_DATABASE_DATASOURCES_KEY] = (
                get_all_database_datasources()
            )
        except Exception:
            st.session_state[STEP_EDITOR_DATABASE_DATASOURCES_KEY] = []
            st.error("Errore caricamento database datasources per step.")


def load_step_editor_brokers(force: bool = False):
    if force or STEP_EDITOR_BROKERS_KEY not in st.session_state:
        try:
            st.session_state[STEP_EDITOR_BROKERS_KEY] = get_all_brokers()
        except Exception:
            st.session_state[STEP_EDITOR_BROKERS_KEY] = []
            st.error("Errore caricamento broker per step.")


def load_step_editor_queues_for_broker(broker_id: str, force: bool = False) -> list[dict]:
    broker_id_value = str(broker_id or "").strip()
    if not broker_id_value:
        return []

    queues_by_broker = st.session_state.setdefault(STEP_EDITOR_QUEUES_BY_BROKER_KEY, {})
    if not isinstance(queues_by_broker, dict):
        queues_by_broker = {}
        st.session_state[STEP_EDITOR_QUEUES_BY_BROKER_KEY] = queues_by_broker

    if force or broker_id_value not in queues_by_broker:
        try:
            queues_by_broker[broker_id_value] = get_queues_by_broker_id(broker_id_value)
        except Exception:
            queues_by_broker[broker_id_value] = []
            st.error("Errore caricamento queue per broker nello step editor.")

    queues = queues_by_broker.get(broker_id_value)
    return queues if isinstance(queues, list) else []


def load_step_editor_context(force: bool = False):
    load_step_editor_json_arrays(force=force)
    load_step_editor_database_datasources(force=force)
    load_step_editor_brokers(force=force)


def load_scenarios_context(force: bool = False):
    load_scenarios(force=force)
    load_steps_catalog(force=force)
    load_operations_catalog(force=force)
    load_step_editor_context(force=force)
