import unittest
from src.env import EnterpriseEnv
from src.tools import call_tool
from src.tasks import TASKS, apply_setup
from src.agents import HeuristicAgent, ReActAgent, OracleAgent
from src.harness import run_task, run_benchmark


class TestEnv(unittest.TestCase):
    def test_seed_counts(self):
        env = EnterpriseEnv.seed()
        self.assertEqual(len(env.users), 6)
        self.assertGreaterEqual(len(env.devices), 5)
        self.assertGreaterEqual(len(env.tickets), 24)

    def test_password_guard(self):
        env = EnterpriseEnv.seed()
        out = call_tool(env, "reset_password", {"user_id": "u_ben", "verified": True})
        self.assertFalse(out["ok"])  # Ben MFA unverified -> must refuse
        out2 = call_tool(env, "reset_password", {"user_id": "u_ava", "verified": True})
        self.assertTrue(out2["ok"])

    def test_unknown_tool_scores_not_crashes(self):
        env = EnterpriseEnv.seed()
        out = call_tool(env, "delete_everything", {})
        self.assertFalse(out["ok"])
        self.assertIn("unknown tool", out["error"])

    def test_oracle_passes_majority(self):
        bench = run_benchmark(OracleAgent(), verbose=False)
        self.assertGreaterEqual(bench["pass_rate"], 0.9)

    def test_difficulty_spread(self):
        h = run_benchmark(HeuristicAgent(), verbose=False)
        o = run_benchmark(OracleAgent(), verbose=False)
        self.assertLess(h["pass_rate"], o["pass_rate"])  # headroom exists

    def test_all_tasks_have_verifiers(self):
        self.assertEqual(len(TASKS), 24)
        env = EnterpriseEnv.seed()
        for t in TASKS:
            e = apply_setup(env.clone(), t)
            passed, checks = t["verify"](e, [])
            self.assertIsInstance(checks, dict)


if __name__ == "__main__":
    unittest.main()
