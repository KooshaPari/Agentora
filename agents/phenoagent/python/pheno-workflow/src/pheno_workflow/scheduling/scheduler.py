"""
Workflow scheduler for background jobs.
"""

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4


@dataclass
class ScheduledJob:
    """
    Scheduled job definition.
    """

    id: str
    name: str
    handler: Callable
    schedule: str  # cron or interval
    next_run: datetime
    last_run: datetime | None = None
    enabled: bool = True


class WorkflowScheduler:
    """Simple workflow scheduler.

    Features:
    - Interval-based scheduling
    - Cron-like scheduling (basic)
    - Async job execution
    - Job management

    Example:
        scheduler = WorkflowScheduler()

        # Schedule every 5 minutes
        scheduler.schedule_interval(
            "cleanup",
            cleanup_handler,
            minutes=5
        )

        # Start scheduler
        await scheduler.start()
    """

    def __init__(self):
        self._jobs: dict[str, ScheduledJob] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    def schedule_interval(
        self,
        name: str,
        handler: Callable,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
    ) -> str:
        """Schedule job at fixed interval.

        Args:
            name: Job name
            handler: Async function to execute
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours

        Returns:
            Job ID
        """
        total_seconds = seconds + (minutes * 60) + (hours * 3600)

        job = ScheduledJob(
            id=str(uuid4()),
            name=name,
            handler=handler,
            schedule=f"interval:{total_seconds}",
            next_run=datetime.utcnow() + timedelta(seconds=total_seconds),
        )

        self._jobs[job.id] = job
        return job.id

    def schedule_cron(
        self,
        name: str,
        handler: Callable,
        cron: str,
    ) -> str:
        """Schedule job with cron expression (basic support).

        Args:
            name: Job name
            handler: Async function
            cron: Cron expression (e.g., "0 * * * *" for hourly)

        Returns:
            Job ID
        """
        job = ScheduledJob(
            id=str(uuid4()),
            name=name,
            handler=handler,
            schedule=f"cron:{cron}",
            next_run=self._parse_cron_next(cron),
        )

        self._jobs[job.id] = job
        return job.id

    def _parse_cron_next(self, cron: str) -> datetime:
        """
        Parse cron expression to next run time (simplified).
        """
        # Simplified: just schedule 1 hour from now
        # Full cron parsing would require croniter or similar
        return datetime.utcnow() + timedelta(hours=1)

    async def start(self):
        """
        Start scheduler.
        """
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """
        Stop scheduler.
        """
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run_loop(self):
        """
        Main scheduler loop.
        """
        while self._running:
            try:
                await self._check_and_run_jobs()
                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                print(f"Scheduler error: {e}")

    async def _check_and_run_jobs(self):
        """
        Check and execute due jobs.
        """
        now = datetime.utcnow()

        for job in list(self._jobs.values()):
            if not job.enabled:
                continue

            if job.next_run <= now:
                # Execute job
                await self._execute_job(job)

                # Schedule next run
                if job.schedule.startswith("interval:"):
                    interval = int(job.schedule.split(":")[1])
                    job.next_run = now + timedelta(seconds=interval)
                elif job.schedule.startswith("cron:"):
                    cron = job.schedule.split(":", 1)[1]
                    job.next_run = self._parse_cron_next(cron)

    async def _execute_job(self, job: ScheduledJob):
        """
        Execute a job.
        """
        try:
            job.last_run = datetime.utcnow()

            if asyncio.iscoroutinefunction(job.handler):
                await job.handler()
            else:
                job.handler()
        except Exception as e:
            print(f"Job {job.name} failed: {e}")

    def get_job(self, job_id: str) -> ScheduledJob | None:
        """
        Get job by ID.
        """
        return self._jobs.get(job_id)

    def enable_job(self, job_id: str):
        """
        Enable a job.
        """
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True

    def disable_job(self, job_id: str):
        """
        Disable a job.
        """
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False

    def remove_job(self, job_id: str):
        """
        Remove a job.
        """
        self._jobs.pop(job_id, None)

    def list_jobs(self) -> list:
        """
        List all jobs.
        """
        return list(self._jobs.values())
