"""
Agent 工具注册表 — 将 services 封装为 LLM 可调用的 Tool
"""

import os, json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from config import get_model_config, LANGUAGES, DEFAULT_LANGUAGE
from .memory import WorkingMemory
from services.quality_evaluator import QualityEvaluator


class Tool:
    """Agent 工具：名称、参数 schema、执行函数。"""

    def __init__(self, name: str, description: str, parameters: dict, func: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_llm_desc(self) -> str:
        """生成注入 LLM System Prompt 的工具描述。"""
        params_desc = json.dumps(self.parameters.get('properties', {}),
                                 ensure_ascii=False, indent=2)
        return f"### {self.name}\n{self.description}\n参数:\n{params_desc}\n"

    def execute(self, **kwargs) -> dict:
        try:
            return {'success': True, 'data': self.func(**kwargs)}
        except Exception as e:
            return {'success': False, 'error': str(e)[:500]}


class ToolRegistry:
    """工具注册表，Agent 的工具箱。"""

    def __init__(self, memory: WorkingMemory, session_dir: str):
        self.memory = memory
        self.session_dir = session_dir
        self._tools = {}
        self._register_all()
        self._cached_llm_desc = '\n'.join(
            t.to_llm_desc() for t in self._tools.values()
        )

    def _register_all(self):
        self._register(Tool(
            'parse_document',
            '解析上传的文档(.txt/.docx)，提取全文内容',
            {'type': 'object', 'properties': {
                'filepath': {'type': 'string', 'description': '文档文件的完整路径'},
            }, 'required': ['filepath']},
            self._parse_document,
        ))
        self._register(Tool(
            'design_shots',
            '调用 LLM 通读文档内容，设计完整分镜脚本（镜号/场景/运镜/灯光/时长/角色）',
            {'type': 'object', 'properties': {}, 'required': []},
            self._design_shots,
        ))
        self._register(Tool(
            'generate_prompts',
            '为所有镜头生成结构化的 image_prompt 和 video_prompt。必须先完成 design_shots',
            {'type': 'object', 'properties': {}, 'required': []},
            self._generate_prompts,
        ))
        self._register(Tool(
            'generate_image',
            '为单个镜头调用 Seedream 生成关键帧图片',
            {'type': 'object', 'properties': {
                'shot_id': {'type': 'string', 'description': '镜头编号，如 SC01'},
            }, 'required': ['shot_id']},
            self._generate_image,
        ))
        self._register(Tool(
            'generate_video',
            '为单个镜头调用 Seedance 将关键帧转为视频片段',
            {'type': 'object', 'properties': {
                'shot_id': {'type': 'string', 'description': '镜头编号，如 SC01'},
            }, 'required': ['shot_id']},
            self._generate_video,
        ))
        self._register(Tool(
            'generate_narration',
            '为单个镜头调用 Edge TTS 生成旁白配音',
            {'type': 'object', 'properties': {
                'shot_id': {'type': 'string', 'description': '镜头编号，如 SC01'},
            }, 'required': ['shot_id']},
            self._generate_narration,
        ))
        self._register(Tool(
            'batch_generate_images',
            '批量并行生成多个镜头的图片，自动同场景复用',
            {'type': 'object', 'properties': {
                'shot_ids': {'type': 'array', 'items': {'type': 'string'},
                            'description': '镜头编号列表。空数组表示全部待生成'},
            }, 'required': ['shot_ids']},
            self._batch_generate_images,
        ))
        self._register(Tool(
            'batch_generate_videos',
            '批量并行生成多个镜头的视频',
            {'type': 'object', 'properties': {
                'shot_ids': {'type': 'array', 'items': {'type': 'string'},
                            'description': '镜头编号列表。空数组表示全部待生成'},
            }, 'required': ['shot_ids']},
            self._batch_generate_videos,
        ))
        self._register(Tool(
            'compose_video',
            '将所有已完成的视频片段、配音、字幕合成为最终视频文件',
            {'type': 'object', 'properties': {}, 'required': []},
            self._compose_video,
        ))
        self._register(Tool(
            'check_status',
            '查看当前工作状态——已完成/失败/待处理的镜头',
            {'type': 'object', 'properties': {}, 'required': []},
            self._check_status,
        ))

    def _register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_for_llm(self) -> str:
        return self._cached_llm_desc

    def list_names(self) -> list:
        return list(self._tools.keys())

    def execute(self, name: str, **kwargs) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {'success': False, 'error': f'未知工具: {name}'}
        return tool.execute(**kwargs)

    def _record_shot_failure(self, shot_id: str, step: str, error: Exception) -> dict:
        reason = str(error)[:200]
        category = QualityEvaluator.categorize_failure(reason)
        status = f'{step}_failed'
        self.memory.update_shot(shot_id, status=status, failure_reason=reason)
        self.memory.record_error(f'{shot_id} {step}失败: {reason}')
        return {'shot_id': shot_id, 'status': status,
                'reason': reason, 'category': category}

    # ── 工具实现 ──

    def _parse_document(self, filepath: str) -> dict:
        from services.document_parser import parse_document
        content = parse_document(filepath)
        self.memory.record_thought('tool_result',
                                    f'文档解析完成，共 {len(content)} 字符')
        return {'content': content, 'length': len(content)}

    def _design_shots(self) -> dict:
        filepath = self.memory.config.get('filepath', '')
        if not filepath:
            return {'error': '未找到文档路径，请先调用 parse_document'}

        from services.llm_service import design_shots_from_document
        from services.document_parser import parse_document

        content = parse_document(filepath)
        result = design_shots_from_document(content, self.memory.config)

        shots = result.get('shots', [])
        self.memory.scene_map = result.get('scene_map', {})
        self.memory.characters = result.get('character_summary', {})
        self.memory.emotion_arc = result.get('emotion_curve', '')
        self.memory.title = result.get('title', '')
        self.memory.init_shots(shots)
        self.memory.phase = 'planning'

        self.memory.record_thought('tool_result',
            f'分镜设计完成: {len(shots)}镜头, '
            f'{len(self.memory.scene_map)}场景, '
            f'{len(self.memory.characters)}角色')

        return {
            'shot_count': len(shots),
            'scene_count': len(self.memory.scene_map),
            'character_count': len(self.memory.characters),
            'title': self.memory.title,
            'shots_preview': [
                {'id': s['id'], 'duration': s.get('final_duration', 5),
                 'location': s.get('location', ''),
                 'mood': s.get('mood', '')}
                for s in shots
            ],
        }

    def _generate_prompts(self) -> dict:
        from services.llm_service import generate_prompts

        shot_list = []
        for sid, ss in self.memory.shots.items():
            if hasattr(ss, '_raw'):
                shot_list.append(ss._raw)

        if not shot_list:
            return {'error': '没有分镜数据，请先调用 design_shots'}

        prompts = generate_prompts(shot_list, self.memory.config,
                                   character_summary=self.memory.characters)

        for p in prompts:
            sid = p.get('shot_id', '')
            self.memory.update_shot(sid,
                                     image_prompt=p.get('image_prompt', ''),
                                     video_prompt=p.get('video_prompt', ''),
                                     status='prompt_ready')

        self.memory.record_thought('tool_result',
                                    f'Prompt 生成完成，共 {len(prompts)} 个镜头')
        return {'prompt_count': len(prompts)}

    def _generate_image(self, shot_id: str) -> dict:
        ss = self.memory.get_shot(shot_id)
        if not ss:
            return {'error': f'镜头 {shot_id} 不存在'}
        if not ss.image_prompt:
            return {'error': f'镜头 {shot_id} 没有 image_prompt，请先调用 generate_prompts'}

        model_config = get_model_config('seedream')
        resolution = self.memory.config.get('resolution', '1920x1080')
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.session_dir, f'{ts}_{shot_id}_kf.png')

        self.memory.update_shot(shot_id, status='image_generating')
        self.memory.record_thought('tool_call',
                                    f'调用 Seedream 生成 {shot_id} 关键帧...')

        try:
            from services.image_generator import generate_image
            generate_image(model_config, ss.image_prompt, resolution, path)

            eval_result = QualityEvaluator.evaluate_image(path)
            if eval_result['pass']:
                self.memory.update_shot(shot_id, image_path=path, status='image_done')
                self.memory.record_thought('tool_result',
                    f'{shot_id} 关键帧生成成功 ✅')
                return {'shot_id': shot_id, 'status': 'image_done', 'path': path}
            else:
                self.memory.update_shot(shot_id, status='image_failed',
                                         failure_reason=eval_result['reason'])
                return {'shot_id': shot_id, 'status': 'image_failed',
                        'reason': eval_result['reason'], 'action': eval_result['action']}
        except Exception as e:
            return self._record_shot_failure(shot_id, 'image', e)

    def _generate_video(self, shot_id: str) -> dict:
        ss = self.memory.get_shot(shot_id)
        if not ss:
            return {'error': f'镜头 {shot_id} 不存在'}
        if ss.status != 'image_done' or not ss.image_path:
            return {'error': f'镜头 {shot_id} 图片未就绪(current: {ss.status})，请先生成图片'}

        model_config = get_model_config('seedance')
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = os.path.join(self.session_dir, f'{ts}_{shot_id}.mp4')

        self.memory.update_shot(shot_id, status='video_generating')
        self.memory.record_thought('tool_call',
                                    f'调用 Seedance 生成 {shot_id} 视频...')

        try:
            from services.pipeline import (
                build_seedance_payload, create_seedance_task,
                poll_seedance_task, download_video,
            )

            payload = build_seedance_payload(
                model=model_config['model'],
                first_frame_path=ss.image_path,
                video_prompt=ss.video_prompt or '',
                duration=getattr(ss, '_raw', {}).get('final_duration', 5),
                resolution=self.memory.config.get('video_quality', '480p'),
                seed_session_id=f"{self.memory.session_id}_{shot_id}",
            )

            tid = create_seedance_task(model_config['api_url'],
                                       model_config['api_key'], payload)
            if not tid:
                raise RuntimeError('Seedance 创建任务失败')

            poll_result = poll_seedance_task(model_config['api_url'],
                                              model_config['api_key'], tid)
            if poll_result['status'] != 'succeeded' or not poll_result['video_url']:
                raise RuntimeError(f"Seedance 任务失败: {poll_result['status']}")

            if not download_video(poll_result['video_url'], out):
                raise RuntimeError('视频下载失败')

            eval_result = QualityEvaluator.evaluate_video(out)
            if eval_result['pass']:
                self.memory.update_shot(shot_id, video_path=out, status='video_done')
                self.memory.record_thought('tool_result',
                    f'{shot_id} 视频生成成功 ✅')
                return {'shot_id': shot_id, 'status': 'video_done', 'path': out}
            else:
                self.memory.update_shot(shot_id, status='video_failed',
                                         failure_reason=eval_result['reason'])
                return {'shot_id': shot_id, 'status': 'video_failed',
                        'reason': eval_result['reason'], 'action': eval_result['action']}

        except Exception as e:
            return self._record_shot_failure(shot_id, 'video', e)

    def _generate_narration(self, shot_id: str) -> dict:
        ss = self.memory.get_shot(shot_id)
        if not ss:
            return {'error': f'镜头 {shot_id} 不存在'}

        raw = getattr(ss, '_raw', {})
        narration_text = raw.get('narration', '')
        if not narration_text:
            self.memory.update_shot(shot_id, narration_path=None, status='narration_done')
            return {'shot_id': shot_id, 'status': 'narration_done', 'note': '无旁白文本，跳过'}

        lang = self.memory.config.get('language', DEFAULT_LANGUAGE)
        voice = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE])['tts_voice']
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.session_dir, f'{ts}_{shot_id}_narration.mp3')

        self.memory.record_thought('tool_call',
                                    f'调用 Edge TTS 生成 {shot_id} 旁白...')

        try:
            from services.tts_service import generate_narration
            generate_narration(narration_text, path, voice)

            eval_result = QualityEvaluator.evaluate_narration(path)
            if eval_result['pass']:
                self.memory.update_shot(shot_id, narration_path=path,
                                         status='narration_done')
                return {'shot_id': shot_id, 'status': 'narration_done'}
            else:
                self.memory.update_shot(shot_id, status='narration_failed',
                                         failure_reason=eval_result['reason'])
                return {'shot_id': shot_id, 'status': 'narration_failed'}

        except Exception as e:
            self.memory.update_shot(shot_id, status='narration_failed',
                                     failure_reason=str(e)[:200])
            return {'shot_id': shot_id, 'status': 'narration_failed',
                    'reason': str(e)[:200]}

    def _batch_generate_images(self, shot_ids: list = None) -> dict:
        if not shot_ids:
            shot_ids = [sid for sid, ss in self.memory.shots.items()
                       if ss.status == 'idle']

        if not shot_ids:
            return {'generated': 0, 'note': '所有镜头图片已就绪'}

        self.memory.record_thought('tool_call',
            f'批量生成图片，共 {len(shot_ids)} 个镜头 (5线程并行)...')

        results = {'generated': 0, 'failed': [], 'reused': 0}

        seen_locations = {}
        to_generate = []
        for sid in shot_ids:
            ss = self.memory.get_shot(sid)
            if not ss:
                continue
            raw = getattr(ss, '_raw', {})
            loc = raw.get('location', '')
            if loc and loc in seen_locations:
                lead_id = seen_locations[loc]
                lead_ss = self.memory.get_shot(lead_id)
                if lead_ss and lead_ss.image_path and os.path.exists(lead_ss.image_path):
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_path = os.path.join(self.session_dir, f'{ts}_{sid}_kf.png')
                    import shutil
                    shutil.copy2(lead_ss.image_path, new_path)
                    self.memory.update_shot(sid, image_path=new_path,
                        status='image_done', image_reused_from=lead_id)
                    results['reused'] += 1
                    continue
            if loc:
                seen_locations[loc] = sid
            to_generate.append(sid)

        if to_generate:
            with ThreadPoolExecutor(max_workers=min(len(to_generate), 5)) as ex:
                futures = {ex.submit(self._generate_image, sid): sid for sid in to_generate}
                for f in as_completed(futures):
                    sid = futures[f]
                    try:
                        result = f.result()
                        if result.get('status') == 'image_done':
                            results['generated'] += 1
                        else:
                            results['failed'].append(sid)
                    except Exception:
                        results['failed'].append(sid)

        self.memory.record_thought('tool_result',
            f'图片批量完成: 生成{results["generated"]}, '
            f'复用{results["reused"]}, 失败{len(results["failed"])}')

        return results

    def _batch_generate_videos(self, shot_ids: list = None) -> dict:
        if not shot_ids:
            shot_ids = [sid for sid, ss in self.memory.shots.items()
                       if ss.status == 'image_done']

        if not shot_ids:
            return {'generated': 0, 'note': '没有可生成视频的镜头'}

        self.memory.record_thought('tool_call',
            f'批量生成视频，共 {len(shot_ids)} 个镜头...')

        results = {'generated': 0, 'failed': []}
        with ThreadPoolExecutor(max_workers=min(len(shot_ids), 10)) as ex:
            futures = {ex.submit(self._generate_video, sid): sid for sid in shot_ids}
            for f in as_completed(futures):
                r = f.result()
                if r.get('status') == 'video_done':
                    results['generated'] += 1
                else:
                    results['failed'].append(r.get('shot_id'))

        return results

    def _compose_video(self) -> dict:
        shot_list = []
        for sid, ss in self.memory.shots.items():
            d = {'id': sid, 'video_path': ss.video_path,
                 'narration_path': ss.narration_path}
            raw = getattr(ss, '_raw', {})
            d['on_screen_text'] = raw.get('on_screen_text', '')
            d['narration'] = raw.get('narration', '')
            shot_list.append(d)

        self.memory.record_thought('tool_call', '调用 ffmpeg 合成最终视频...')

        try:
            from services.composer import compose_video
            final_path = compose_video(self.session_dir, shot_list,
                                       self.memory.config,
                                       global_tone=self.memory.emotion_arc)
            self.memory.phase = 'done'
            self.memory.record_thought('tool_result',
                f'🎬 视频合成完成: {final_path}')
            return {'status': 'done', 'video_path': final_path}
        except Exception as e:
            self.memory.record_error(f'合成失败: {e}')
            return {'status': 'failed', 'error': str(e)[:300]}

    def _check_status(self) -> dict:
        return {
            'phase': self.memory.phase,
            'total_shots': len(self.memory.shots),
            'image_done': self.memory.count_by_status('image_done'),
            'video_done': self.memory.count_by_status('video_done'),
            'image_failed': self.memory.count_by_status('image_failed'),
            'video_failed': self.memory.count_by_status('video_failed'),
            'narration_failed': self.memory.count_by_status('narration_failed'),
            'summary': self.memory.get_state_for_llm(),
        }
