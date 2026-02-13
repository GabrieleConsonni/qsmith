import streamlit as st

from scenarios.services.scenario_api_service import (
    get_all_operations,
    get_all_scenarios,
    get_all_steps,
)
from scenarios.services.state_keys import (
    OPERATIONS_CATALOG_KEY,
    SCENARIOS_KEY,
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


def load_scenarios_context(force: bool = False):
    load_scenarios(force=force)
    load_steps_catalog(force=force)
    load_operations_catalog(force=force)

