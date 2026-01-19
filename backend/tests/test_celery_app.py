from app.core.celery_app import celery_app


def test_celery_app_configuration():
    assert celery_app.main == "novellaforge"
    assert celery_app.conf.task_serializer == "json"
    assert "json" in celery_app.conf.accept_content
    assert celery_app.conf.timezone == "UTC"


def test_tasks_module_exports_celery_app():
    from app import tasks

    assert tasks.celery_app is celery_app
