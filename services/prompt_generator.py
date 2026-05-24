from config import STYLE_DESCRIPTIONS, DURATION_MAPS, NARRATOR_DESCRIPTIONS

MAX_KEY_POINTS = 8
MAX_POINTS_PER_SCENE = 2


def generate_prompt(content, video_style, video_duration, narrator):
    """根据文档内容生成 AI 视频 prompt"""
    style_desc = STYLE_DESCRIPTIONS.get(video_style, STYLE_DESCRIPTIONS['business'])
    duration_info = DURATION_MAPS.get(video_duration, DURATION_MAPS['medium'])
    narrator_desc = NARRATOR_DESCRIPTIONS.get(narrator, NARRATOR_DESCRIPTIONS['female1'])

    content_lines = content.strip().split('\n')

    structure = _analyze_document_structure(content_lines)
    document_title = structure['title']
    key_points = structure['key_points']

    selected_points = _select_content_for_duration(
        key_points, duration_info['scenes'], duration_info['words_per_scene']
    )

    scene_descriptions = _build_scene_descriptions(
        document_title, selected_points, style_desc, duration_info
    )

    return f"""【文档介绍视频生成】

视频主题：{document_title}

【场景设计】
{scene_descriptions}

【视觉风格】
{style_desc}

【配音要求】
{narrator_desc}

【技术规格】
- 总时长：{duration_info['desc']}
- 场景数量：{duration_info['scenes']}个
- 每个场景约{duration_info['seconds'] // duration_info['scenes']}秒
- 文字叠加：清晰易读，突出关键信息
- 转场效果：平滑自然的场景切换
- 背景音乐：轻柔的背景音，不干扰配音

【内容要求】
- 简洁明了，突出文档核心价值
- 每个场景聚焦一个主要观点
- 使用图表、图标等视觉元素辅助说明
- 保持一致的视觉风格和配色
- 确保信息传达清晰准确"""


def _analyze_document_structure(content_lines):
    """智能分析文档结构：提取标题、要点、摘要"""
    structure = {'title': '文档介绍', 'key_points': [], 'summary': '', 'sections': []}

    for line in content_lines:
        if line.strip() and len(line.strip()) > 5:
            structure['title'] = line.strip()
            break

    for line in content_lines:
        line = line.strip()
        if line and len(line) > 10:
            if any(marker in line[:3] for marker in ['•', '-', '*', '1.', '2.', '3.']):
                structure['key_points'].append(line)
            elif len(structure['key_points']) < MAX_KEY_POINTS:
                structure['key_points'].append(line)

    if structure['key_points']:
        structure['summary'] = ' '.join(structure['key_points'][:3])

    return structure


def _select_content_for_duration(key_points, num_scenes, words_per_scene):
    """根据视频时长选择合适的内容量"""
    if not key_points:
        return []

    selected = []
    points_per_scene = max(1, len(key_points) // num_scenes)

    for i in range(num_scenes):
        start_idx = i * points_per_scene
        end_idx = start_idx + points_per_scene
        if start_idx < len(key_points):
            scene_points = key_points[start_idx:end_idx]
            if scene_points:
                combined = ' '.join(scene_points[:MAX_POINTS_PER_SCENE])
                selected.append(combined)

    while len(selected) < num_scenes and len(selected) < len(key_points):
        selected.append(key_points[len(selected)])

    return selected[:num_scenes]


def _build_scene_descriptions(document_title, selected_points, style_desc, duration_info):
    """构建分场景描述"""
    scenes = []
    scene_duration = duration_info['seconds'] // duration_info['scenes']
    style_parts = style_desc.split('，')
    style_keyword = style_parts[0] if style_parts else '专业'
    font_keyword = style_parts[1] if len(style_parts) > 1 else '专业'

    # 场景1：开场
    scenes.append(f"""场景1（开场，{scene_duration}秒）：
- 画面：文档标题"{document_title}"以大字体居中显示
- 背景：{style_keyword}的渐变背景
- 动画：标题从下方淡入，配合光效
- 文字：标题文字清晰，使用{font_keyword}字体
- 配音：介绍文档主题和目的（约{scene_duration * 3}字）""")

    # 场景2-N：核心内容
    for i, point in enumerate(selected_points, 2):
        if i > duration_info['scenes']:
            break
        scenes.append(f"""场景{i}（内容展示，{scene_duration}秒）：
- 画面：展示要点内容"{point[:30]}..."
- 布局：左侧文字，右侧配图或图标
- 动画：文字逐行显示，配合图标动画
- 颜色：使用{style_keyword}配色
- 配音：详细说明要点内容（约{scene_duration * 3}字）""")

    # 结尾场景
    scenes.append(f"""场景{len(scenes) + 1}（结尾，{scene_duration}秒）：
- 画面：文档标题再次出现，下方显示"谢谢观看"
- 背景：与开场呼应的渐变效果
- 动画：标题和文字同时淡入
- 文字：简洁明了，突出重点
- 配音：总结文档价值，感谢观看（约{scene_duration * 3}字）""")

    return '\n\n'.join(scenes)
