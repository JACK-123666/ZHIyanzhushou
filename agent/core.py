"""
ZhiyanAgent — ReAct 自主视频导演 Agent
"""

import json, re, logging, time, threading
from typing import Callable, Optional, Dict, Any
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from .memory import WorkingMemory
from .tools import ToolRegistry
from services.quality_evaluator import QualityEvaluator
from .planner import replan, reflect

logger = logging.getLogger(__name__)

MAX_AGENT_ITERATIONS = 60
CRITICAL_ACTIONS = {'design_shots', 'generate_prompts', 'batch_generate_images',
                    'batch_generate_videos', 'compose_video'}


AGENT_SYSTEM = """你是 Zhiyan，一位 AI 电影导演 Agent。接收用户文档，全自动完成从剧本到成片的视频制作。

=== Chain-of-Thought 决策框架 ===
每次决策前，按以下结构分析:

【进度】当前在计划哪个阶段？完成度？
【瓶颈】有无镜头卡住(>5min)？有无大量同类失败(>30%)？
【优先级】哪些是关键镜头(角色出场/高潮)必须成功？哪些过渡镜头可跳过？
【成本】≥3个镜头需要同操作时，必须用 batch_* 工具节省 API 调用
【策略】综合以上，选最合适的工具和参数

在 thought 中体现这 5 个维度的分析。

=== 工具列表 ===
{tools}

=== 批量优先 ===
- ≥3 镜需同操作 → batch_generate_images / batch_generate_videos
- batch_generate_images 自动同场景复用，节省 30-50% API 调用
- generate_image / generate_video 仅用于: 单镜重试、补充关键镜

=== 自适应重试 ===
- rate_limit: 第1次等15s → 第2次等30s+降并发 → 第3次等60s
- quality: 第1次原参数 → 第2次追加质量词 → 第3次降分辨率
- network: 第1次等5s → 第2次等15s → 第3次等60s
- config: 立即 abort

=== 输出格式 ===
{"thought": "【进度】... 【瓶颈】... 【优先级】... 【成本】... 【策略】...",
 "action": "工具名",
 "params": {}}

完成时: {"thought": "...", "action": "done", "params": {}}
只输出 JSON。"""


