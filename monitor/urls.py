'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:12:53
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:13:00
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MonitorRuleViewSet, MonitorRecordViewSet, AlarmLogViewSet

router = DefaultRouter()
router.register(r'rules', MonitorRuleViewSet, basename='monitor-rule')
router.register(r'records', MonitorRecordViewSet, basename='monitor-record')
router.register(r'alarm-logs', AlarmLogViewSet, basename='alarm-log')

urlpatterns = [
    path('', include(router.urls)),
]