# Day 27 — Human-in-the-Loop (HITL)

This project demonstrates a LangGraph churn-risk workflow that pauses before high-risk actions and resumes only after a human decision.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
streamlit run app.py
```

Run the automated checks with `pytest`.

## Policy and routing

The confidence threshold is **0.85**. `send_email` auto-executes at or above the threshold. Any lower-confidence action is escalated. The hard policy rule always escalates `increase_credit_limit`, even when confidence is high. The graph uses `MemorySaver()` and `interrupt_before=["execute_high_risk_action"]` so the proposed action and reasoning survive the pause.

In the UI, enter a customer, review the proposal, then choose Approve, Reject, or Edit. Edit stores the replacement action before resuming the graph.

## Audit trail

Human decisions are appended to `audit_log.json` with timestamp, agent ID, action, confidence, reviewer ID, and decision. No credentials or API keys are required; the evaluator is deterministic for reproducible lab testing. A production system should replace the JSON file with an append-only database.

