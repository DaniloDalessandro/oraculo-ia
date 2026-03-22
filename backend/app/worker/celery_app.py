"""
Configuração central do Celery.
Importado pelos workers e pela API para enfileirar tarefas.
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "oraculo",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.worker.tasks.message_tasks",
        "app.worker.tasks.session_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_default_queue="fila_mensagens",
    task_queues={
        "fila_mensagens": {"exchange": "fila_mensagens", "routing_key": "mensagens"},
        "fila_ia":        {"exchange": "fila_ia",        "routing_key": "ia"},
    },
    task_routes={
        "app.worker.tasks.message_tasks.*": {"queue": "fila_ia"},
    },
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    beat_schedule={
        "expire-whatsapp-sessions": {
            "task": "app.worker.tasks.session_tasks.expire_sessions_task",
            "schedule": 3600,
        },
    },
)
