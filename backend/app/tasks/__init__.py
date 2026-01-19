"""
Celery tasks module
"""
from app.core.celery_app import celery_app
from app.tasks import coherence_maintenance

__all__ = ["celery_app", "coherence_maintenance"]
