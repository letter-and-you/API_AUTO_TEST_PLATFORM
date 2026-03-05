'''
Author: letterzhou
Description: -- 
Date: 2025-9-25 15:04:22
LastEditors: letterzhou
LastEditTime: 2025-12-29 16:46:19
'''

import logging
import time
from celery import shared_task
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from .models import (MonitorRule, MonitorRecord, AlarmLog, 
                    MonitorAlertRecord, MonitorThresholdBaseline)
from executors.runner import TestRunner
from common.utils import get_users_to_notify

logger = logging.getLogger(__name__)

# 修复：移除重复的装饰器
@shared_task(bind=True, max_retries=3)
def execute_monitor_task(self, rule_id):
    """执行单个监控规则（修复版：解决参数校验、逻辑矛盾等问题）"""
    # 初始化任务执行轨迹记录
    execution_trace = {
        "steps": [],
        "start_time": timezone.now(),
        "end_time": None,
        "status": "running"
    }
    
    def log_step(step_name, status, message=""):
        """记录执行步骤详情"""
        execution_trace["steps"].append({
            "step": step_name,
            "status": status,
            "message": message,
            "timestamp": timezone.now()
        })
        logger.info(f"监控规则 {rule_id} 步骤 [{step_name}]：{status} - {message}")

    # 新增：参数校验（rule_id不能为空）
    if rule_id is None:
        log_step("param_check", "failed", "未传入 rule_id")
        execution_trace["status"] = "failed"
        execution_trace["end_time"] = timezone.now()
        return {"status": "error", "error": "rule_id 不能为空", "trace": execution_trace}

    # 初始化rule变量，避免locals()判断问题
    rule = None
    try:
        # 步骤1：获取并验证监控规则（加锁避免并发问题）
        log_step("load_rule", "started", "开始加载监控规则")
        from django.db import transaction
        with transaction.atomic():
            # 新增：类型转换与校验
            try:
                rule_id_int = int(rule_id)
            except (ValueError, TypeError):
                raise ValueError(f"rule_id 格式错误：{rule_id}（必须为整数）")
            
            # 新增：加行锁防止并发更新冲突
            rule = MonitorRule.objects.select_for_update().get(
                id=rule_id_int, 
                is_active=True
            )
        
        # 初始化规则执行状态
        rule.last_executed_at = timezone.now()
        rule.last_execution_status = 'in_progress'
        rule.execution_error = None
        rule.execution_trace = execution_trace
        rule.save(update_fields=['last_executed_at', 'last_execution_status', 'execution_trace'])
        log_step("load_rule", "completed", f"成功加载规则：{rule.rule_type}")

        # 步骤2：验证关联测试用例
        log_step("validate_test_case", "started", "验证关联测试用例")
        test_case = rule.test_case
        if not test_case:
            log_step("validate_test_case", "failed", "未关联测试用例")
            # 记录错误并更新规则状态
            MonitorRecord.objects.create(
                rule=rule,
                actual_value=0,
                status='critical',
                message="监控规则未关联测试用例",
                execution_trace=execution_trace
            )
            rule.last_execution_status = 'failed'
            rule.execution_error = "未关联测试用例"
            rule.execution_trace["status"] = "failed"
            rule.execution_trace["end_time"] = timezone.now()
            rule.save(update_fields=['last_execution_status', 'execution_error', 'execution_trace'])
            return {"rule_id": rule_id, "status": "error", "trace": execution_trace}
        log_step("validate_test_case", "completed", f"关联用例验证通过：{test_case.id}")

        # 步骤3：执行测试用例（带重试机制）
        log_step("execute_test_case", "started", "开始执行测试用例")
        max_retries = 2
        retry_count = 0
        result = None
        last_exception = None

        while retry_count <= max_retries:
            try:
                runner = TestRunner(test_case.id)
                result = runner.run_single_case_sync(test_case_id)
                if "error" in result:
                    raise Exception(result["error"])
                log_step("execute_test_case", "completed", f"用例执行成功（重试次数：{retry_count}）")
                break
            except Exception as e:
                if isinstance(e, TimeoutError):
                    last_exception = Exception(f"用例执行超时{60}秒")
                else:
                    last_exception = e
                retry_count += 1
                log_step("execute_test_case", "retrying", 
                        f"用例执行失败（{retry_count}/{max_retries}）：{str(last_exception)}")
                if retry_count > max_retries:
                    break  # 退出循环，不再重试
                time.sleep(1)

        # 检查是否成功获取结果
        if result is None and last_exception:
            raise last_exception  # 抛出最后一次的异常

        # 步骤4：生成监控记录
        log_step("generate_record", "started", "生成监控记录")
        status, message = judge_monitor_status(rule, result)
        record = MonitorRecord.objects.create(
            rule=rule,
            actual_value=get_actual_value(rule, result),
            status=status,
            message=message,
            execution_trace=execution_trace
        )
        # 新增：及时保存执行轨迹
        rule.execution_trace = execution_trace
        rule.save(update_fields=['execution_trace'])
        log_step("generate_record", "completed", f"生成记录：{record.id}（状态：{status}）")

        # 步骤5：处理告警逻辑（修复告警关闭条件）
        log_step("handle_alert", "started", "处理告警逻辑")
        alert_triggered = False
        
        if should_send_alert(rule, status):
            # 检查是否已有未解决的相同告警
            existing_alert = MonitorAlertRecord.objects.filter(
                rule=rule,
                status='unresolved',
                record__status=status
            ).first()
            
            if not existing_alert:
                # 创建新的告警记录
                alert_record = MonitorAlertRecord.objects.create(
                    rule=rule,
                    record=record,
                    status=status
                )
                # 发送告警通知
                send_alarm_notification.delay(alert_record.id)
                alert_triggered = True
                log_step("handle_alert", "completed", f"告警已触发（ID: {alert_record.id}）")
            else:
                # 更新现有告警的时间
                existing_alert.updated_at = timezone.now()
                existing_alert.save()
                log_step("handle_alert", "completed", f"已存在未解决告警（ID: {existing_alert.id}），未重复触发")
        else:
            # 修复：状态正常时关闭所有未解决告警（移除record__status条件）
            MonitorAlertRecord.objects.filter(rule=rule, status='unresolved').update(
                status='resolved',
                resolved_at=timezone.now()
            )
        log_step("handle_alert", "completed", f"告警处理完成（触发状态：{alert_triggered}）")

        # 步骤6：更新最终状态
        execution_trace["status"] = "success"
        execution_trace["end_time"] = timezone.now()
        rule.last_execution_status = 'success'
        rule.execution_trace = execution_trace
        rule.save(update_fields=['last_execution_status', 'execution_trace'])
        log_step("task_complete", "success", "监控任务执行完成")

        # 步骤7：更新动态阈值基线（优化基线存储）
        update_threshold_baseline(rule, record.actual_value)
        
        return {
            "rule_id": rule_id,
            "status": status,
            "record_id": record.id,
            "trace": execution_trace
        }

    except MonitorRule.DoesNotExist:
        error_msg = f"监控规则 {rule_id} 不存在或已禁用"
        logger.warning(error_msg)
        execution_trace["status"] = "failed"
        execution_trace["end_time"] = timezone.now()
        log_step("load_rule", "failed", error_msg)
        self.retry(countdown=60, exc=Exception(error_msg))

    except ValueError as e:
        # 处理rule_id格式错误
        error_msg = f"参数错误：{str(e)}"
        execution_trace["status"] = "failed"
        execution_trace["end_time"] = timezone.now()
        log_step("param_check", "failed", error_msg)
        logger.error(error_msg)
        return {"rule_id": rule_id, "status": "error", "error": error_msg, "trace": execution_trace}

    except Exception as e:
        error_msg = f"任务执行失败：{str(e)}"
        execution_trace["status"] = "failed"
        execution_trace["end_time"] = timezone.now()
        log_step("task_failed", "error", error_msg)
        
        # 异常情况下更新规则状态（使用显式判断）
        if rule is not None:
            MonitorRecord.objects.create(
                rule=rule,
                actual_value=0,
                status='critical',
                message=error_msg,
                execution_trace=execution_trace
            )
            rule.last_execution_status = 'failed'
            rule.execution_error = error_msg
            rule.execution_trace = execution_trace
            rule.save(update_fields=['last_execution_status', 'execution_error', 'execution_trace'])
        
        logger.error(f"监控规则 {rule_id} 执行失败：{str(e)}", exc_info=True)
        return {"rule_id": rule_id, "status": "error", "error": error_msg, "trace": execution_trace}


