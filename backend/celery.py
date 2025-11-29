
import os
from celery import Celery

# 设置Django环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_test_platform.settings')

# 初始化Celery应用
app = Celery('api_test_platform')

# 从Django配置中读取Celery配置（前缀为CELERY_的配置）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有应用中的tasks.py文件
app.autodiscover_tasks()

# 测试任务（用于验证Celery是否正常工作）
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')