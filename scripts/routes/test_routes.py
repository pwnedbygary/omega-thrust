#!/usr/bin/env python3
"""Checks the committed route files; no build, disc or BIOS needed.

Run: python3 -B scripts/routes/test_routes.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_route  # noqa: E402

ROUTES = sorted(HERE.glob("*.json"))
LISTED = ["title_to_zone1", "menus", "memcard"] + [f"demo_zone{k}" for k in range(1, 7)]  # AGENTS.md "## Routes"
SHOT_MARGIN = 30  # AGENTS.md: end every shot step 30 frames before the next button change


class CommittedRoutes(unittest.TestCase):
    def test_route_files_match_the_list(self):
        self.assertEqual(sorted(path.stem for path in ROUTES), sorted(LISTED))

    def test_runner_accepts_each_route(self):
        for path in ROUTES:
            with self.subTest(route=path.name):
                name, _ = run_route.load_route(path)
                self.assertEqual(name.replace("-", "_"), path.stem)

    def test_names_are_unique(self):
        names = [json.loads(path.read_text())["name"] for path in ROUTES]
        self.assertEqual(sorted(set(names)), sorted(names))

    def test_shots_end_before_the_next_button_change(self):
        for path in ROUTES:
            steps = json.loads(path.read_text())["steps"]
            starts = [0]
            for step in steps:
                starts.append(starts[-1] + step["frames"])
            for i, step in enumerate(steps):
                if "shot" not in step:
                    continue
                change = next((starts[j] for j in range(i + 1, len(steps))
                               if steps[j]["buttons"] != step["buttons"]), None)
                if change is None:
                    continue
                with self.subTest(route=path.name, step=i, shot=step["shot"]):
                    self.assertGreaterEqual(change - starts[i + 1], SHOT_MARGIN)


if __name__ == "__main__":
    unittest.main()
