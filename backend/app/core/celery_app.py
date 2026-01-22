"""Celery application configuration"""
from celery import Celery
from celery.schedules import crontab
from kombu import Queue
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

# Priority Queue Configuration
# Higher priority queues get processed first
celery_app.conf.task_queues = (
    # High priority: beat generation (time-sensitive, parallel)
    Queue("beats_high", routing_key="beats.#"),
    # Medium priority: chapter generation, plan pregeneration
    Queue("generation_medium", routing_key="generation.#"),
    # Low priority: maintenance tasks (can wait)
    Queue("maintenance_low", routing_key="maintenance.#"),
    # Default queue
    Queue("celery", routing_key="celery"),
)

celery_app.conf.task_default_queue = "celery"
celery_app.conf.task_default_exchange = "tasks"
celery_app.conf.task_default_routing_key = "celery"

# Task routing based on task name
celery_app.conf.task_routes = {
    # Beat generation - high priority
    "generate_beat": {"queue": "beats_high"},
    "assemble_beats": {"queue": "beats_high"},
    # Chapter/plan generation - medium priority
    "generate_chapter_async": {"queue": "generation_medium"},
    "pregenerate_plans_async": {"queue": "generation_medium"},
    # Maintenance tasks - low priority
    "reconcile_all_active_projects": {"queue": "maintenance_low"},
    "reconcile_project_memory": {"queue": "maintenance_low"},
    "rebuild_all_project_rags": {"queue": "maintenance_low"},
    "rebuild_project_rag": {"queue": "maintenance_low"},
    "cleanup_old_drafts": {"queue": "maintenance_low"},
}

# Priority settings
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5

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


# Worker command examples for different queues:
# High priority beats (4 concurrent):
#   celery -A app.core.celery_app worker -Q beats_high --concurrency=4 -n beats@%h
#
# Medium priority generation (2 concurrent):
#   celery -A app.core.celery_app worker -Q generation_medium --concurrency=2 -n gen@%h
#
# Low priority maintenance (1 worker):
#   celery -A app.core.celery_app worker -Q maintenance_low --concurrency=1 -n maint@%h
#
# All queues (default):
#   celery -A app.core.celery_app worker -Q beats_high,generation_medium,maintenance_low,celery --concurrency=4
