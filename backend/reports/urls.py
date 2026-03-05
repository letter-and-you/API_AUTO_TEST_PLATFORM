'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 17:21:10
LastEditors: letterzhou
LastEditTime: 2025-11-25 17:21:16
'''
# reports/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'reports', views.TestReportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]