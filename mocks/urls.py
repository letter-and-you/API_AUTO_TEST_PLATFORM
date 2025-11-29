'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:07:32
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:07:38
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MockServiceViewSet, MockResponseViewSet

router = DefaultRouter()
router.register(r'services', MockServiceViewSet, basename='mock-service')
router.register(r'responses', MockResponseViewSet, basename='mock-response')

urlpatterns = [
    path('', include(router.urls)),
]