class ZhiyanAgent:
    """自主视频导演 Agent，ReAct 循环 + 预规划 + 自适应重试 + 决策反思。"""

    def __init__(self, memory: WorkingMemory, session_dir: str):
        self.memory = memory
        self.session_dir = session_dir
        self.tools = ToolRegistry(memory, session_dir)
        self.client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        self.iteration = 0
        self._final_result = None
        self._on_thought = None

    def run(self, on_thought: Callable = None, stop_event: threading.Event = None) -> dict:
        self._on_thought = on_thought
        self._stop_event = stop_event
        self.iteration = 0

        self._emit('thinking', {'content': 'Zhiyan Agent 启动...'})

        while self._final_result is None and self.iteration < MAX_AGENT_ITERATIONS:
            if self._stop_event and self._stop_event.is_set():
                self._final_result = {'status': 'cancelled', 'reason': '客户端断开连接'}
                self._emit('thinking', {'content': '停止信号，退出'})
                break
            self.iteration += 1
            try:
                self._step()
            except Exception as e:
                logger.error(f"Agent 循环异常 (iter={self.iteration}): {e}", exc_info=True)
                self.memory.record_error(str(e))
                self._emit('error', {'content': f'Agent 异常: {str(e)[:200]}'})
                if self.iteration >= MAX_AGENT_ITERATIONS - 3:
                    self._final_result = {'status': 'error', 'error': str(e)[:500]}

        if self.iteration >= MAX_AGENT_ITERATIONS and self._final_result is None:
            self._emit('error', {'content': '达到最大迭代次数，强制终止'})
            self._final_result = {'status': 'timeout', 'phase': self.memory.phase}

        self._emit('complete', self._final_result or {'status': 'unknown'})
        return self._final_result or {'status': 'unknown'}

    def _emit(self, event_type: str, data: dict):
        self.memory.record_thought(event_type, json.dumps(data, ensure_ascii=False)[:500])
        if self._on_thought:
            try:
                self._on_thought(event_type, data)
            except Exception:
                pass

    def _step(self):
        state = self.memory.get_state_for_llm()
        tools_desc = self.tools.list_for_llm()

        if self.memory.phase == 'planning' and self.memory.execution_plan is None:
            self._create_and_store_plan()

        plan_context = self._get_plan_context()
        system_prompt = AGENT_SYSTEM.format(tools=tools_desc)

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'{state}\n\n{plan_context}\n\n请按 CoT 框架分析并决定下一步。'},
        ]

        recent = self.memory.thought_history[-5:]
        if recent:
            history_text = '最近操作:\n' + '\n'.join(
                f"[{h['type']}] {h['content'][:150]}" for h in recent
            )
            messages.insert(1, {'role': 'user', 'content': history_text})

        self._emit('thinking', {'content': 'CoT 分析中...'})

        try:
            resp = self.client.chat.completions.create(
                model='deepseek-v4-pro',
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
            )
            raw = resp.choices[0].message.content.strip()
        except Exception as e:
            self._emit('error', {'content': f'LLM 调用失败: {str(e)[:150]}'})
            time.sleep(5)
            return

        action_data = self._parse_action(raw)
        if not action_data:
            self._emit('error', {'content': f'LLM 输出解析失败: {raw[:200]}'})
            return

        thought = action_data.get('thought', '')
        action = action_data.get('action', '')
        params = action_data.get('params', {})

        self._emit('thinking', {'content': thought})

        if action == 'done':
            self._final_result = {
                'status': 'done', 'phase': self.memory.phase,
                'session_id': self.memory.session_id,
            }
            self.memory.save()
            return

        if action not in self.tools.list_names():
            self._emit('error', {'content': f'未知工具: {action}'})
            return

        self.memory.advance_plan_step(action)
        self._emit('tool_call', {'tool': action, 'params': params})
        result = self.tools.execute(action, **params)

        if result.get('success') is False:
            result = self._adaptive_retry(action, params, result)
        else:
            self._emit('tool_result', {'tool': action, 'success': True,
                                       'summary': json.dumps(result, ensure_ascii=False)[:300]})
            self.memory.estimate_cost(action)

            if action in CRITICAL_ACTIONS:
                self._self_reflect(action, params, result)

        self.memory.save()

    # ── 预规划 ──

    def _create_and_store_plan(self):
        from .execution_plan import create_execution_plan
        plan = create_execution_plan(self.memory, self.client)
        self.memory.set_plan(plan)
        self._emit('plan_created', {'phases': [p.phase_id for p in plan.phases],
                                    'summary': plan.to_summary()})

    def _get_plan_context(self) -> str:
        if not self.memory.execution_plan:
            return '执行计划: 尚未创建'
        return self.memory.execution_plan.to_summary()

    # ── 自适应重试 ──

    def _adaptive_retry(self, action: str, params: dict, first_result: dict) -> dict:
        error_msg = first_result.get('error', '未知错误')
        category = QualityEvaluator.categorize_failure(error_msg)
        self._emit('eval', {'tool': action, 'success': False,
                           'error': error_msg[:200], 'category': category})

        if category == 'config':
            self._emit('error', {'content': f'配置错误，终止: {error_msg[:200]}'})
            self._final_result = {'status': 'aborted', 'reason': f'配置错误: {error_msg[:200]}'}
            return first_result

        base_waits = {'rate_limit': 15, 'network': 5, 'quality': 5, 'unknown': 5}

        for attempt in range(3):
            wait = base_waits.get(category, 5) * (2 ** attempt)
            self._emit('replan', {'category': category, 'error': error_msg[:150],
                                 'attempt': attempt + 1})

            replan_result = replan(
                {'tool': action, 'error': error_msg, 'category': category},
                self.memory.get_state_for_llm(),
                attempt_number=attempt,
            )
            decision = replan_result.get('decision', 'retry')
            self._emit('thinking', {
                'content': f'重试决策(第{attempt+1}次): {decision} — {replan_result.get("reason", "")}'
            })

            if decision == 'abort':
                self._final_result = {'status': 'aborted',
                                     'reason': replan_result.get('reason', '')}
                self.memory.save()
                return first_result

            if decision == 'skip':
                self._emit('thinking', {'content': '跳过，继续'})
                return first_result

            exec_params = dict(params)
            if decision == 'modify':
                modified = replan_result.get('modified_params', {})
                if modified:
                    exec_params.update(modified)
                    self._emit('thinking', {'content': f'修改参数重试: {modified}'})

            exec_params = self._mutate_params(action, exec_params, category, attempt)

            self._emit('thinking', {'content': f'等待 {wait}s 后重试...'})
            time.sleep(wait)
            result = self.tools.execute(action, **exec_params)
            if result.get('success') is not False:
                self._emit('tool_result', {'tool': action, 'success': True,
                    'summary': f'重试{attempt+1}次后成功: ' +
                    json.dumps(result, ensure_ascii=False)[:200]})
                self.memory.estimate_cost(action)
                return result

            error_msg = result.get('error', '未知错误')
            category = QualityEvaluator.categorize_failure(error_msg)
            self._emit('eval', {'tool': action, 'success': False,
                               'error': error_msg[:200], 'category': category})

        self._emit('error', {'content': f'{action} 重试3次后仍失败: {error_msg[:150]}'})
        return first_result

    def _mutate_params(self, action: str, params: dict, category: str, attempt: int) -> dict:
        if attempt == 0:
            return params

        p = dict(params)
        if category == 'rate_limit' and attempt >= 1:
            if 'shot_ids' in p and isinstance(p['shot_ids'], list) and len(p['shot_ids']) > 3:
                p['shot_ids'] = p['shot_ids'][:max(1, len(p['shot_ids']) // 2)]
        elif category == 'quality' and attempt >= 1:
            if 'resolution' in p:
                p['resolution'] = '480p'
        return p

    # ── 自我反思 ──

    def _self_reflect(self, action: str, params: dict, result: dict):
        try:
            refl = reflect(action, params, result, self.memory.get_state_for_llm())
            self.memory.record_reflection(action,
                refl.get('assessment', 'adequate'),
                refl.get('score', 3))
            self._emit('reflection', {'action': action,
                'assessment': refl.get('assessment', '?'),
                'score': refl.get('score', 3),
                'lesson': refl.get('lesson', '')})
        except Exception:
            pass

    # ── JSON 解析 ──

    def _parse_action(self, raw: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None
