"""Streamlit approval console for the HITL graph."""

import uuid
from pathlib import Path

import streamlit as st

from graph import build_graph


st.set_page_config(page_title="Day 27 • HITL", page_icon="🧑‍⚖️", layout="centered")
st.title("🧑‍⚖️ Human-in-the-Loop Review")
st.caption("Churn-risk agent • hard policy + confidence routing")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph(str(Path(__file__).with_name("audit_log.json")))
if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}

with st.form("customer_form"):
    customer_id = st.text_input("Customer ID", "CUST001")
    income = st.number_input("Total operating income", min_value=0.0, value=100000.0, step=1000.0)
    churn = st.slider("Churn probability", 0.0, 1.0, 0.78, 0.01)
    submitted = st.form_submit_button("Evaluate customer", type="primary")

if submitted:
    st.session_state.config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    st.session_state.graph.invoke({"customer_id": customer_id, "total_operating_income": income,
        "churn_probability": churn, "human_decision": None}, st.session_state.config)
    st.rerun()

state = st.session_state.graph.get_state(st.session_state.config)
values = state.values
if values.get("proposed_action"):
    st.subheader("Action proposal")
    st.metric("Customer", values.get("customer_id"))
    st.write(f"**Proposed action:** `{values.get('proposed_action')}`")
    st.write(f"**Confidence:** `{values.get('confidence_score', 0):.0%}`")
    st.info(values.get("reasoning", ""))

    if state.next:
        reviewer = st.text_input("Reviewer ID", "operator_01")
        edited = st.text_input("Edited action (used only for Edit)", values.get("proposed_action", ""))
        c1, c2, c3 = st.columns(3)
        decision = None
        if c1.button("Approve", use_container_width=True): decision = "approve"
        if c2.button("Reject", use_container_width=True): decision = "reject"
        if c3.button("Edit", use_container_width=True): decision = "edit"
        if decision:
            update = {"human_decision": decision, "reviewer_id": reviewer}
            if decision == "edit": update["edited_action"] = edited
            st.session_state.graph.update_state(st.session_state.config, update)
            st.session_state.graph.invoke(None, st.session_state.config)
            st.rerun()
    elif values.get("execution_result"):
        st.success(values["execution_result"])