def judge_monitor_status(rule, test_result):
    """判断监控状态（根据规则类型和测试结果）"""
    actual = get_actual_value(rule, test_result)
    # 修复：使用有效阈值（支持动态阈值）
    threshold = rule.get_effective_threshold(rule.rule_type)
    
    if rule.rule_type == 'response_time':
        if actual > threshold * 2:
            return 'critical', f"响应时间({actual}ms)远超阈值({threshold}ms)"
        elif actual > threshold:
            return 'warning', f"响应时间({actual}ms)超过阈值({threshold}ms)"
    elif rule.rule_type == 'error_rate':
        # 修复：错误率判断逻辑
        if actual > 0.5:  # 错误率>50%为严重
            return 'critical', f"错误率({actual*100}%)过高"
        elif actual > threshold:
            return 'warning', f"错误率({actual*100}%)超过阈值({threshold*100}%)"
    elif rule.rule_type == 'status_code':
        if test_result.get('status_code', 0) not in [200, 201]:
            return 'critical', f"状态码异常: {test_result.get('status_code')}"
    return 'normal', "监控正常"


def should_send_alert(rule, current_status):
    """判断是否应该发送告警，考虑静默期和告警级别"""
    # 非异常状态不发送告警
    if current_status not in ['warning', 'critical']:
        return False
        
    # 严重告警总是发送，不受静默期限制
    if current_status == 'critical':
        return True
        
    # 检查静默期
    if rule.silence_minutes > 0:
        # 检查静默期内是否已有相同级别的告警
        recent_alert = MonitorAlertRecord.objects.filter(
            rule=rule,
            status=current_status,
            created_at__gte=timezone.now() - timedelta(minutes=rule.silence_minutes)
        ).exists()
        return not recent_alert
        
    return True


