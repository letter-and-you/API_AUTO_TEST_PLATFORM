'''
Author: letterzhou
Description: -- 接口模块
Date: 2025-11-25 16:28:23
LastEditors: letterzhou
LastEditTime: 2025-12-29 12:55:13
'''
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apis"
