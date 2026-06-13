"""
Agent 工作记忆 — 每个 shot 的完整生命周期状态机，代码层确定性追踪
"""

import json, os
from datetime import datetime


class ShotState:
    """单个镜头状态机"""

    VALID_STATES = [
        'idle', 'prompt_ready',
        'image_generating', 'image_done', 'image_failed',
        'video_generating', 'video_done', 'video_failed',
        'narration_done', 'narration_failed',
    ]

    def __init__(self, shot_id: str):
        self.shot_id = shot_id
        self.status = 'idle'
        self.image_path = None
        self.video_path = None
        self.narration_path = None
        self.image_prompt = None
        self.video_prompt = None
        self.failure_reason = None
        self.retry_count = 0
        self.image_reused_from = None

    def to_dict(self):
        d = {
            'shot_id': self.shot_id, 'status': self.status,
            'image_path': self.image_path, 'video_path': self.video_path,
            'narration_path': self.narration_path, 'image_prompt': self.image_prompt,
            'video_prompt': self.video_prompt, 'failure_reason': self.failure_reason,
            'retry_count': self.retry_count, 'image_reused_from': self.image_reused_from,
        }
        if hasattr(self, '_raw'):
            d['_raw'] = self._raw
        return d

    @classmethod
    def from_dict(cls, d):
        s = cls(d['shot_id'])
        s.status = d.get('status', 'idle')
        s.image_path = d.get('image_path')
        s.video_path = d.get('video_path')
        s.narration_path = d.get('narration_path')
        s.image_prompt = d.get('image_prompt')
        s.video_prompt = d.get('video_prompt')
        s.failure_reason = d.get('failure_reason')
        s.retry_count = d.get('retry_count', 0)
        s.image_reused_from = d.get('image_reused_from')
        if '_raw' in d:
            s._raw = d['_raw']
        return s