def get_actual_value(rule, test_result):
    """提取实际值（根据规则类型）"""
    if rule.rule_type == 'response_time':
        return test_result.get('response_time', 0)
    elif rule.rule_type == 'error_rate':
        
        if test_result.get('success') is False:
            # 获取最近5次执行结果计算错误率
            recent_records = MonitorRecord.objects.filter(
                rule=rule
            ).order_by('-executed_at')[:5]
            
            if recent_records:
                error_count = sum(1 for r in recent_records if not r.status == 'normal')
                return error_count / len(recent_records)
            return 1.0  # 首次执行失败
        return 0.0
    return 0


def update_threshold_baseline(rule, new_value):
    """更新动态阈值基线（新增功能）"""
    if not rule.is_dynamic_threshold:
        return
        
    # 获取最近30个数据点计算基线
    recent_records = MonitorRecord.objects.filter(
        rule=rule,
        executed_at__gte=timezone.now() - timedelta(days=7)
    ).order_by('-executed_at')[:30]
    
    if len(recent_records) < 5:  # 至少需要5个数据点
        return
        
    values = [r.actual_value for r in recent_records]
    avg_value = sum(values) / len(values)
    # 计算标准差
    std_dev = (sum((v - avg_value) **2 for v in values) / len(values))** 0.5
    
    # 更新基线
    latest_baseline = MonitorThresholdBaseline.objects.filter(
        monitor_rule=rule,
        metric_type=rule.rule_type
    ).order_by('-created_at').first()
    
    if latest_baseline:
        if timezone.now() - latest_baseline.created_at < timedelta(hours=1):
            # 最近一小时内已更新，无需重复创建
            latest_baseline.avg_value = avg_value
            latest_baseline.std_dev = std_dev
            latest_baseline.sample_count = len(values)
            latest_baseline.save()
            return
    
    MonitorThresholdBaseline.objects.create(
        monitor_rule=rule,
        metric_type=rule.rule_type,
        avg_value=avg_value,
        std_dev=std_dev,
        sample_count=len(values)
    )


