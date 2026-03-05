'''
Author: letterzhou
Description: -- 性能测试任务评分任务
Date: 2025-12-04 19:59:04
LastEditors: letterzhou
LastEditTime: 2025-12-29 18:51:51
'''
from celery import shared_task
from .models import PerformanceTest

@shared_task
def calculate_performance_score(performance_id):
    try:
        performance = PerformanceTest.objects.get(id=performance_id)
        # 假设有评分逻辑
        score = performance.value * 2  # 示例逻辑
        performance.score = score
        performance.save()
        return score
    except PerformanceTest.DoesNotExist:
        return None

@shared_task
def update_all_performance_scores():
    performances = PerformanceTest.objects.all()
    for performance in performances:
        calculate_performance_score.delay(performance.id)
    return "All performance scores update tasks dispatched."

@shared_task(bind=True, max_retries=2)
def run_performance_test(self, performance_test_id):
    """执行性能测试任务"""
    try:
        test = PerformanceTest.objects.get(id=performance_test_id)
        test.status = 'running'
        test.started_at = timezone.now()
        test.save()
        
        # 实际性能测试执行逻辑（示例）
        from executors.runner import TestRunner
        runner = TestRunner()
        
        # 根据测试类型执行
        if test.test_type == 'case' and test.test_case:
            # 执行单接口性能测试
            result = runner.run_performance_test_case(test.test_case, test)
        elif test.test_type == 'suite' and test.test_suite:
            # 执行套件性能测试
            result = runner.run_performance_test_suite(test.test_suite, test)
        else:
            raise ValueError("未设置有效的测试目标")
            
        test.status = 'completed'
        test.completed_at = timezone.now()
        test.save()
        return {"status": "completed", "report_id": test.report.id if test.report else None}
        
    except Exception as e:
        test.status = 'failed'
        test.save()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5)
        return {"status": "failed", "error": str(e)}