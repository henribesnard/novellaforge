"""
Celery tasks module
"""
from app.core.celery_app import celery_app

# Import all task modules here
# Example:
# from app.tasks import document_processing, embeddings

__all__ = ["celery_app"]
