import os
import tempfile
import time
import unittest

from core.orchestrator import run_jobs


def ok_job(args):
    folder, name = args
    with open(os.path.join(folder, name), "w") as f:
        f.write("done")


def crash_once_job(args):
    """Crashes on the first attempt, succeeds on the next one."""
    folder, name = args
    marker = os.path.join(folder, name + ".attempted")
    if not os.path.exists(marker):
        open(marker, "w").close()
        os._exit(1)
    with open(os.path.join(folder, name), "w") as f:
        f.write("done")


def mixed_job(args):
    """Crashes when asked to, otherwise writes its output file."""
    folder, name, mode = args
    if mode == "crash":
        os._exit(1)
    with open(os.path.join(folder, name), "w") as f:
        f.write("done")


def hang_job(args):
    time.sleep(60)


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = self.tmp.name

    def jobs(self, names):
        return [(self.folder, n) for n in names]

    def test_all_jobs_complete(self):
        report = run_jobs(ok_job, self.jobs(["a", "b", "c"]), max_parallel=2)
        self.assertEqual(report.completed, [0, 1, 2])
        self.assertEqual(report.failed, [])
        self.assertEqual(sorted(os.listdir(self.folder)), ["a", "b", "c"])

    def test_crashed_job_is_retried_and_succeeds(self):
        report = run_jobs(crash_once_job, self.jobs(["a"]), max_retries=2)
        self.assertEqual(report.completed, [0])
        self.assertEqual(report.attempts[0], 2)

    def test_job_that_always_fails_is_reported_and_others_finish(self):
        jobs = [
            (self.folder, "a", "ok"),
            (self.folder, "b", "crash"),
            (self.folder, "c", "ok"),
        ]
        report = run_jobs(mixed_job, jobs, max_parallel=3, max_retries=1)
        self.assertEqual(report.completed, [0, 2])
        self.assertEqual(report.failed, [1])
        self.assertEqual(report.attempts[1], 2)
        self.assertEqual(sorted(os.listdir(self.folder)), ["a", "c"])

    def test_hanging_job_is_killed_after_timeout(self):
        start = time.monotonic()
        report = run_jobs(hang_job, [None], max_retries=0, timeout=1.0)
        self.assertEqual(report.failed, [0])
        self.assertLess(time.monotonic() - start, 30)


if __name__ == "__main__":
    unittest.main()
