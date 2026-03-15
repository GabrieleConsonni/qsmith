import streamlit as st

from test_suites.services.api_service import get_test_suite_executions


st.title("Home")
st.caption("Recent test suite executions.")

executions = get_test_suite_executions(limit=20)
if not executions:
    st.info("No test suite executions available.")
else:
    for execution in executions:
        label = (
            f"{execution.get('status') or '-'} | "
            f"{execution.get('started_at') or '-'} | "
            f"{execution.get('requested_test_id') or execution.get('test_suite_description') or execution.get('id')}"
        )
        with st.expander(label, expanded=False):
            st.write(f"Suite: {execution.get('test_suite_description') or execution.get('test_suite_id') or '-'}")
            st.write(f"Error: {execution.get('error_message') or '-'}")
            for item in execution.get("items") or []:
                st.markdown(
                    f"- {item.get('item_kind')} | {item.get('hook_phase') or item.get('item_description') or item.get('suite_item_id')} | {item.get('status')}"
                )
