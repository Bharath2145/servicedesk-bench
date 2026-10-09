import unittest
from src.tasks import TASKS
from src.splits import get_split, split_of, mutate, describe
from src.stats import bootstrap_ci
from src.judge import score_from_trajectory, heuristic_score
from src.harness import run_task
from src.agents import OracleAgent
from src.llm_agent import LLMAgent


class TestExtensions(unittest.TestCase):
    def test_split_covers_all_once(self):
        pub, held = get_split(TASKS, "public"), get_split(TASKS, "heldout")
        self.assertEqual(len(pub) + len(held), len(TASKS))
        self.assertEqual(len(set(t["id"] for t in pub) & set(t["id"] for t in held)), 0)
        self.assertGreater(len(pub), len(held))

    def test_mutation_preserves_verifiers(self):
        t = TASKS[0]
        m = mutate(t, 3)
        self.assertEqual(m["ticket_id"], t["ticket_id"])
        self.assertEqual(m["verify"], t["verify"])
        self.assertNotEqual(m["prompt"], t["prompt"])

    def test_bootstrap_ci_contains_point_estimate(self):
        lo, hi, base = bootstrap_ci([True] * 11 + [False] * 13)
        self.assertLessEqual(lo, base)
        self.assertGreaterEqual(hi, base)

    def test_judge_scores_good_notes_high(self):
        r = run_task(OracleAgent(), TASKS[0])
        j = score_from_trajectory(TASKS[0], r["trajectory"])
        self.assertGreaterEqual(j["score"], 1)
        self.assertIn(j["method"], ("heuristic", "llm"))

    def test_judge_zero_for_no_notes(self):
        s, _ = heuristic_score([])
        self.assertEqual(s, 0)

    def test_llm_agent_offline_fallback_runs(self):
        import os
        os.environ.pop("OPENAI_API_KEY", None)  # force offline
        r = run_task(LLMAgent(), TASKS[0])
        self.assertIn("passed", r)


if __name__ == "__main__":
    unittest.main()
