import csv
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

# HDFC Bank is used as a fictional demonstration context.
# This prototype is NOT connected to HDFC Bank or any real bank account.
BASE_DIR = Path(__file__).parent
AGENTS_FILE = BASE_DIR / "agents.json"
AUDIT_FILE = BASE_DIR / "audit_log.csv"
ENROLMENT_NO = "PGD202567305"
BANK_NAME = "HDFC Bank (classroom prototype)"
PAYMENT_LIMIT = 5000

ACTIONS = ["view_balance", "pay_bill", "transfer_money"]


def load_agents():
    if not AGENTS_FILE.exists():
        return {}
    with AGENTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_agents(agents):
    with AGENTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(agents, f, indent=2)


def ensure_audit_file():
    if not AUDIT_FILE.exists():
        with AUDIT_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "customer", "agent_name", "action",
                "amount_inr", "decision", "rule", "reason"
            ])


def record_audit(customer, agent_name, action, amount, decision, rule, reason):
    ensure_audit_file()
    with AUDIT_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().astimezone().isoformat(timespec="seconds"),
            customer, agent_name, action, amount, decision, rule, reason
        ])


def decide_request(customer, agent_name, action, amount):
    agents = load_agents()
    agent = agents.get(agent_name)

    # Priority matters: revoked and unknown agents are checked first.
    if agent is None:
        return "BLOCK", "R1", "This agent is not registered."

    if agent.get("revoked_at"):
        return "BLOCK", "R2", f"Agent permission was revoked at {agent['revoked_at']}."

    if action not in ACTIONS:
        return "BLOCK", "R7", "This action is not supported by the prototype."

    if action == "view_balance":
        return "ALLOW", "R3", "Registered and active agent; balance viewing is read-only."

    if action == "pay_bill":
        if amount <= PAYMENT_LIMIT:
            return "ALLOW", "R4", f"Bill payment is within the ₹{PAYMENT_LIMIT:,} demonstration limit."
        return "ASK CUSTOMER", "R5", f"Payment exceeds ₹{PAYMENT_LIMIT:,}; customer confirmation is required."

    if action == "transfer_money":
        return "ASK CUSTOMER", "R6", "All money transfers require direct customer confirmation."

    return "BLOCK", "R7", "Unsupported action."


st.set_page_config(page_title="Agent Gatekeeper | HDFC Bank", page_icon="🛡️", layout="wide")
st.title("🛡️ Agent Gatekeeper")
st.subheader(BANK_NAME)
st.caption(f"Enrolment Number: {ENROLMENT_NO}  |  Demonstration only — no real banking connection")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Choose a section", ["Evaluate request", "Register / revoke agent", "Audit log", "Rules & test cases"])
    st.divider()
    st.metric("Bill payment limit", f"₹{PAYMENT_LIMIT:,}")
    st.caption("Prototype data is stored locally in JSON and CSV files.")

if page == "Evaluate request":
    st.header("Evaluate an AI agent request")
    agents = load_agents()
    with st.form("request_form"):
        customer = st.text_input("Customer name", placeholder="e.g. Asha Sharma")
        agent_name = st.text_input("AI agent name", placeholder="e.g. MyAssistant")
        action = st.selectbox("Requested action", ACTIONS, format_func=lambda x: {
            "view_balance": "View balance",
            "pay_bill": "Pay a bill",
            "transfer_money": "Transfer money"
        }[x])
        amount = st.number_input("Amount (₹) — enter 0 for view balance", min_value=0, step=500)
        submitted = st.form_submit_button("Evaluate request", type="primary")

    if submitted:
        if not customer.strip() or not agent_name.strip():
            st.error("Please enter both customer name and agent name.")
        else:
            decision, rule, reason = decide_request(customer.strip(), agent_name.strip(), action, int(amount))
            record_audit(customer.strip(), agent_name.strip(), action, int(amount), decision, rule, reason)
            if decision == "ALLOW":
                st.success(f"{decision} — {rule}")
            elif decision == "ASK CUSTOMER":
                st.warning(f"{decision} — {rule}")
            else:
                st.error(f"{decision} — {rule}")
            st.write(f"**Reason:** {reason}")
            st.info("ASK CUSTOMER is a decision only. This prototype does not process or execute payments.")

