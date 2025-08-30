import requests
import json
from typing import Dict, List, Any, Optional
import time

def check_ollama_connection(base_url: str, timeout: int = 5) -> Dict[str, Any]:
    """
    检查与Ollama服务的连接状态
    
    Args:
        base_url: Ollama服务的基础URL
        timeout: 连接超时时间（秒）
        
    Returns:
        包含连接状态的字典
    """
    # 确保URL格式正确
    if not base_url.startswith('http'):
        base_url = f'http://{base_url}'
    
    # 确保URL以斜杠结尾
    if not base_url.endswith('/'):
        base_url = f'{base_url}/'
    
    try:
        # 构建健康检查的URL
        health_url = f'{base_url}api/health'
        
        # 发送健康检查请求
        start_time = time.time()
        response = requests.get(health_url, timeout=timeout)
        response_time = time.time() - start_time
        
        # 检查响应
        if response.status_code == 200:
            return {
                'connected': True,
                'status': 'success',
                'response_time_ms': round(response_time * 1000, 2),
                'message': 'Ollama服务连接成功'
            }
        else:
            return {
                'connected': False,
                'status': 'error',
                'status_code': response.status_code,
                'message': f'Ollama服务返回非成功状态码: {response.status_code}'
            }
    except requests.exceptions.Timeout:
        return {
            'connected': False,
            'status': 'error',
            'error_type': 'timeout',
            'message': f'Ollama服务连接超时（{timeout}秒）'
        }
    except requests.exceptions.ConnectionError:
        return {
            'connected': False,
            'status': 'error',
            'error_type': 'connection_error',
            'message': '无法连接到Ollama服务，请检查地址是否正确'
        }
    except Exception as e:
        return {
            'connected': False,
            'status': 'error',
            'error_type': 'unknown',
            'message': f'连接Ollama服务时发生错误: {str(e)}'
        }

def get_available_models(base_url: str, timeout: int = 10) -> List[Dict[str, str]]:
    """
    获取Ollama服务上可用的模型列表
    
    Args:
        base_url: Ollama服务的基础URL
        timeout: 请求超时时间（秒）
        
    Returns:
        模型信息列表
    """
    # 确保URL格式正确
    if not base_url.startswith('http'):
        base_url = f'http://{base_url}'
    
    # 确保URL以斜杠结尾
    if not base_url.endswith('/'):
        base_url = f'{base_url}/'
    
    try:
        # 构建获取模型列表的URL
        models_url = f'{base_url}api/tags'
        
        # 发送请求
        response = requests.get(models_url, timeout=timeout)
        
        # 检查响应状态
        if response.status_code == 200:
            # 解析响应
            data = response.json()
            
            # 提取模型信息
            models = data.get('models', [])
            
            # 格式化模型信息
            formatted_models = []
            for model in models:
                formatted_model = {
                    'name': model.get('name', ''),
                    'size': model.get('size', 0),
                    'modified_at': model.get('modified_at', ''),
                    'digest': model.get('digest', '')
                }
                formatted_models.append(formatted_model)
            
            return formatted_models
        else:
            raise Exception(f'获取模型列表失败，状态码: {response.status_code}')
    except requests.exceptions.Timeout:
        raise Exception(f'获取模型列表超时（{timeout}秒）')
    except json.JSONDecodeError:
        raise Exception('Ollama服务返回的不是有效的JSON数据')
    except Exception as e:
        raise Exception(f'获取模型列表时发生错误: {str(e)}')

def test_ollama_integration(base_url: str) -> Dict[str, Any]:
    """
    集成测试函数，检查连接和获取模型列表
    
    Args:
        base_url: Ollama服务的基础URL
        
    Returns:
        包含测试结果的字典
    """
    result = {
        'connection': check_ollama_connection(base_url),
        'models': [],
        'error': None
    }
    
    # 如果连接成功，尝试获取模型列表
    if result['connection']['connected']:
        try:
            result['models'] = get_available_models(base_url)
        except Exception as e:
            result['error'] = str(e)
    
    return result