from django.utils import timezone
import time
import requests
import json
from requests.exceptions import RequestException
from django.conf import settings
from testcases.utils import validate_response, extract_response_data, replace_parameters
from testcases.models import TestCase
from reports.models import TestReport, TestResult

class TestRunner:
    """测试执行器核心类
    负责发送HTTP请求、处理响应、验证结果并生成报告
    """    
    def __init__(self):
        # 初始化请求会话，保持连接复用
        self.session = requests.Session()
        # 设置默认超时时间
        self.timeout = settings.TEST_REQUEST_TIMEOUT if hasattr(settings, 'TEST_REQUEST_TIMEOUT') else 30
        # 存储用例间传递的参数
        self.shared_params = {}

    def _prepare_request(self, test_case):
        """准备请求参数（处理参数化、替换占位符）"""        # 合并全局参数和用例自身参数
        parameters = {**self.shared_params, **test_case.parameters} if test_case.is_parameterized else self.shared_params

        # 处理请求URL（替换参数占位符）
        url = replace_parameters(test_case.url, parameters)

        # 处理请求头
        headers = replace_parameters(test_case.headers, parameters)
        # 添加默认请求头
        default_headers = {'Content-Type': self._get_content_type(test_case.body_type)}
        headers.update(default_headers)

        # 处理请求参数（GET/DELETE等）
        params = replace_parameters(test_case.params, parameters)

        # 处理请求体
        body = replace_parameters(test_case.body, parameters)
        data = self._prepare_body(body, test_case.body_type)

        return {'url': url, 'headers': headers, 'params': params, 'data': data}

    def _get_content_type(self, body_type):
        """根据请求体类型返回对应的Content-Type"""        
        content_types = {
            'form': 'application/x-www-form-urlencoded',
            'json': 'application/json',
            'xml': 'text/xml',
            'text': 'text/plain'
        }
        return content_types.get(body_type, 'application/json')

    def _prepare_body(self, body, body_type):
        """根据请求体类型处理请求体数据"""        
        if not body:
            return None

        try:
            if body_type == 'json':
                return json.loads(body)
            elif body_type == 'form':
                # 解析表单数据（key1=value1&key2=value2）
                return dict(item.split('=') for item in body.split('&') if '=' in item)
            else:
                # xml/text直接返回字符串
                return body
        except Exception as e:
            # 处理数据解析错误
            return body

    def _send_request(self, test_case, retries=3):
        """发送HTTP请求并返回响应信息（支持重试）"""        
        request_data = self._prepare_request(test_case)
        method = test_case.method.upper()
        response_info = {
            'success': False,
            'status_code': 0,
            'response_content': '',
            'headers': {},
            'cookies': {},
            'error': '',
            'duration': 0
        }

        for attempt in range(retries):
            try:
                # 记录请求开始时间
                start_time = time.time()
                # 发送请求
                response = self.session.request(
                    method=method,
                    url=request_data['url'],
                    headers=request_data['headers'],
                    params=request_data['params'],
                    data=request_data['data'],
                    timeout=self.timeout,
                    verify=False  # 生产环境建议改为True并配置CA证书
                )
                # 计算请求耗时
                response_info['duration'] = round(time.time() - start_time, 3)

                # 提取响应信息
                response_info['success'] = True
                response_info['status_code'] = response.status_code
                response_info['response_content'] = response.text
                response_info['headers'] = dict(response.headers)
                response_info['cookies'] = dict(response.cookies)
                return response_info  # 成功则返回

            except RequestException as e:
                # 网络异常可重试（最后一次不重试）
                if attempt < retries - 1:
                    time.sleep(2 **attempt)  # 指数退避
                    continue
                response_info['error'] = f"请求失败（重试{retries}次后）：{str(e)}"
            except Exception as e:
                # 其他错误（如参数错误）不重试
                response_info['error'] = f"执行错误：{str(e)}"
                break

        return response_info

    def run_single_case(self, test_case, report=None):
        """执行单个测试用例并生成结果
        :param test_case: TestCase实例
        :param report: 关联的TestReport实例（可选）
        :return: TestResult实例
        """        # 执行请求
        response_info = self._send_request(test_case)

        # 验证响应结果
        pass_flag, errors = validate_response(
            test_case=test_case,
            actual_response=response_info['response_content'],
            actual_status_code=response_info['status_code']
        )

        # 提取响应数据（供后续用例使用）
        if test_case.extract_rules:
            extracted_data = extract_response_data(
                response_content=response_info['response_content'],
                extract_rules=test_case.extract_rules
            )
            self.shared_params.update(extracted_data)
        else:
            extracted_data = {}

        # 创建测试结果
        test_result = TestResult.objects.create(
            test_case=test_case,
            test_report=report,
            project=test_case.project,
            method=test_case.method,
            url=response_info.get('url', test_case.url),
            request_headers=test_case.headers,
            request_body=test_case.body,
            response_status=response_info['status_code'],
            response_content=response_info['response_content'],
            response_headers=response_info['headers'],
            duration=response_info['duration'],
            success=pass_flag,
            errors=errors,
            extracted_data=extracted_data,
            error_message=response_info['error'],
            status='passed' if pass_flag else 'failed' if response_info['success'] else 'error'
        )

        return test_result

    def run_suite(self, test_suite, created_by):
        """执行测试套件并生成报告
        :param test_suite: TestSuite实例
        :param created_by: 执行发起者（User实例）
        :return: TestReport实例
        """        # 获取套件内所有已启用的用例
        test_cases = test_suite.test_cases.filter(status='active', is_active=True).order_by('id')
        if not test_cases:
            raise ValueError("测试套件中无可用的测试用例")

        # 创建测试报告
        test_report = TestReport.objects.create(
            project=test_suite.project,
            test_suite=test_suite,
            created_by=created_by,
            total_cases=len(test_cases),
            status='running',
            start_at=timezone.now(),
        )

        try:
            # 重置共享参数
            self.shared_params = {}
            passed_count = 0
            failed_count = 0
            skipped_count = 0
            total_duration = 0
            total_response_time = 0
            results = []

            # 批量执行用例
            for case in test_cases:
                result = self.run_single_case(case, report=test_report)
                results.append(result)
                total_duration += result.duration
                total_response_time += result.duration * 1000  # 转换为毫秒
                
                if result.status == 'passed':
                    passed_count += 1
                elif result.status == 'failed':
                    failed_count += 1
                else:
                    skipped_count += 1

            # 更新报告统计信息
            success_rate = round((passed_count / len(test_cases)) * 100, 2) if len(test_cases) > 0 else 0
            avg_response_time = round(total_response_time / len(test_cases), 2) if len(test_cases) > 0 else 0
            
            test_report.passed_cases = passed_count
            test_report.failed_cases = failed_count
            test_report.skipped_cases = skipped_count
            test_report.success_rate = success_rate
            test_report.total_duration = round(total_duration, 3)
            test_report.average_response_time = avg_response_time
            test_report.status = 'completed'
            test_report.completed_at = timezone.now()
        
        except Exception as e:
            # 处理套件执行异常
            test_report.status = 'failed'            
            test_report.error_message = str(e)
            test_report.completed_at = timezone.now()
        finally:
            test_report.save()

            return test_report

    def run_single_case_sync(self, test_case_id):
        """同步执行单个用例并返回结果数据（用于即时查询）"""        
        try:
            test_case = TestCase.objects.get(id=test_case_id, is_active=True, status='active')        
        except TestCase.DoesNotExist:
            return {"error": "测试用例不存在或已禁用"}

        # 执行用例
        response_info = self._send_request(test_case)
        pass_flag, errors = validate_response(
            test_case=test_case,
            actual_response=response_info['response_content'],
            actual_status_code=response_info['status_code']
        )

        # 提取响应数据
        if test_case.extract_rules:
            try:
                extracted_data = extract_response_data(
                    response_content=response_info['response_content'],
                    extract_rules=test_case.extract_rules
                )
            except Exception as e:
                # 记录提取错误，但不中断执行
                extracted_data = {"error": f"数据提取失败: {str(e)}"}
                logger.warning(f"用例 {test_case.id} 提取响应数据失败: {str(e)}")
        else:
            extracted_data = {}

        return {
            "test_case_id": test_case.id,
            "test_case_name": test_case.name,
            "method": test_case.method,
            "url": test_case.url,
            "status_code": response_info['status_code'],
            "success": pass_flag,
            "errors": errors,
            "duration": response_info['duration'],
            "response_content": response_info['response_content'],
            "extracted_data": extracted_data,
            "error_message": response_info['error']
        }
    
