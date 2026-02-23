from celery import Celery

from src.infra.adapters.config import Config


def _create_celery_app(config: Config) -> Celery:
    app = Celery(
        "ab_platform",
        broker=config.rabbitmq_url,
        # Results are not consumed anywhere; disable result backend to avoid
        # coupling the notification pipeline to a specific result store.
        backend=None,
        include=["src.infra.tasks.notifications"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
    )
    return app


celery_app = _create_celery_app(Config.get_config())
