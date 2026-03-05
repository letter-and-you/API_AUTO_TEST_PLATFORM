

from celery import shared_task
from django.conf import settings
from .runner import TestRunner
from monitor.models import MonitorRule 
from testcases.models import TestCase, TestSuite
from monitor.tasks import  execute_monitor_task, check_monitor_alarm

@shared_task(bind=True, retry_backoff=3, retry_kwargs={'max_retries': 2})
def run_test_case(self, test_case_id, user_id=None,sync=False):
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
                created_by_id=user_id,
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
    """执行定时任务(由Celery Beat调用)""" 
    # 获取所有已启用的、定时类型的监控规则
    scheduled_rules = MonitorRule.objects.filter(
        is_active=True,
        # 假设通过 interval 或其他字段区分定时任务，根据实际业务调整
        # 例如：仅执行间隔>0的规则（表示需要定时执行）
        monitor_type='scheduled',
        interval__gt=0
    )
    for rule in scheduled_rules:
        # 调用监控任务，传递规则ID（与 execute_monitor_task 定义匹配）
        execute_monitor_task.delay(rule_id=rule.id)

