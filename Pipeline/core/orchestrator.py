"""Local reference orchestrator: spawn per job, retry on failure.

Each job attempt runs in its own short-lived process, like a serverless
invocation: started on demand, torn down when it finishes. If an attempt
crashes (non-zero exit) or exceeds the timeout, it is killed and the job is
retried, up to `max_retries` extra attempts. Other jobs keep running.

This is a single-machine reference for the retry/respawn pattern. It does not
talk to any cloud service or scheduler.

Uses only the Python standard library.
"""
import multiprocessing as mp
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Report:
    completed: list = field(default_factory=list)  # job indices that succeeded
    failed: list = field(default_factory=list)  # job indices that ran out of retries
    attempts: dict = field(default_factory=dict)  # job index -> attempts used


def run_jobs(work_fn, jobs, max_parallel=4, max_retries=2, timeout=60.0, poll=0.02):
    """Run `work_fn(job)` for every job, each attempt in a fresh process.

    `work_fn` must be a top-level function so it can be pickled by the
    "spawn" start method (the default on Windows).
    """
    ctx = mp.get_context("spawn")
    pending = deque(range(len(jobs)))
    running = {}  # job index -> (process, start time)
    report = Report()

    while pending or running:
        while pending and len(running) < max_parallel:
            idx = pending.popleft()
            report.attempts[idx] = report.attempts.get(idx, 0) + 1
            proc = ctx.Process(target=work_fn, args=(jobs[idx],))
            proc.start()
            running[idx] = (proc, time.monotonic())

        time.sleep(poll)

        for idx, (proc, started) in list(running.items()):
            timed_out = proc.is_alive() and time.monotonic() - started > timeout
            if timed_out:
                proc.terminate()
            if timed_out or not proc.is_alive():
                proc.join()
                del running[idx]
                if not timed_out and proc.exitcode == 0:
                    report.completed.append(idx)
                elif report.attempts[idx] <= max_retries:
                    pending.append(idx)
                else:
                    report.failed.append(idx)

    report.completed.sort()
    report.failed.sort()
    return report