@shared_task
def send_alarm_notification(record_id):
    """发送告警通知（实现完整功能）"""
    try:
        record = MonitorRecord.objects.get(id=record_id)
    except MonitorRecord.DoesNotExist:
        logger.error(f"监控记录 {record_id} 不存在")
        return "监控记录不存在"
    
    rule = record.rule
    users_to_notify = get_users_to_notify(rule.project)
    
    if not users_to_notify:
        logger.warning(f"监控规则 {rule.id} 没有需要通知的用户")
        return "没有需要通知的用户"
    
    # 构建告警消息
    subject = f"[{record.status.upper()}]监控告警：{rule.get_rule_type_display()}"
    message = (
        f"监控规则 {rule.id} 触发{record.status}告警\n"
        f"项目：{rule.project.name}\n"
        f"规则类型：{rule.get_rule_type_display()}\n"
        f"实际值：{record.actual_value}\n"
        f"状态：{record.get_status_display()}\n"
        f"描述：{record.message}\n"
        f"时间：{record.executed_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # 发送邮件通知
    if settings.SENDGRID_API_KEY and users_to_notify:
        email_recipients = [user.email for user in users_to_notify if user.email]
        if email_recipients:
            try:
                mail = Mail(
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to_emails=email_recipients,
                    subject=subject,
                    plain_text_content=message
                )
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(mail)
                
                # 记录告警日志
                alarm_log = AlarmLog.objects.create(
                    record=record,
                    notify_type='email',
                    is_success=(response.status_code in [200, 202]),
                    message=message
                )
                alarm_log.notified_users.set(users_to_notify)
                
                logger.info(f"告警通知已发送到 {len(email_recipients)} 个邮箱")
                return f"成功发送 {len(email_recipients)} 封告警邮件"
            except Exception as e:
                logger.error(f"发送告警邮件失败：{str(e)}")
                AlarmLog.objects.create(
                    record=record,
                    notify_type='email',
                    is_success=False,
                    message=f"发送失败：{str(e)}"
                )
                return f"发送告警邮件失败：{str(e)}"
    
    return "未配置邮件服务或无有效收件人"

@shared_task(bind=True, retry_backoff=2, retry_kwargs={'max_retries': 1})
def check_monitor_alarm(self, test_case_id, result_id):
    """
    检查测试结果是否触发监控告警
    :param test_case_id: 测试用例ID
    :param result_id: 测试结果ID
    """
    try:
        # 获取测试用例及关联的监控规则
        test_case = TestCase.objects.get(id=test_case_id, is_active=True)
        # 查找关联当前用例且已启用的监控规则
        monitor_rules = MonitorRule.objects.filter(
            is_active=True,
            test_case=test_case,
            # 排除定时任务类型，只处理结果触发型
            monitor_type__in=['failure', 'abnormal']
        )
        
        if not monitor_rules.exists():
            return {"status": "no monitor rules found"}

        # 获取测试结果
        from testcases.models import TestResult  # 假设结果模型
        test_result = TestResult.objects.get(id=result_id)

        # 检查是否需要触发告警
        for rule in monitor_rules:
            # 失败用例触发告警
            if rule.monitor_type == 'failure' and not test_result.success:
                execute_monitor_task.delay(rule_id=rule.id, test_result_id=result_id)
            # 异常结果触发告警（可根据实际业务定义异常判断逻辑）
            elif rule.monitor_type == 'abnormal' and test_result.has_exception:
                execute_monitor_task.delay(rule_id=rule.id, test_result_id=result_id)

        return {"status": "check completed"}
        
    except (TestCase.DoesNotExist, TestResult.DoesNotExist) as e:
        self.update_state(state='FAILURE', meta={"error": f"资源不存在: {str(e)}"})
        raise
    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        self.update_state(state='FAILURE', meta={"error": f"检查告警失败: {str(e)}"})
        raise