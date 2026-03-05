# Create your models here.

from django.db import models
from django.conf import settings
from projects.models import Project

class TestCase(models.Model):
    """
    API测试用例模型
    存储API测试的核心信息: 请求配置、断言配置等
    """
    # HTTP请求方法选择
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]
    
    # 用例状态
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '已启用'),
        ('disabled', '已禁用'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='所属项目'
    )
    name = models.CharField(max_length=200, verbose_name='用例名称')
    description = models.TextField(blank=True, null=True, verbose_name='用例描述')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET', verbose_name='请求方法')
    url = models.URLField(verbose_name='请求URL')
    headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')  # 存储JSON格式的请求头
    params = models.JSONField(default=dict, blank=True, verbose_name='URL参数')  # GET请求参数
    body = models.TextField(blank=True, null=True, verbose_name='请求体')  # POST/PUT等请求体
    body_type = models.CharField(
        max_length=20,
        choices=[('form', '表单'), ('json', 'JSON'), ('xml', 'XML'), ('text', '文本')],
        default='json',
        verbose_name='请求体类型'
    )
    
    # 断言配置
    expected_status = models.IntegerField(default=200, verbose_name='预期状态码')
    expected_response = models.TextField(blank=True, null=True, verbose_name='预期响应')  # 预期响应内容
    expected_json_schema = models.JSONField(default=dict, blank=True, verbose_name='JSON Schema断言')  # 用于结构校验
    extract_rules = models.JSONField(default=dict, blank=True, verbose_name='响应提取规则')  # 提取响应数据供其他用例使用
    
    # 参数化配置
    is_parameterized = models.BooleanField(default=False, verbose_name='是否参数化')
    parameters = models.JSONField(default=dict, blank=True, verbose_name='参数配置')  # 存储参数化数据
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name='用例状态')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_test_cases',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否有效')  # 软删除标记

    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        db_table = 'test_cases'
        ordering = ['-created_at']
        # 同一项目下用例名称不能重复
        unique_together = ['project', 'name']

    def __str__(self):
        return f"{self.name} ({self.method} {self.url})"

    # 简化请求体展示（用于列表显示）
    @property
    def simple_body(self):
        if not self.body:
            return ""
        # 只显示前50个字符
        return self.body[:50] + "..." if len(self.body) > 50 else self.body

    # 获取用例最近执行结果
    # backend/testcases/models.py (修复last_result属性)
    @property
    def last_result(self):
        """获取用例最近一次的执行结果"""
        from reports.models import TestResult
        last_result = TestResult.objects.filter(test_case=self).order_by('-executed_at').first()
        if not last_result:
            return None
        return {
            'status': last_result.status, 
            'executed_at': last_result.executed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'duration': round(last_result.duration, 2)
        }

# 测试套件模型（用于批量执行用例）
class TestSuite(models.Model):
    """
    测试套件模型
    包含多个测试用例，支持批量执行
    """
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, null=True, verbose_name='套件描述')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_suites',
        verbose_name='所属项目'
    )
    test_cases = models.ManyToManyField(
        TestCase,
        related_name='test_suites',
        verbose_name='包含用例'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_test_suites',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '测试套件'
        verbose_name_plural = '测试套件'
        db_table = 'test_suites'
        unique_together = ['project', 'name']

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    # 获取套件内用例数量
    @property
    def case_count(self):
        return self.test_cases.count()

    # 获取套件最近执行结果
    @property
    def last_execution(self):
        from reports.models import TestReport
        last_report = TestReport.objects.filter(test_suite=self).order_by('-executed_at').first()
        if not last_report:
            return None
        return {
            'success_rate': last_report.success_rate,
            'executed_at': last_report.executed_at.strftime('%Y-%m-%d %H:%M:%S'),
            'total_cases': last_report.total_cases,
            'passed_cases': last_report.passed_cases
        }
        
        


class TestStep(models.Model):
    """测试步骤模型，支持复杂用例流程控制"""
    STEP_TYPE_CHOICES = [
        ('request', 'HTTP请求'),
        ('condition', '条件判断'),
        ('loop', '循环控制'),
        ('sleep', '等待'),
        ('extract', '变量提取'),
        ('assert', '断言'),
    ]
    
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name='所属用例'
    )
    name = models.CharField(max_length=200, verbose_name='步骤名称')
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default='request', verbose_name='步骤类型')
    sort_order = models.IntegerField(default=0, verbose_name='执行顺序')
    
    # HTTP请求相关字段
    method = models.CharField(max_length=10, choices=TestCase.METHOD_CHOICES, blank=True, null=True, verbose_name='请求方法')
    url = models.URLField(blank=True, null=True, verbose_name='请求URL')
    headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')
    params = models.JSONField(default=dict, blank=True, verbose_name='URL参数')
    body = models.TextField(blank=True, null=True, verbose_name='请求体')
    body_type = models.CharField(
        max_length=20,
        choices=[('form', '表单'), ('json', 'JSON'), ('xml', 'XML'), ('text', '文本')],
        default='json',
        blank=True,
        verbose_name='请求体类型'
    )
    
    # 条件控制相关字段
    condition_expression = models.TextField(blank=True, null=True, verbose_name='条件表达式')
    true_step_id = models.IntegerField(blank=True, null=True, verbose_name='条件为真时执行的步骤ID')
    false_step_id = models.IntegerField(blank=True, null=True, verbose_name='条件为假时执行的步骤ID')
    
    # 循环控制相关字段
    loop_count = models.IntegerField(default=1, blank=True, null=True, verbose_name='循环次数')
    loop_variable = models.CharField(max_length=50, blank=True, null=True, verbose_name='循环变量')
    loop_start_step = models.IntegerField(blank=True, null=True, verbose_name='循环开始步骤ID')
    loop_end_step = models.IntegerField(blank=True, null=True, verbose_name='循环结束步骤ID')
    
    # 等待步骤相关字段
    sleep_seconds = models.IntegerField(default=1, blank=True, null=True, verbose_name='等待秒数')
    
    # 提取步骤相关字段
    extract_expression = models.TextField(blank=True, null=True, verbose_name='提取表达式')
    extract_variable = models.CharField(max_length=50, blank=True, null=True, verbose_name='提取变量名')
    
    # 断言步骤相关字段
    assert_type = models.CharField(
        max_length=20,
        choices=[('equals', '等于'), ('contains', '包含'), ('greater', '大于'), ('less', '小于'), ('regex', '正则匹配')],
        blank=True,
        null=True,
        verbose_name='断言类型'
    )
    assert_left = models.TextField(blank=True, null=True, verbose_name='断言左值')
    assert_right = models.TextField(blank=True, null=True, verbose_name='断言右值')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '测试步骤'
        verbose_name_plural = '测试步骤'
        db_table = 'test_steps'
        ordering = ['test_case', 'sort_order']
    
    def __str__(self):
        return f"{self.test_case.name} - {self.name} ({self.get_step_type_display()})"