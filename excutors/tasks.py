

from celery import shared_task
from django.conf import settings
from .runner import TestRunner
from testcases.models import TestCase, TestSuite
from monitor.tasks import check_monitor_alarm

@shared_task(bind=True, retry_backoff=3, retry_kwargs={'max_retries': 2})
def run_test_case(self, test_case_id, sync=False):
    """
    执行单个测试用例的Celery任务
    :param self: 任务实例（用于重试）
    :param test_case_id: 测试用例ID
    :param sync: 是否同步返回结果（True为同步，False为异步）
    :return: 同步时返回结果字典，异步时返回结果ID
    """    
    try:
        test_case = TestCase.objects.get(id=test_case_id, is_active=True)
        runner = TestRunner()

        if sync:
            # 同步执行，直接返回结果
            return runner.run_single_case_sync(test_case_id)
        else:
            # 异步执行，生成报告和结果
            from reports.models import TestReport
            # 创建临时报告（单个用例执行）
            report = TestReport.objects.create(
                project=test_case.project,
                test_case=test_case,
                created_by_id=self.request.id if hasattr(self.request, 'id') else None,
                total_cases=1,
                status='running'         )
            # 执行用例
            result = runner.run_single_case(test_case, report=report)
            # 更新报告状态
            report.passed_cases = 1 if result.success else 0
            report.failed_cases = 0 if result.success else 1
            report.success_rate = 100 if result.success else 0
            report.status = 'completed' if result.success else 'partially_completed'           
            report.save()
            # 检查是否需要触发告警
            check_monitor_alarm.delay(test_case_id=test_case.id, result_id=result.id)
            return {"report_id": report.id, "result_id": result.id}
    except TestCase.DoesNotExist:
        if sync:
            return {"error": "测试用例不存在或已删除"}
        else:
            self.update_state(state='FAILURE', meta={"error": "测试用例不存在或已删除"})
            raise
    except Exception as e:
        # 任务重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        if sync:
            return {"error": f"用例执行失败：{str(e)}"}
        else:
            self.update_state(state='FAILURE', meta={"error": f"用例执行失败：{str(e)}"})
            raise

@shared_task(bind=True, retry_backoff=5, retry_kwargs={'max_retries': 1})
def run_test_suite(self, test_suite_id, created_by_id):
    """
    执行测试套件的Celery任务
    :param self: 任务实例
    :param test_suite_id: 测试套件ID
    :param created_by_id: 执行发起者ID
    :return: 测试报告ID
    """    
    try:
        test_suite = TestSuite.objects.get(id=test_suite_id)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        created_by = User.objects.get(id=created_by_id)

        runner = TestRunner()
        # 执行套件
        report = runner.run_suite(test_suite, created_by)
        # 检查套件内用例是否需要触发告警
        for result in report.test_results.all():
            check_monitor_alarm.delay(test_case_id=result.test_case.id, result_id=result.id)
        return {"report_id": report.id}
    except (TestSuite.DoesNotExist, User.DoesNotExist) as e:
        self.update_state(state='FAILURE', meta={"error": str(e)})
        raise
    except Exception as e:
        # 仅重试一次
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        # 更新报告状态为失败
        from reports.models import TestReport
        try:
            report = TestReport.objects.get(
                test_suite_id=test_suite_id,
                created_by_id=created_by_id,
                status='running'        )
            report.status = 'failed'    
            report.error_message = str(e)
            report.save()
        except TestReport.DoesNotExist:
            pass
        self.update_state(state='FAILURE', meta={"error": f"套件执行失败：{str(e)}"})
        raise

@shared_task
def run_scheduled_tasks():
    """
    执行定时任务(由Celery Beat调用)
    触发所有已启用的定时监控任务
    """    
    from monitor.models import MonitorTask
    # 获取所有已启用的定时任务
    scheduled_tasks = MonitorTask.objects.filter(
        is_active=True,
        monitor_type='scheduled' )
    for task in scheduled_tasks:
        # 执行监控任务
        run_monitor_task.delay(monitor_task_id=task.id)

@shared_task
def run_monitor_task(monitor_task_id):
    """
    执行监控任务
    :param monitor_task_id: 监控任务ID
    """    
    try:
        from monitor.models import MonitorTask
        monitor_task = MonitorTask.objects.get(id=monitor_task_id, is_active=True)
        runner = TestRunner()

        # 根据监控类型执行对应逻辑
        if monitor_task.monitor_type == 'scheduled':          # 定时监控：执行关联的用例或套件
            if monitor_task.test_case:
                # 执行单个用例
                result = runner.run_single_case(monitor_task.test_case)
                check_monitor_alarm.delay(
                    test_case_id=monitor_task.test_case.id,
                    result_id=result.id,
                    monitor_task_id=monitor_task.id
                )
            elif monitor_task.test_suite:
                # 执行套件
                report = runner.run_suite(
                    monitor_task.test_suite,
                    monitor_task.created_by
                )
                for result in report.test_results.all():
                    check_monitor_alarm.delay(
                        test_case_id=result.test_case.id,
                        result_id=result.id,
                        monitor_task_id=monitor_task.id
                    )
        elif monitor_task.monitor_type == 'api':            # API监控：直接执行HTTP请求（用于简单接口监控）
            from testcases.models import TestCase
            # 临时创建测试用例执行
            temp_case = TestCase(
                name=f"临时监控用例_{monitor_task.id}",
                project=monitor_task.project,
                method=monitor_task.request_method,
                url=monitor_task.request_url,
                headers=monitor_task.request_headers,
                body=monitor_task.request_body,
                body_type=monitor_task.request_body_type,
                expected_status=monitor_task.expected_status,
                created_by=monitor_task.created_by,
                status='active'           )
            # 执行临时用例
            result = runner.run_single_case_sync(temp_case.id)
            # 检查告警
            check_monitor_alarm.delay(
                test_case_id=temp_case.id,
                result_data=result,
                monitor_task_id=monitor_task.id
            )
    except MonitorTask.DoesNotExist:
        pass
    except Exception as e:
        # 记录监控任务错误
        from monitor.models import MonitorLog
        MonitorLog.objects.create(
            monitor_task_id=monitor_task_id,
            status='failed',
            message=f"监控任务执行失败：{str(e)}"
        )