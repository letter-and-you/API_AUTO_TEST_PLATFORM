'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:15:36
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:15:42
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import APIInterfaceViewSet

router = DefaultRouter()
router.register(r'', APIInterfaceViewSet, basename='api-interface')

urlpatterns = [
    path('', include(router.urls)),
]