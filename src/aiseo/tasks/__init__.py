"""Celery app and async task definitions."""

from celery import Celery

from aiseo.config import get_settings

settings = get_settings()

celery_app = Celery("aiseo")
celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
