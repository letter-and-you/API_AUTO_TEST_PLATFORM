# Create your tests here.

from django.test import TestCase
from unittest.mock import patch, Mock
from django.conf import settings
from .runner import TestRunner
from testcases.models import TestCase
import json
import time

class TestRunnerTestCase(TestCase):
    def setUp(self):
        """初始化测试环境"""
        self.runner = TestRunner()
        # 创建测试用例模拟数据
        self.test_case = Mock(spec=TestCase)
        self.test_case.method = 'GET'
        self.test_case.url = 'http://example.com/api'
        self.test_case.headers = {'Content-Type': 'application/json'}
        self.test_case.params = {'id': '{{param}}'}
        self.test_case.body = '{"name": "{{name}}"}'
        self.test_case.body_type = 'json'
        self.test_case.is_parameterized = True
        self.test_case.parameters = {'param': 123, 'name': 'test'}
        self.test_case.extract_rules = {}
        self.test_case.expected_status = 200
        self.test_case.expected_response = ''

    def test_parameter_replacement(self):
        """测试参数替换逻辑"""
        request_data = self.runner._prepare_request(self.test_case)
        
        # 验证URL参数替换
        self.assertEqual(request_data['params']['id'], '123')
        # 验证请求体参数替换
        self.assertEqual(request_data['data']['name'], 'test')

    @patch('requests.Session.request')
    def test_request_sending(self, mock_request):
        """测试请求发送逻辑"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.cookies = {}
        mock_request.return_value = mock_response

        response_info = self.runner._send_request(self.test_case)
        
        self.assertTrue(response_info['success'])
        self.assertEqual(response_info['status_code'], 200)
        self.assertGreater(response_info['duration'], 0)

    @patch('requests.Session.request')
    def test_request_timeout(self, mock_request):
        """测试请求超时重试逻辑"""
        # 模拟请求超时
        mock_request.side_effect = Exception("Connection timeout")

        response_info = self.runner._send_request(self.test_case)
        
        self.assertFalse(response_info['success'])
        self.assertIn("timeout", response_info['error'].lower())

    def test_content_type_mapping(self):
        """测试Content-Type映射"""
        self.assertEqual(self.runner._get_content_type('json'), 'application/json')
        self.assertEqual(self.runner._get_content_type('form'), 'application/x-www-form-urlencoded')
        self.assertEqual(self.runner._get_content_type('xml'), 'text/xml')
        self.assertEqual(self.runner._get_content_type('text'), 'text/plain')
        self.assertEqual(self.runner._get_content_type('unknown'), 'application/json')

    def test_body_preparation(self):
        """测试请求体处理逻辑"""
        # 测试JSON类型
        json_body = '{"key": "value"}'
        prepared = self.runner._prepare_body(json_body, 'json')
        self.assertEqual(prepared, {'key': 'value'})

        # 测试表单类型
        form_body = 'name=test&age=18'
        prepared = self.runner._prepare_body(form_body, 'form')
        self.assertEqual(prepared, {'name': 'test', 'age': '18'})

        # 测试文本类型
        text_body = 'plain text'
        prepared = self.runner._prepare_body(text_body, 'text')
        self.assertEqual(prepared, text_body)