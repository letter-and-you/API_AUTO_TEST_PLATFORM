'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 00:09:24
LastEditors: letterzhou
LastEditTime: 2025-11-25 00:09:33
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]