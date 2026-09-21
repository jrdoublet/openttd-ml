from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from c65_pass3 import EXPECTED_TASKS, extract_main_task_queue, task_to_method

MAIN = ROOT / "ai" / "OpexAI" / "main.nut"
SCHEDULER = ROOT / "ai" / "OpexAI" / "scheduler.nut"
TASKS = ROOT / "ai" / "OpexAI" / "scheduler_tasks.nut"


class TestSchedulerTaskContract(unittest.TestCase):
    def test_queue_dispatch_and_handlers_are_exactly_aligned(self):
        main = MAIN.read_text(encoding="utf-8")
        scheduler = SCHEDULER.read_text(encoding="utf-8")
        tasks = TASKS.read_text(encoding="utf-8")
        queue = extract_main_task_queue(main)
        self.assertEqual(queue, EXPECTED_TASKS)
        for name in queue:
            method = task_to_method(name)
            if name in ("c41_road", "c41_water"):
                self.assertIn(
                    f'{{ name = "{name}", dueCycle = 2147483647, enabled = false }}',
                    main,
                )
                if name == "c41_water":
                    self.assertIn('if (task.name == "c41_water") return false;', scheduler)
                else:
                    self.assertNotIn(f'task.name == "{name}"', scheduler)
                self.assertNotIn(f"function OpexAI::{method}(", tasks)
                self.assertNotIn(f'if (task.name == "{name}")', main)
                self.assertNotIn(
                    f'if (task.name == "{name}")',
                    (ROOT / "ai" / "OpexAI" / "events.nut").read_text(encoding="utf-8"),
                )
                continue
            self.assertIn(f'task.name == "{name}"', scheduler)
            self.assertIn(f"function OpexAI::{method}(", tasks)

    def test_unknown_task_is_loud_before_it_is_disabled(self):
        scheduler = SCHEDULER.read_text(encoding="utf-8")
        log = scheduler.index('AILog.Error("Unknown scheduler task name: " + task.name);')
        disable = scheduler.index("task.enabled = false;", log)
        ret = scheduler.index("return false;", disable)
        self.assertLess(log, disable)
        self.assertLess(disable, ret)

    def test_contract_would_reject_a_queue_only_typo(self):
        broken = list(EXPECTED_TASKS)
        broken[-1] = "repya"
        self.assertNotEqual(tuple(broken), EXPECTED_TASKS)


if __name__ == "__main__":
    unittest.main()
