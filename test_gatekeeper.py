import csv
import json
import os
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# Ensure Streamlit calls do not fail when running as a headless test script
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()

# Import the application logic
import app


class TestAgentGatekeeperRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_dir = Path(__file__).parent
        cls.agents_file = cls.project_dir / "agents.json"
        cls.audit_file = cls.project_dir / "audit_log.csv"
        cls.backup_agents = cls.project_dir / "agents.json.bak"
        cls.backup_audit = cls.project_dir / "audit_log.csv.bak"

        # Backup existing files if present
        if cls.agents_file.exists():
            shutil.copy2(cls.agents_file, cls.backup_agents)
        if cls.audit_file.exists():
            shutil.copy2(cls.audit_file, cls.backup_audit)

    @classmethod
    def tearDownClass(cls):
        # Restore backup files after tests
        if cls.backup_agents.exists():
            shutil.move(cls.backup_agents, cls.agents_file)
        if cls.backup_audit.exists():
            shutil.move(cls.backup_audit, cls.audit_file)
        elif cls.audit_file.exists():
            cls.audit_file.unlink()

    def setUp(self):
        # Seed fresh standard agents for predictable testing
        test_seed = {
            "DemoAssistant": {
                "customer": "Asha Sharma",
                "registered_at": "DEMO-SEED-RECORD",
                "revoked_at": None
            },
            "RevokedAssistant": {
                "customer": "Ravi Kumar",
                "registered_at": "DEMO-SEED-RECORD",
                "revoked_at": "2026-11-20T10:00:00+05:30"
            }
        }
        with open(self.agents_file, "w", encoding="utf-8") as f:
            json.dump(test_seed, f, indent=2)

    def test_enrolment_number(self):
        """Verify enrolment number is correctly configured."""
        self.assertEqual(app.ENROLMENT_NO, "PGD202567305")

    def test_r1_unknown_agent_blocked(self):
        """R1: Unknown agents must be blocked."""
        decision, rule, reason = app.decide_request("Asha Sharma", "UnknownBot", "view_balance", 0)
        self.assertEqual(decision, "BLOCK")
        self.assertEqual(rule, "R1")
        self.assertIn("not registered", reason)

    def test_r2_revoked_agent_blocked_zero_amount(self):
        """R2: Revoked agents must be blocked even for 0 amount."""
        decision, rule, reason = app.decide_request("Ravi Kumar", "RevokedAssistant", "view_balance", 0)
        self.assertEqual(decision, "BLOCK")
        self.assertEqual(rule, "R2")
        self.assertIn("revoked", reason)

    def test_r2_revoked_agent_blocked_small_amount(self):
        """R2: Revoked agents must be blocked even if transaction amount is small (e.g. ₹1,000)."""
        decision, rule, reason = app.decide_request("Ravi Kumar", "RevokedAssistant", "pay_bill", 1000)
        self.assertEqual(decision, "BLOCK")
        self.assertEqual(rule, "R2")
        self.assertIn("revoked", reason)

    def test_r3_view_balance_allowed(self):
        """R3: Registered active agents can view balances."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "view_balance", 0)
        self.assertEqual(decision, "ALLOW")
        self.assertEqual(rule, "R3")

    def test_r4_pay_bill_within_limit_allowed(self):
        """R4: Bill payments up to ₹5,000 are allowed."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "pay_bill", 2000)
        self.assertEqual(decision, "ALLOW")
        self.assertEqual(rule, "R4")

    def test_r4_pay_bill_exact_limit_allowed(self):
        """R4: Bill payments exactly at ₹5,000 boundary are allowed."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "pay_bill", 5000)
        self.assertEqual(decision, "ALLOW")
        self.assertEqual(rule, "R4")

    def test_r5_pay_bill_above_limit_requires_confirmation(self):
        """R5: Bill payments above ₹5,000 require customer confirmation."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "pay_bill", 5001)
        self.assertEqual(decision, "ASK CUSTOMER")
        self.assertEqual(rule, "R5")

        decision2, rule2, reason2 = app.decide_request("Asha Sharma", "DemoAssistant", "pay_bill", 15000)
        self.assertEqual(decision2, "ASK CUSTOMER")
        self.assertEqual(rule2, "R5")

    def test_r6_transfer_money_requires_confirmation(self):
        """R6: All money transfers require customer confirmation."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "transfer_money", 3000)
        self.assertEqual(decision, "ASK CUSTOMER")
        self.assertEqual(rule, "R6")

    def test_r6_transfer_money_small_amount_requires_confirmation(self):
        """R6: Money transfers require confirmation even for small amounts."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "transfer_money", 100)
        self.assertEqual(decision, "ASK CUSTOMER")
        self.assertEqual(rule, "R6")

    def test_r7_unsupported_action_blocked(self):
        """R7: Unsupported actions must be blocked."""
        decision, rule, reason = app.decide_request("Asha Sharma", "DemoAssistant", "withdraw_cash", 1000)
        self.assertEqual(decision, "BLOCK")
        self.assertEqual(rule, "R7")

    def test_audit_logging_csv(self):
        """Verify audit log records correctly in CSV format."""
        if self.audit_file.exists():
            self.audit_file.unlink()

        app.record_audit("Asha Sharma", "DemoAssistant", "pay_bill", 2000, "ALLOW", "R4", "Bill payment within limit")
        self.assertTrue(self.audit_file.exists())

        with open(self.audit_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            expected_fields = ["timestamp", "customer", "agent_name", "action", "amount_inr", "decision", "rule", "reason"]
            self.assertEqual(fieldnames, expected_fields)
            rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["decision"], "ALLOW")
            self.assertEqual(rows[0]["rule"], "R4")

    def test_register_and_revoke_lifecycle(self):
        """Verify registering a new agent and revoking an agent preserves exact timestamps."""
        agents = app.load_agents()
        test_agent = "LifecycleBot"
        now_ts = datetime.now().astimezone().isoformat(timespec="seconds")
        agents[test_agent] = {
            "customer": "Test Customer",
            "registered_at": now_ts,
            "revoked_at": None
        }
        app.save_agents(agents)

        # Confirm registered
        loaded = app.load_agents()
        self.assertIn(test_agent, loaded)
        self.assertEqual(loaded[test_agent]["registered_at"], now_ts)
        self.assertIsNone(loaded[test_agent]["revoked_at"])

        # Allowed while active
        dec, r, _ = app.decide_request("Test Customer", test_agent, "view_balance", 0)
        self.assertEqual(dec, "ALLOW")
        self.assertEqual(r, "R3")

        # Now revoke
        revoke_ts = datetime.now().astimezone().isoformat(timespec="seconds")
        loaded[test_agent]["revoked_at"] = revoke_ts
        app.save_agents(loaded)

        # Confirm revoked
        re_loaded = app.load_agents()
        self.assertEqual(re_loaded[test_agent]["revoked_at"], revoke_ts)

        # Must now be blocked by R2
        dec2, r2, _ = app.decide_request("Test Customer", test_agent, "view_balance", 0)
        self.assertEqual(dec2, "BLOCK")
        self.assertEqual(r2, "R2")


if __name__ == "__main__":
    unittest.main()
