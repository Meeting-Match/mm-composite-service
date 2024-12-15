"""
ASGI config for mm_composite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
import logging

logger = logging.getLogger('composite')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mm_composite.settings')

logger.info('Starting ASGI application for mm_composite project')
application = get_asgi_application()
logger.info('ASGI application started successfully')
