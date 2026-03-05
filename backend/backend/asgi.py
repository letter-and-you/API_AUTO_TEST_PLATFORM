'''
Author: letterzhou
Description: -- 
Date: 2025-11-07 13:26:16
LastEditors: letterzhou
LastEditTime: 2025-12-29 19:49:17
'''
"""
ASGI config for API_django_tp project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_asgi_application()