class WorkingMemory:
    """
    当前 session 的完整状态图。

    - 追踪每个 shot 的状态机转换
    - 记录 Agent 思考历史和工具调用链
    - get_state_for_llm() 生成 LLM 可读的上下文摘要
    - 持久化到 agent_state.json，与管线 state.json 分离
    """

    STATE_FILE = 'agent_state.json'
    MAX_THOUGHT_HISTORY = 50

    def __init__(self, session_id: str, session_dir: str, config: dict = None):
        self.session_id = session_id
        self.session_dir = session_dir
        self.config = config or {}
        self.phase = 'init'
        self.shots = {}
        self.characters = {}
        self.scene_map = {}
        self.global_style = ''
        self.emotion_arc = ''
        self.title = ''
        self.thought_history = []
        self.execution_plan = None
        self.action_reflections = []
        self.cost_estimates = {'api_calls_made': 0, 'api_calls_saved_by_batch': 0,
                               'api_calls_saved_by_reuse': 0, 'estimated_remaining': 0}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def init_shots(self, shot_list: list):
        self.shots = {}
        for s in shot_list:
            ss = ShotState(s['id'])
            ss._raw = s
            self.shots[s['id']] = ss

    def update_shot(self, shot_id: str, **kwargs):
        if shot_id in self.shots:
            for k, v in kwargs.items():
                if hasattr(self.shots[shot_id], k):
                    setattr(self.shots[shot_id], k, v)

    def get_shot(self, shot_id: str):
        return self.shots.get(shot_id)

    def get_shots_by_status(self, status: str) -> list:
        return [s for s in self.shots.values() if s.status == status]

    def count_by_status(self, status: str) -> int:
        return sum(1 for s in self.shots.values() if s.status == status)

    def record_thought(self, thought_type: str, content: str):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': thought_type,
            'content': content,
        }
        self.thought_history.append(entry)
        if len(self.thought_history) > self.MAX_THOUGHT_HISTORY:
            self.thought_history = self.thought_history[-self.MAX_THOUGHT_HISTORY:]

    def record_error(self, error: str):
        self.record_thought('error', str(error)[:300])

    def set_plan(self, plan):
        self.execution_plan = plan

    def advance_plan_step(self, tool_name: str = None):
        if self.execution_plan:
            if tool_name:
                phase = self.execution_plan.phase_for_tool(tool_name)
                if phase:
                    self.execution_plan.mark_active(phase.phase_id)
                    self.execution_plan.advance_step(phase.phase_id)
            else:
                self.execution_plan.advance_step()

    def record_reflection(self, action: str, assessment: str, score: int):
        self.action_reflections.append({
            'timestamp': datetime.now().isoformat(),
            'action': action, 'assessment': assessment, 'score': score
        })
        if len(self.action_reflections) > 20:
            self.action_reflections = self.action_reflections[-20:]

    def estimate_cost(self, action: str, shot_count: int = 1):
        ce = self.cost_estimates
        if action in ('generate_image', 'batch_generate_images'):
            ce['api_calls_made'] += shot_count
        elif action in ('generate_video', 'batch_generate_videos'):
            ce['api_calls_made'] += shot_count * 2
        elif action in ('design_shots', 'generate_prompts'):
            ce['api_calls_made'] += 1
        ce['estimated_remaining'] = max(0,
            len(self.shots) * 3 - ce['api_calls_made'])

    def get_state_for_llm(self) -> str:
        try:
            from .state_summary import generate_smart_summary
            return generate_smart_summary(self)
        except Exception:
            return self._get_state_raw()

    def _get_state_raw(self) -> str:
        total = len(self.shots)
        image_done = self.count_by_status('image_done')
        video_done = self.count_by_status('video_done')
        failed = (self.count_by_status('image_failed') +
                  self.count_by_status('video_failed') +
                  self.count_by_status('narration_failed'))

        lines = [
            f"=== 当前状态 ===",
            f"阶段: {self.phase}",
            f"总镜头数: {total}",
            f"图片完成: {image_done}/{total}",
            f"视频完成: {video_done}/{total}",
            f"失败镜头: {failed}",
            f"角色数: {len(self.characters)}",
            f"场景数: {len(self.scene_map)}",
        ]

        if self.shots:
            lines.append("\n=== 各镜头状态 ===")
            for sid, ss in self.shots.items():
                extra = ''
                if ss.failure_reason:
                    extra = f" [失败原因: {ss.failure_reason[:80]}]"
                if ss.image_reused_from:
                    extra += f" [复用自: {ss.image_reused_from}]"
                lines.append(f"  {sid}: {ss.status}{extra}")

        recent_errors = [h for h in self.thought_history if h.get('type') == 'error']
        if recent_errors:
            lines.append(f"\n=== 最近错误 ===")
            for e in recent_errors[-3:]:
                lines.append(f"  [{e['timestamp'][:19]}] {e['content'][:120]}")

        return '\n'.join(lines)

    def to_dict(self) -> dict:
        d = {
            'session_id': self.session_id, 'phase': self.phase,
            'config': self.config, 'shots': {k: v.to_dict() for k, v in self.shots.items()},
            'characters': self.characters, 'scene_map': self.scene_map,
            'global_style': self.global_style, 'emotion_arc': self.emotion_arc,
            'title': self.title, 'thought_history': self.thought_history,
            'action_reflections': self.action_reflections,
            'cost_estimates': self.cost_estimates,
            'created_at': self.created_at,
            'updated_at': datetime.now().isoformat(),
        }
        if self.execution_plan:
            d['execution_plan'] = self.execution_plan.to_dict()
        return d

    def _state_path(self):
        return os.path.join(self.session_dir, self.STATE_FILE)

    def save(self):
        self.updated_at = datetime.now().isoformat()
        with open(self._state_path(), 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, session_id: str, session_dir: str) -> 'WorkingMemory':
        path = os.path.join(session_dir, cls.STATE_FILE)
        if not os.path.exists(path):
            old_path = os.path.join(session_dir, 'state.json')
            if os.path.exists(old_path):
                return cls._migrate_from_old(session_id, session_dir, old_path)
            return None
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls._from_dict(session_id, session_dir, data)

    @classmethod
    def _from_dict(cls, session_id: str, session_dir: str, data: dict) -> 'WorkingMemory':
        mem = cls(session_id, session_dir, data.get('config', {}))
        mem.phase = data.get('phase', 'init')
        mem.characters = data.get('characters', {})
        mem.scene_map = data.get('scene_map', {})
        mem.global_style = data.get('global_style', '')
        mem.emotion_arc = data.get('emotion_arc', '')
        mem.title = data.get('title', '')
        mem.thought_history = data.get('thought_history', [])
        mem.action_reflections = data.get('action_reflections', [])
        mem.cost_estimates = data.get('cost_estimates',
            {'api_calls_made': 0, 'api_calls_saved_by_batch': 0,
             'api_calls_saved_by_reuse': 0, 'estimated_remaining': 0})
        mem.created_at = data.get('created_at', mem.created_at)
        if 'execution_plan' in data:
            from .execution_plan import ExecutionPlan
            mem.execution_plan = ExecutionPlan.from_dict(data['execution_plan'])
        for sid, sd in data.get('shots', {}).items():
            mem.shots[sid] = ShotState.from_dict(sd)
        return mem

    @classmethod
    def _migrate_from_old(cls, session_id: str, session_dir: str, old_path: str) -> 'WorkingMemory':
        with open(old_path, 'r', encoding='utf-8') as f:
            old = json.load(f)

        config = old.get('config', {})
        for key in ('filepath', 'filename'):
            if key in old and key not in config:
                config[key] = old[key]
        mem = cls(session_id, session_dir, config)

        old_shots = old.get('shots', [])
        if isinstance(old_shots, list):
            mem.phase = 'migrated'
            mem.init_shots(old_shots)
            for s in old_shots:
                sid = s.get('id', '')
                ss = mem.shots.get(sid)
                if not ss:
                    continue
                if s.get('image_path') and os.path.exists(s.get('image_path', '')):
                    ss.status = 'image_done'
                    ss.image_path = s['image_path']
                if s.get('video_path') and os.path.exists(s.get('video_path', '')):
                    ss.status = 'video_done'
                    ss.video_path = s['video_path']
                if s.get('narration_path'):
                    ss.narration_path = s['narration_path']
                    ss.status = 'narration_done'
                if s.get('image_prompt'):
                    ss.image_prompt = s['image_prompt']
                    if ss.status == 'idle':
                        ss.status = 'prompt_ready'
                if s.get('video_prompt'):
                    ss.video_prompt = s['video_prompt']
        else:
            mem = cls._from_dict(session_id, session_dir, old)

        mem.title = old.get('title', '')
        mem.scene_map = old.get('scene_map', {})
        mem.characters = old.get('character_summary', old.get('characters', {}))
        mem.global_style = old.get('global_tone', '')
        mem.emotion_arc = old.get('global_tone', '')
        mem.save()
        return mem
