'''
Author: letterzhou
Description: -- 
Date: 2025-11-07 13:26:16
LastEditors: letterzhou
LastEditTime: 2025-12-29 17:29:00
'''
"""
URL configuration for API_django_tp project.
#主路由配置文件, http请求进入Django后首先经过这里, 然后根据不同的路由分发到不同的应用中
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions



# API文档配置
schema_view = get_schema_view(
    openapi.Info(
        title="智能API测试与监控平台API",
        default_version='v1',
        description="API测试与监控平台的后端接口文档支持前端Vue3项目调用",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@api-test.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),  # 开发环境允许匿名访问文档
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # API文档（Swagger）
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # JWT认证接口
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # 获取令牌
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 刷新令牌
    
    # 模块路由
    path('api/users/', include('accounts.urls')),          # 用户模块
    path('api/projects/', include('projects.urls')),    # 项目模块
    path('api/testcases/', include('testcases.urls')),  # 测试用例模块
    path('api/executors/', include('executors.urls')),    # 执行引擎模块
    path('api/reports/', include('reports.urls')),      # 报告模块
    path('api/monitor/', include('monitor.urls')),      # 监控模块
    path('api/apis/', include('apis.urls')),        # API接口模块
    path('api/machines/', include('machines.urls')),# 测试机器模块
    path('api/mocks/', include('mocks.urls')),      # Mock服务模块
    path('api/performance/', include('performance.urls')), # 性能测试模块
]

# 开发环境下提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)