import json

from graph import build_graph, evaluate_customer, route_action


def test_hard_policy_overrides_confidence():
    assert route_action({"proposed_action": "increase_credit_limit", "confidence_score": 0.99}) == "execute_high_risk_action"


def test_low_risk_auto_executes():
    assert route_action({"proposed_action": "send_email", "confidence_score": 0.90}) == "execute_low_risk_action"


def test_low_confidence_escalates():
    assert route_action({"proposed_action": "send_email", "confidence_score": 0.82}) == "execute_high_risk_action"


def test_evaluator_returns_required_fields_and_valid_confidence():
    result = evaluate_customer({"customer_id": "CUST001", "churn_probability": 0.5, "total_operating_income": 100})
    assert {"proposed_action", "confidence_score", "reasoning"} <= result.keys()
    assert 0.0 <= result["confidence_score"] <= 1.0


def test_interrupt_preserves_state_and_approve_writes_audit(tmp_path):
    audit = tmp_path / "audit.json"
    workflow = build_graph(str(audit))
    config = {"configurable": {"thread_id": "test-approve"}}
    workflow.invoke({"customer_id": "CUST001", "churn_probability": 0.8, "total_operating_income": 100}, config)
    pending = workflow.get_state(config)
    assert pending.next == ("execute_high_risk_action",)
    assert pending.values["proposed_action"] == "increase_credit_limit"
    workflow.update_state(config, {"human_decision": "approve", "reviewer_id": "tester"})
    result = workflow.invoke(None, config)
    assert "executed" in result["execution_result"]
    assert json.loads(audit.read_text())[0]["decision"] == "approve"


def test_reject_and_edit_are_audited_without_overwriting_history(tmp_path):
    audit = tmp_path / "audit.json"
    workflow = build_graph(str(audit))
    for thread_id, decision, edited_action in [
        ("test-reject", "reject", None),
        ("test-edit", "edit", "send_email"),
    ]:
        config = {"configurable": {"thread_id": thread_id}}
        workflow.invoke({"customer_id": thread_id, "churn_probability": 0.8}, config)
        update = {"human_decision": decision, "reviewer_id": "tester"}
        if edited_action:
            update["edited_action"] = edited_action
        workflow.update_state(config, update)
        workflow.invoke(None, config)
    entries = json.loads(audit.read_text())
    assert [entry["decision"] for entry in entries] == ["reject", "edit"]
    assert entries[1]["action"] == "send_email"
