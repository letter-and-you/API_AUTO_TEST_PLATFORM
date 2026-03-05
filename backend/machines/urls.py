'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:11:17
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:15:23
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestMachineViewSet, MachineMonitorDataViewSet

router = DefaultRouter()
router.register(r'', TestMachineViewSet, basename='test-machine')
router.register(r'monitor-data', MachineMonitorDataViewSet, basename='machine-monitor')

urlpatterns = [
    path('', include(router.urls)),
]