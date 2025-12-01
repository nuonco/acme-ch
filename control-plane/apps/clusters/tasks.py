from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def debug_task():
    logger.info("Debug task executed")
