"""Celery application configuration"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "novellaforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "weekly-memory-reconciliation": {
        "task": "reconcile_all_active_projects",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),
    },
    "monthly-rag-rebuild": {
        "task": "rebuild_all_project_rags",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),
    },
}
