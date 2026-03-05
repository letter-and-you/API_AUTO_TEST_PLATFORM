'''
Author: letterzhou
Description: -- 
Date: 2025-11-07 13:26:16
LastEditors: letterzhou
LastEditTime: 2025-12-29 19:39:29
'''
#web服务网关的配置文件，用于部署Django应用，django正式启动时会调用这个文件
"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

application = get_wsgi_application()
