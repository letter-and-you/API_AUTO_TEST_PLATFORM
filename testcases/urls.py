'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 14:43:22
LastEditors: letterzhou
LastEditTime: 2025-11-25 14:43:30
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestCaseViewSet, TestSuiteViewSet

router = DefaultRouter()
router.register(r'cases', TestCaseViewSet, basename='testcase')
router.register(r'suites', TestSuiteViewSet, basename='testsuite')

urlpatterns = [
    path('', include(router.urls)),
]