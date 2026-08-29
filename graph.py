"""LangGraph HITL workflow for deterministic churn-risk demonstrations."""

from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from audit import append_audit_entry
from models import AuditEntry


CONFIDENCE_THRESHOLD = 0.85
HIGH_RISK_ACTION = "increase_credit_limit"
AGENT_ID = "churn-risk-agent"


class GraphState(TypedDict, total=False):
    customer_id: str
    total_operating_income: float
    churn_probability: float
    proposed_action: str
    confidence_score: float
    reasoning: str
    human_decision: str | None
    edited_action: str | None
    reviewer_id: str | None
    execution_result: str


def evaluate_customer(state: GraphState) -> dict[str, Any]:
    """Mock agent reasoning based on churn probability and customer income."""
    churn = float(state.get("churn_probability", 0.5))
    income = float(state.get("total_operating_income", 0))
    if churn >= 0.70:
        action = HIGH_RISK_ACTION
        confidence = 0.96
        reasoning = (
            f"Churn probability is {churn:.0%}; income is {income:,.0f}. "
            "A credit-limit increase could improve retention, but policy requires review."
        )
    else:
        action = "send_email"
        confidence = 0.92 if churn >= 0.40 else 0.88
        reasoning = (
            f"Churn probability is {churn:.0%}; income is {income:,.0f}. "
            "A retention email is a low-risk intervention."
        )
    return {"proposed_action": action, "confidence_score": confidence, "reasoning": reasoning}


def route_action(state: GraphState) -> Literal["execute_low_risk_action", "execute_high_risk_action"]:
    """Apply hard policy before confidence-based routing."""
    if state["proposed_action"] == HIGH_RISK_ACTION:
        return "execute_high_risk_action"
    if state["confidence_score"] >= CONFIDENCE_THRESHOLD:
        return "execute_low_risk_action"
    return "execute_high_risk_action"


def execute_low_risk_action(state: GraphState) -> dict[str, str]:
    return {"execution_result": f"Auto-executed {state['proposed_action']} for {state['customer_id']}."}


def execute_high_risk_action(state: GraphState) -> dict[str, str]:
    decision = (state.get("human_decision") or "pending").lower()
    action = state.get("edited_action") or state["proposed_action"]
    if decision == "approve" or decision == "edit":
        result = f"Human-approved and executed {action} for {state['customer_id']}."
    elif decision == "reject":
        result = f"Human-rejected {state['proposed_action']} for {state['customer_id']}; no action taken."
    else:
        result = "Pending human review."
    if decision in {"approve", "reject", "edit"}:
        append_audit_entry(
            AuditEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent_id=AGENT_ID,
                action=action,
                confidence=state["confidence_score"],
                reviewer_id=state.get("reviewer_id") or "unknown-reviewer",
                decision=decision,
            )
        )
    return {"execution_result": result}


def build_graph(audit_path: str = "audit_log.json"):
    """Compile a checkpointed graph with a pause before high-risk execution."""
    # The node closes over the selected audit path, which is useful for tests/UI.
    def high_risk_with_path(state: GraphState) -> dict[str, str]:
        decision = (state.get("human_decision") or "pending").lower()
        action = state.get("edited_action") or state["proposed_action"]
        if decision == "approve" or decision == "edit":
            result = f"Human-approved and executed {action} for {state['customer_id']}."
        elif decision == "reject":
            result = f"Human-rejected {state['proposed_action']} for {state['customer_id']}; no action taken."
        else:
            result = "Pending human review."
        if decision in {"approve", "reject", "edit"}:
            append_audit_entry(AuditEntry(timestamp=datetime.now(timezone.utc).isoformat(), agent_id=AGENT_ID,
                action=action, confidence=state["confidence_score"], reviewer_id=state.get("reviewer_id") or "unknown-reviewer",
                decision=decision), audit_path)
        return {"execution_result": result}

    builder = StateGraph(GraphState)
    builder.add_node("evaluate_customer", evaluate_customer)
    builder.add_node("execute_low_risk_action", execute_low_risk_action)
    builder.add_node("execute_high_risk_action", high_risk_with_path)
    builder.add_edge(START, "evaluate_customer")
    builder.add_conditional_edges("evaluate_customer", route_action)
    builder.add_edge("execute_low_risk_action", END)
    builder.add_edge("execute_high_risk_action", END)
    return builder.compile(checkpointer=MemorySaver(), interrupt_before=["execute_high_risk_action"])


graph = build_graph()

