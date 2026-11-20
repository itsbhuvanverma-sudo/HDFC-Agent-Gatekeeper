# PROMPTS.md — Agent Gatekeeper

## Project
HDFC Bank classroom prototype — enrolment number PGD202567305.

## Main coding-agent instructions
1. Build a beginner-friendly Streamlit application named Agent Gatekeeper.
2. Display HDFC Bank (classroom prototype) and enrolment number PGD202567305 on the main screen.
3. Accept customer name, AI agent name, action, and amount.
4. Return ALLOW, ASK CUSTOMER, or BLOCK with a rule number and plain-language reason.
5. Implement rules R1–R7 from the project report.
6. Register agents and revoke them. Save registration and revocation timestamps.
7. Write every evaluated request to a local CSV audit log with timestamp, request, decision, rule, and reason.
8. Store the agent registry in a local JSON file.
9. Include a page showing rules and six suggested test cases.
10. Do not connect to a real bank, request credentials, or execute payments.

## One thing I checked/changed myself
[I personally tested the agent revocation feature by registering RahulTestAgent, revoking its permission, checking the saved revocation timestamp, and verifying that a subsequent ₹1,000 bill payment request returned BLOCK under Rule R2.]
