
# Create your views here.
# reports/views.py
import os
import json
from django.db import models
from .models import TestReport, TestResult
from datetime import datetime
from django.db import transaction
from django.http import HttpResponse, FileResponse
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.conf import settings
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TestReport, TestResult
from .serializers import TestReportListSerializer, TestReportDetailSerializer, TestResultSerializer
from .permissions import IsReportOwnerOrProjectMember

class TestReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    测试报告视图集

    list:
    获取报告列表

    retrieve:
    获取报告详情

    export:
    导出HTML格式报告
    """
    queryset = TestReport.objects.all().select_related('project', 'created_by', 'test_suite', 'test_case')
    permission_classes = [IsAuthenticated, IsReportOwnerOrProjectMember]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'project__name']
    ordering_fields = ['created_at', 'total_duration', 'success_rate']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return TestReportListSerializer
        return TestReportDetailSerializer

    def get_queryset(self):
        """
        重写查询集，用户只能看到自己创建的或所在项目的报告。
        """
        user = self.request.user
        # 获取用户参与的所有项目ID
        user_project_ids = user.project_members.filter(
            is_active=True
        ).values_list('project_id', flat=True)
        
        return TestReport.objects.filter(
            models.Q(created_by=user) | models.Q(project_id__in=user_project_ids)
        ).select_related('project', 'created_by', 'test_suite', 'test_case')

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        导出HTML格式的测试报告。
        如果已生成，则直接下载；否则，动态生成。
        """
        report = self.get_object()

        # 检查是否已存在HTML报告文件
        if report.html_report_file and os.path.exists(report.html_report_file.path):
            try:
                return FileResponse(
                    open(report.html_report_file.path, 'rb'),
                    as_attachment=True,
                    filename=f"{slugify(report.name)}_{report.created_at.strftime('%Y%m%d_%H%M%S')}.html"
                )
            except Exception as e:
                # 如果文件存在但读取失败，删除旧文件并继续重新生成
                report.html_report_file.delete(save=False)

        # 动态生成HTML报告
        # 预加载所有关联的测试结果，避免N+1查询问题
        test_results = TestResult.objects.filter(test_report=report).select_related('test_case')

        # 准备模板数据
        context = {
            'report': report,
            'test_results': test_results,
            'generated_at': datetime.now(),
            'settings': settings, # 可在模板中使用一些项目配置，如LOGO_URL等
        }

        # 渲染HTML
        html_content = render_to_string('reports/report_template.html', context)

        # 保存HTML文件到服务器（可选，但推荐，避免重复生成）
        if not os.path.exists(os.path.dirname(settings.MEDIA_ROOT + '/reports/html/')):
            os.makedirs(os.path.dirname(settings.MEDIA_ROOT + '/reports/html/'), exist_ok=True)
        
        filename = f"report_{report.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.html"
        file_path = os.path.join(settings.MEDIA_ROOT, 'reports/html/', filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 更新报告记录
        report.html_report_file = f'reports/html/{filename}'
        report.save(update_fields=['html_report_file'])

        # 返回文件响应
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{slugify(report.name)}.html"'
        return response