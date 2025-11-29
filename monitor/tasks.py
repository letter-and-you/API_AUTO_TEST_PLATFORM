from celery import shared_task
from sendgrid import Mail
from sendgrid import SendGridAPIClient
from django.conf import settings
from .models import MonitorRule, MonitorRecord, AlarmLog
from excutors.runner import run_single_case
from common.utils import get_users_to_notify

@shared_task(bind=True, max_retries=3)
def execute_monitor_task(self, rule_id):
    """执行单个监控规则"""
    try:
        rule = MonitorRule.objects.get(id=rule_id, is_active=True)
    except MonitorRule.DoesNotExist:
        self.retry(countdown=60)  # 规则不存在时重试
    
    # 执行关联的测试用例
    test_case = rule.test_case
    result = run_single_case(test_case.id)
    
    # 生成监控记录
    status, message = judge_monitor_status(rule, result)
    record = MonitorRecord.objects.create(
        rule=rule,
        actual_value=get_actual_value(rule, result),
        status=status,
        message=message
    )
    
    # 触发告警（异常状态）
    if status in ['warning', 'critical']:
        send_alarm_notification.delay(record.id)
    
    return {"rule_id": rule_id, "status": status}


def judge_monitor_status(rule, test_result):
    """判断监控状态（根据规则类型和测试结果）"""
    actual = get_actual_value(rule, test_result)
    if rule.rule_type == 'response_time':
        if actual > rule.threshold * 2:
            return 'critical', f"响应时间({actual}ms)远超阈值({rule.threshold}ms)"
        elif actual > rule.threshold:
            return 'warning', f"响应时间({actual}ms)超过阈值({rule.threshold}ms)"
    elif rule.rule_type == 'error_rate':
        if actual > 0.5:  # 错误率>50%为严重
            return 'critical', f"错误率({actual*100}%)过高"
        elif actual > rule.threshold:
            return 'warning', f"错误率({actual*100}%)超过阈值({rule.threshold*100}%)"
    elif rule.rule_type == 'status_code':
        if test_result.get('status_code', 0) not in [200, 201]:
            return 'critical', f"状态码异常: {test_result.get('status_code')}"
    return 'normal', "监控正常"


def get_actual_value(rule, test_result):
    """提取实际值（根据规则类型）"""
    if rule.rule_type == 'response_time':
        return test_result.get('response_time', 0)
    elif rule.rule_type == 'error_rate':
        return 0 if test_result.get('success') else 1
    return 0


@shared_task
def send_alarm_notification(record_id):
    """发送告警通知"""
    record = MonitorRecord.objects.get(id=record_id)
    rule = record.rule
    project = rule.project
    
    # 获取需要通知的用户
    users = get_users_to_notify(project)
    if not users:
        return "无需要通知的用户"
    
    # 构建告警内容
    alarm_msg = (
        f"[API监控告警]\n"
        f"项目: {project.name}\n"
        f"规则: {rule.get_rule_type_display()}\n"
        f"状态: {record.get_status_display()}\n"
        f"详情: {record.message}\n"
        f"时间: {record.executed_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # 发送通知（根据用户配置）
    for user in users:
        config = user.notify_config
        if not config.is_active:
            continue
            
        # 邮件通知
        if config.notify_type in ['email', 'both'] and user.alarm_email:
            send_email.delay(user.alarm_email, "API监控告警", alarm_msg)
            AlarmLog.objects.create(
                record=record,
                notify_type='email',
                message=alarm_msg,
                is_success=True
            ).notified_users.add(user)
        #电话通知
        elif config.notify_type in ['phones', 'both'] and user.alarm_phone:
            send_phone.delay(user.alarm_phone, "API监控告警", alarm_msg)
            AlarmLog.objects.create(
                record=record,
                notify_type='phone',
                message=alarm_msg,
                is_success=True
            ).notified_users.add(user)
    return f"已通知 {len(users)} 位用户"


@shared_task
def send_email(to_email, subject, content):
    """发送邮件(优先使用SendGrid,回退到Django邮件发送)"""
    # 尝试导入 SendGrid，如果不可用则回退到 Django 的 send_mail
    try:
        
        
        sg_available = True
    except Exception:
        sg_available = False

    try:
        if sg_available:
            message = Mail(
                from_email=settings.NOTIFY_CONFIG['email']['FROM_EMAIL'],
                to_emails=to_email,
                subject=subject,
                plain_text_content=content
            )
            sg = SendGridAPIClient(settings.NOTIFY_CONFIG['email']['SENDGRID_API_KEY'])
            sg.send(message)
            return True
        else:
            # 回退到 Django 的邮件发送
            from django.core.mail import send_mail as django_send_mail
            from_email = settings.NOTIFY_CONFIG.get('email', {}).get('FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', None))
            # 如果没有配置 FROM_EMAIL 且 settings 没有 DEFAULT_FROM_EMAIL，直接失败以便被捕获
            if not from_email:
                raise RuntimeError("No FROM_EMAIL configured for email sending")
            django_send_mail(subject, content, from_email, [to_email], fail_silently=False)
            return True
    except Exception:
        return False

@shared_task
def send_phone(to_phone, subject, content):
    """发送电话短信"""
    # 这里可以集成第三方短信服务商的API进行短信发送
    # 目前仅为示例，实际实现需根据具体服务商的SDK或API文档来编写
    try:
        # 示例伪代码
        # sms_client = SMSClient(api_key=settings.NOTIFY_CONFIG['phone']['API_KEY'])
        # sms_client.send_message(to_phone, f"{subject}\n{content}")
        return True
    except Exception:
        return False
