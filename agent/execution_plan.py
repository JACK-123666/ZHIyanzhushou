"""
执行计划 — Agent 执行前创建多阶段计划，执行中跟踪进度
"""

import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PlanPhase:
    phase_id: str
    goal: str
    tools: List[str]
    estimated_steps: int = 1
    depends_on: List[str] = field(default_factory=list)
    status: str = 'pending'
    actual_steps: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


DEFAULT_PLAN_PHASES = [
    PlanPhase('parse', '解析文档', ['parse_document'], 1),
    PlanPhase('design', '设计分镜', ['design_shots'], 1, depends_on=['parse']),
    PlanPhase('prompts', '生成 Prompt', ['generate_prompts'], 1, depends_on=['design']),
    PlanPhase('images', '批量生成图片', ['batch_generate_images'], 2, depends_on=['prompts']),
    PlanPhase('videos', '批量生成视频', ['batch_generate_videos'], 2, depends_on=['images']),
    PlanPhase('narration', '生成配音', ['generate_narration'], 1, depends_on=['videos']),
    PlanPhase('compose', '合成视频', ['compose_video'], 1, depends_on=['videos', 'narration']),
]


class ExecutionPlan:
    """多阶段执行计划，跟踪每阶段进度。"""

    def __init__(self, phases: List[PlanPhase]):
        self.phases = phases
        self.created_at = datetime.now().isoformat()
        self._phase_index = 0

    def current_phase(self) -> Optional[PlanPhase]:
        for p in self.phases:
            if p.status in ('active', 'pending'):
                return p
        return self.phases[-1] if self.phases else None

    def mark_active(self, phase_id: str):
        for p in self.phases:
            if p.phase_id == phase_id and p.status == 'pending':
                p.status = 'active'
                p.started_at = datetime.now().isoformat()

    def mark_done(self, phase_id: str):
        for p in self.phases:
            if p.phase_id == phase_id:
                p.status = 'done'
                p.completed_at = datetime.now().isoformat()

    def mark_skipped(self, phase_id: str):
        for p in self.phases:
            if p.phase_id == phase_id:
                p.status = 'skipped'

    def advance_step(self, phase_id: str = None):
        cp = self.current_phase()
        if cp:
            cp.actual_steps += 1

    def progress_pct(self) -> float:
        done = sum(1 for p in self.phases if p.status == 'done')
        return done / len(self.phases) * 100 if self.phases else 0

    def phase_for_tool(self, tool_name: str) -> Optional[PlanPhase]:
        for p in self.phases:
            if tool_name in p.tools:
                return p
        return None

    def to_summary(self) -> str:
        lines = ['执行计划:']
        for p in self.phases:
            icon = {'pending': '○', 'active': '●', 'done': '✓', 'skipped': '✗'}.get(p.status, '?')
            progress = f'{p.actual_steps}/{p.estimated_steps}' if p.status == 'active' else ''
            lines.append(f'  {icon} {p.phase_id}: {p.goal} [{p.status}] {progress}')
        return '\n'.join(lines)

    def to_dict(self) -> dict:
        return {
            'phases': [{'phase_id': p.phase_id, 'goal': p.goal, 'tools': p.tools,
                        'estimated_steps': p.estimated_steps, 'depends_on': p.depends_on,
                        'status': p.status, 'actual_steps': p.actual_steps,
                        'started_at': p.started_at, 'completed_at': p.completed_at}
                       for p in self.phases],
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionPlan':
        phases = [PlanPhase(**p) for p in data.get('phases', [])]
        plan = cls(phases)
        plan.created_at = data.get('created_at', plan.created_at)
        return plan


def create_execution_plan(memory, client) -> ExecutionPlan:
    """LLM 生成执行计划，失败则用默认计划兜底。"""
    plan_system = """你是视频制作项目经理。根据当前镜头列表生成多阶段执行计划。

输出 JSON:
{"phases": [
  {"phase_id":"parse","goal":"解析文档","tools":["parse_document"],"estimated_steps":1},
  {"phase_id":"design","goal":"设计分镜","tools":["design_shots"],"estimated_steps":1},
  ...
]}

规则:
- 每个阶段有唯一 phase_id、简短 goal、需要的 tools、预估步数
- 图片/视频阶段 estimated_steps 根据镜头数估算 (通常每 5-10 镜 1 步)
- 若镜头无旁白文本，narration 阶段可标记为 skip
只输出 JSON。"""

    state = memory.get_state_for_llm()
    total_shots = len(memory.shots)
    has_narration = any(
        getattr(ss, '_raw', {}).get('narration', '') not in ('', '无', None)
        for ss in memory.shots.values()
    )

    try:
        resp = client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[
                {'role': 'system', 'content': plan_system},
                {'role': 'user', 'content': f'共 {total_shots} 个镜头。'
                    f'旁白: {"有" if has_narration else "无"}。\n当前状态:\n{state}'},
            ],
            temperature=0.2, max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            data = json.loads(match.group())
            phases = []
            for p in data.get('phases', []):
                phases.append(PlanPhase(
                    phase_id=p.get('phase_id', ''),
                    goal=p.get('goal', ''),
                    tools=p.get('tools', []),
                    estimated_steps=p.get('estimated_steps', 1),
                    depends_on=p.get('depends_on', []),
                ))
            if phases:
                return ExecutionPlan(phases)
    except Exception:
        pass

    # 默认计划
    phases = [PlanPhase(**{k: v for k, v in p.__dict__.items() if not k.startswith('_')})
              for p in DEFAULT_PLAN_PHASES]

    # 根据实际情况调整
    if not has_narration:
        for p in phases:
            if p.phase_id == 'narration':
                p.status = 'skipped'

    # 根据镜头数调整 images/videos 的估计步数
    for p in phases:
        if p.phase_id == 'images':
            p.estimated_steps = max(1, total_shots // 5)
        elif p.phase_id == 'videos':
            p.estimated_steps = max(1, total_shots // 3)

    return ExecutionPlan(phases)
