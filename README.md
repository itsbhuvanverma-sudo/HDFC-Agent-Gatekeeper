# Agent Gatekeeper — HDFC Bank classroom prototype

**Enrolment number:** PGD202567305

A small Streamlit demonstration that evaluates requests from registered AI agents using proposed classroom rules.

## Safety notice
This is not an HDFC Bank product and is not connected to any bank account. It does not access real customer data or execute payments. Names and seeded records are fictional examples.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (optional but recommended).
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `streamlit run app.py`

## Files
- `app.py` — Streamlit app and decision rules
- `agents.json` — local agent registry (includes demo records)
- `audit_log.csv` — created when the first request is evaluated
- `PROMPTS.md` — coding-agent prompt record to complete with your genuine checks

## Rule summary
R1 unknown agent: BLOCK
R2 revoked agent: BLOCK
R3 active registered agent viewing balance: ALLOW
R4 active registered agent paying a bill up to ₹5,000: ALLOW
R5 bill payment above ₹5,000: ASK CUSTOMER
R6 any money transfer: ASK CUSTOMER
R7 unsupported action: BLOCK

The ₹5,000 threshold is a proposed classroom limit, not an HDFC Bank policy.
