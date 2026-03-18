import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doclate_backend.settings")

app = Celery("doclate")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
