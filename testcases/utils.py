
import json
import jsonschema
from jsonschema.exceptions import ValidationError
from django.conf import settings
import re

def extract_response_data(response_content, extract_rules):
    """
    根据提取规则从响应中提取数据
    :param response_content: 接口响应内容（字符串）
    :param extract_rules: 提取规则字典，格式：{"变量名": {"type": "json"|"regex", "expression": "表达式"}}
    :return: 提取结果字典
    """
    result = {}
    if not extract_rules or not response_content:
        return result
    
    # 尝试将响应内容解析为JSON
    try:
        response_json = json.loads(response_content)
    except json.JSONDecodeError:
        response_json = None
    
    for var_name, rule in extract_rules.items():
        extract_type = rule.get('type', 'json')
        expression = rule.get('expression', '')
        
        if extract_type == 'json' and response_json:
            # JSON路径提取（支持简单的点语法，如data.user.id）
            keys = expression.split('.')
            value = response_json
            try:
                for key in keys:
                    if isinstance(value, list):
                        key = int(key)
                    value = value[key]
                result[var_name] = value
            except (KeyError, IndexError, ValueError):
                result[var_name] = None
        
        elif extract_type == 'regex':
            # 正则表达式提取
            match = re.search(expression, response_content)
            if match:
                result[var_name] = match.group(1) if match.groups() else match.group()
            else:
                result[var_name] = None
    
    return result

def validate_response(test_case, actual_response, actual_status_code):
    """
    验证接口响应是否符合用例断言配置
    :param test_case: TestCase实例
    :param actual_response: 实际响应内容（字符串）
    :param actual_status_code: 实际状态码
    :return: (是否通过, 错误信息列表)
    """
    pass_flag = True
    errors = []
    
    # 1. 状态码验证
    if actual_status_code != test_case.expected_status:
        pass_flag = False
        errors.append(f"状态码不匹配：预期{test_case.expected_status}，实际{actual_status_code}")
    
    # 2. JSON Schema验证（如果配置）
    if test_case.expected_json_schema and actual_response:
        try:
            response_json = json.loads(actual_response)
            jsonschema.validate(instance=response_json, schema=test_case.expected_json_schema)
        except json.JSONDecodeError:
            pass_flag = False
            errors.append(f"响应不是有效的JSON格式，无法进行Schema验证")
        except ValidationError as e:
            pass_flag = False
            errors.append(f"JSON Schema验证失败：{str(e)}")
    
    # 3. 响应内容验证（如果配置了预期响应）
    if test_case.expected_response and actual_response:
        # 支持两种匹配模式：完全匹配和包含匹配（通过前缀区分）
        expected = test_case.expected_response.strip()
        actual = actual_response.strip()
        
        if expected.startswith('CONTAINS:'):
            expected_content = expected[len('CONTAINS:'):]
            if expected_content not in actual:
                pass_flag = False
                errors.append(f"响应内容不包含预期字符串：{expected_content}")
        else:
            # 完全匹配（忽略空格和换行差异）
            expected_clean = re.sub(r'\s+', ' ', expected)
            actual_clean = re.sub(r'\s+', ' ', actual)
            if expected_clean != actual_clean:
                pass_flag = False
                errors.append(f"响应内容不匹配：预期{expected[:100]}...，实际{actual[:100]}...")
    
    return pass_flag, errors

def replace_parameters(content, parameters):
    """
    替换内容中的参数占位符
    :param content: 原始内容（字符串或字典）
    :param parameters: 参数字典，格式：{"参数名": "参数值"}
    :return: 替换后的内容
    """
    if not parameters:
        return content
    
    # 处理字典类型（如请求头、URL参数）
    if isinstance(content, dict):
        return {key: replace_parameters(value, parameters) for key, value in content.items()}
    
    # 处理字符串类型（如URL、请求体）
    if isinstance(content, str):
        for param_name, param_value in parameters.items():
            placeholder = f"{{{{{param_name}}}}}"  # 占位符格式：{{param_name}}
            content = content.replace(placeholder, str(param_value))
    return content