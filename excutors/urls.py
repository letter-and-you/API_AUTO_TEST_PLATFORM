'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:02:03
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:02:12
'''


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExecutionResultViewSet
from testcases.views import TestCaseViewSet, TestSuiteViewSet

router = DefaultRouter()
# 注册执行结果视图集
router.register(r'execution-results', ExecutionResultViewSet, basename='execution-result')
# 注册测试用例和套件视图集（方便统一管理执行相关接口）
router.register(r'test-cases', TestCaseViewSet, basename='test-case')
router.register(r'test-suites', TestSuiteViewSet, basename='test-suite')

urlpatterns = [
    path('', include(router.urls)),
]