elif page == "Register / revoke agent":
    st.header("Agent permission management")
    agents = load_agents()
    left, right = st.columns(2)
    with left:
        st.subheader("Register a new agent")
        with st.form("register_form"):
            customer = st.text_input("Customer name", key="reg_customer")
            agent_name = st.text_input("Unique agent name", key="reg_agent")
            register = st.form_submit_button("Register agent")
        if register:
            if not customer.strip() or not agent_name.strip():
                st.error("Enter both customer and agent names.")
            elif agent_name.strip() in agents:
                st.error("That agent name is already registered.")
            else:
                agents[agent_name.strip()] = {
                    "customer": customer.strip(),
                    "registered_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "revoked_at": None
                }
                save_agents(agents)
                st.success(f"Registered {agent_name.strip()} for {customer.strip()}.")

    with right:
        st.subheader("Revoke an agent")
        active_agents = [name for name, data in agents.items() if not data.get("revoked_at")]
        if active_agents:
            selected = st.selectbox("Select active agent", active_agents)
            if st.button("Revoke permission", type="primary"):
                agents[selected]["revoked_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                save_agents(agents)
                st.success(f"Revoked {selected}. Revocation timestamp saved.")
                st.rerun()
        else:
            st.info("No active agents to revoke.")

    st.subheader("Registered agents")
    if agents:
        rows = []
        for name, data in agents.items():
            rows.append({
                "Agent": name,
                "Customer": data.get("customer", ""),
                "Registered at": data.get("registered_at", ""),
                "Revoked at": data.get("revoked_at") or "Active"
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No agents registered yet.")

elif page == "Audit log":
    st.header("Audit log")
    ensure_audit_file()
    try:
        with AUDIT_FILE.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if rows:
            st.dataframe(rows[::-1], use_container_width=True, hide_index=True)
            st.download_button("Download audit log CSV", AUDIT_FILE.read_bytes(), "audit_log.csv", "text/csv")
        else:
            st.info("No requests have been evaluated yet.")
    except Exception as exc:
        st.error(f"Could not read audit log: {exc}")

elif page == "Rules & test cases":
    st.header("Decision rules")
    rules = [
        ("R1", "Unknown agents are blocked.", "Prevent unregistered agents from acting."),
        ("R2", "Revoked agents are always blocked.", "Ensure revocation takes immediate priority."),
        ("R3", "Registered active agents may view balances.", "Read-only access is lower risk."),
        ("R4", f"Registered active agents may pay bills up to ₹{PAYMENT_LIMIT:,}.", "Allow limited, low-value routine payments."),
        ("R5", f"Bill payments above ₹{PAYMENT_LIMIT:,} require customer confirmation.", "Add a human check for larger payments."),
        ("R6", "All money transfers require customer confirmation.", "Transfers can move funds to unintended recipients."),
        ("R7", "Unsupported or suspicious actions are blocked.", "Keep the prototype within its defined scope.")
    ]
    st.table([{"Rule": a, "Policy": b, "Reason": c} for a, b, c in rules])
    st.caption("These are proposed classroom rules, not official HDFC Bank policy.")

    st.header("Suggested six tests")
    tests = [
        ["Known active agent", "view_balance", "₹0", "ALLOW — R3"],
        ["Unknown agent", "view_balance", "₹0", "BLOCK — R1"],
        ["Known active agent", "pay_bill", "₹15,000", "ASK CUSTOMER — R5"],
        ["Known active agent", "pay_bill", "₹2,000", "ALLOW — R4"],
        ["Revoked agent", "pay_bill", "₹1,000", "BLOCK — R2"],
        ["Known active agent", "transfer_money", "₹3,000", "ASK CUSTOMER — R6"]
    ]
    st.table([{"Test": i+1, "Scenario": t[0], "Action": t[1], "Amount": t[2], "Expected": t[3]} for i, t in enumerate(tests)])

st.divider()
st.caption("Educational prototype only. It does not connect to HDFC Bank, access real customer data, or execute financial transactions.")
