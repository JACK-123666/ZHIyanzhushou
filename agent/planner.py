"""
动态重规划 + 决策反思
"""

import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


REPLAN_SYSTEM = """你是视频制作项目经理，正在处理执行中的异常。

=== 决策规则 ===
- rate_limit: 建议等待后重试。第1次等15s，第2次等30s+降低并发，第3次等60s
- network: 建议重试。第1次等5s，第2次等15s，第3次等60s
- quality: 关键镜头(角色出场/高潮)→修改prompt重试；过渡镜头→可跳过
- config: 立即终止

=== 参数修改建议 ===
- rate_limit 第2次: 降低batch并发数(如10→5)
- quality 第2次: 追加"high quality, detailed, sharp focus"到prompt
- quality 第3次: 降级分辨率(如720p→480p)

输出JSON:
{"decision": "retry"|"skip"|"modify"|"abort",
 "reason": "原因",
 "modified_params": {}}
只输出JSON。"""


REFLECT_SYSTEM = """你是视频制作的决策审计员。快速评估刚才的决策质量。

基于操作结果，判断:
- good: 决策正确，结果符合预期
- adequate: 决策基本合理，但可以优化
- poor: 决策有问题，应该调整策略

输出JSON:
{"assessment": "good"|"adequate"|"poor",
 "score": 1-5,
 "lesson": "教训(1句话)",
 "suggestion": "改进建议(1句话)"}
只输出JSON。"""


def _get_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def replan(failure_info: dict, memory_state: str, attempt_number: int = 0) -> dict:
    """根据失败信息生成调整策略。attempt_number 从 0 开始。"""
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[
                {'role': 'system', 'content': REPLAN_SYSTEM},
                {'role': 'user', 'content': json.dumps({
                    'failure': failure_info,
                    'state': memory_state,
                    'attempt': attempt_number + 1,
                }, ensure_ascii=False)},
            ],
            temperature=0.2, max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].split('```')[0]
        result = json.loads(content)

        if attempt_number >= 1 and result.get('decision') == 'retry':
            result['decision'] = 'modify'
            if 'modified_params' not in result or not result.get('modified_params'):
                cat = failure_info.get('category', '')
                if cat == 'quality':
                    result['modified_params'] = {'prompt_suffix': 'high quality, sharp focus, detailed'}
                elif cat == 'rate_limit':
                    result['modified_params'] = {'reduce_concurrency': True}

        return result
    except Exception:
        return {'decision': 'retry', 'reason': 'LLM 重规划不可用，默认重试', 'modified_params': {}}


def reflect(action: str, params: dict, result: dict, memory_state: str) -> dict:
    """快速评估决策质量，输出 {assessment, score, lesson, suggestion}。"""
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[
                {'role': 'system', 'content': REFLECT_SYSTEM},
                {'role': 'user', 'content': json.dumps({
                    'action': action, 'params': params,
                    'result': result, 'state': memory_state,
                }, ensure_ascii=False)},
            ],
            temperature=0.2, max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].split('```')[0]
        return json.loads(content)
    except Exception:
        return {'assessment': 'adequate', 'score': 3,
                'lesson': '反思不可用', 'suggestion': '继续执行'}
