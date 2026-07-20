"""The routing-evaluation gold set one source of truth.

A fixed list of hand-labeled (question -> expected memory type) pairs, 2 per
type. Used by BOTH the CLI eval (demo/eval_phase7.py) and the on-demand eval
endpoint (backend/api/evaluation.py, Phase 9d), so they can never drift apart.
"""

GOLD: list[tuple[str, str]] = [
    ("Why did we choose PostgreSQL over MongoDB?", "decision"),
    ("What were the tradeoffs of switching to JWT auth?", "decision"),
    ("How do we deploy the backend to production?", "workflow"),
    ("What are the steps to onboard a new hire?", "workflow"),
    ("What does the slugify function do?", "code"),
    ("How many times does the RetryClient retry a failed call?", "code"),
    ("What is the office WiFi network name?", "document"),
    ("What is the meal reimbursement limit in the expense policy?", "document"),
    ("What did the team agree about Friday deploys in the retro?", "conversation"),
    ("What was decided about the mobile app in the Q2 planning call?", "conversation"),
]
