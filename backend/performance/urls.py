from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PerformanceTestViewSet

router = DefaultRouter()
router.register(r'', PerformanceTestViewSet, basename='performance-test')

urlpatterns = [
    path('', include(router.urls)),
]