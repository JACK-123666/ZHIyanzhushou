import json


TAXONOMY = [
    {
        "dimension": "时间",
        "categories": [
            {
                "category": "压缩",
                "subcategories": [
                    {
                        "sub": "跳切",
                        "detail": "省略中间过程，在同一主体连续动作中切掉中间帧，产生跳跃感的时间压缩手法。常用于表现时间流逝或提升节奏。",
                        "keywords": ["jump cut", "jumpcut", "跳切", "skip cut"]
                    },
                    {
                        "sub": "蒙太奇",
                        "detail": "将多个短镜头快速组接，压缩长时间跨度的关键瞬间，形成信息密度极高的叙事段落。常用于转场、训练、成长等过程展示。",
                        "keywords": ["montage", "蒙太奇", "sequence", "assembly edit"]
                    },
                    {
                        "sub": "省略",
                        "detail": "直接跳过部分时间段（省略历时），让观众自行脑补中间过程。常用于日常行为、旅途等非关键情节的裁剪。",
                        "keywords": ["ellipsis", "time skip", "省略", "temporal skip"]
                    },
                ]
            },
            {
                "category": "延长",
                "subcategories": [
                    {
                        "sub": "慢动作",
                        "detail": "通过高帧率拍摄后以正常帧率播放，放慢动作以强调关键瞬间、增强戏剧张力或突出美感。",
                        "keywords": ["slow motion", "slow-mo", "慢动作", "slo-mo", "slow down"]
                    },
                    {
                        "sub": "多角度",
                        "detail": "同一动作从多个机位重复展示，延长主观时间，常用于体育回放、动作场景高潮瞬间。",
                        "keywords": ["multi-angle", "multi angle", "多角度", "multi-cam"]
                    },
                    {
                        "sub": "插入镜头",
                        "detail": "在主镜头之间插入短镜头（如环境、细节、反应），延长时间感受的同时丰富叙事层次。",
                        "keywords": ["insert shot", "cutaway", "插入", "cut-in"]
                    },
                ]
            },
            {
                "category": "颠倒",
                "subcategories": [
                    {
                        "sub": "闪回",
                        "detail": "突然切入过去场景，打断当前时间线。常用于揭示人物过往、交代动机或制造悬念。",
                        "keywords": ["flashback", "闪回", "回忆"]
                    },
                    {
                        "sub": "闪前",
                        "detail": "突然切入未来场景（预演/想象/预示），提前揭示将发生的事件或结果，制造期待感。",
                        "keywords": ["flashforward", "flash forward", "闪前", "预演"]
                    },
                    {
                        "sub": "非线性叙事",
                        "detail": "完全打破时间顺序，按主题、情感逻辑而非时间逻辑组织镜头。常见于悬疑、文艺片、实验影像。",
                        "keywords": ["nonlinear", "non-linear", "非线性", "fragmented"]
                    },
                ]
            },
            {
                "category": "并行",
                "subcategories": [
                    {
                        "sub": "平行剪辑",
                        "detail": "交替展示同时发生在不同空间的两个（或多个）事件，暗示它们之间存在某种关联。",
                        "keywords": ["parallel editing", "parallel", "平行", "cross edit"]
                    },
                    {
                        "sub": "交叉剪辑",
                        "detail": "两组镜头来回快速切换，节奏越切越快最终汇合。用于制造紧张感，典型手法如「最后一分钟营救」。",
                        "keywords": ["cross cutting", "cross-cutting", "交叉", "intercut"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "空间",
        "categories": [
            {
                "category": "连贯剪辑",
                "subcategories": [
                    {
                        "sub": "180度轴线",
                        "detail": "拍摄时所有机位保持在人物或动作的同一侧（180度半圆内），确保银幕方向一致、空间关系清晰。",
                        "keywords": ["180 degree", "180°", "axis line", "轴线"]
                    },
                    {
                        "sub": "30度原则",
                        "detail": "相邻两个景别的机位角度变化应大于30度，避免画面看起来像「跳了一下」而非有意义的切换。",
                        "keywords": ["30 degree", "30° rule", "角度变化"]
                    },
                    {
                        "sub": "匹配剪辑",
                        "detail": "前后镜头在构图、形状、动作或颜色上高度相似，切换流畅自然。包括图形匹配、动作匹配等。",
                        "keywords": ["match cut", "match-cut", "匹配剪辑", "graphic match"]
                    },
                    {
                        "sub": "正反打",
                        "detail": "两人对话时交替切人物面部镜头（过肩/非过肩），构建稳定的对话空间关系。常见于访谈、剧情对话。",
                        "keywords": ["shot reverse shot", "shot-reverse-shot", "正反打", "OTS"]
                    },
                ]
            },
            {
                "category": "解构剪辑",
                "subcategories": [
                    {
                        "sub": "越轴",
                        "detail": "故意跨越180度轴线拍摄和剪辑，打破空间连续性。用于表现混乱、紧张、角色内心动荡或有意制造观众不适。",
                        "keywords": ["cross axis", "越轴", "跳轴", "axis break"]
                    },
                    {
                        "sub": "碎片化空间",
                        "detail": "故意打乱空间方向感（跳跃方向不一致、景别混乱），不让观众建立清晰的空间地图，营造迷失/焦虑感。",
                        "keywords": ["fragmented space", "碎片化", "disorienting", "空间混乱"]
                    },
                ]
            },
            {
                "category": "空间转场",
                "subcategories": [
                    {
                        "sub": "淡入淡出",
                        "detail": "画面逐渐变亮（淡入）或变暗（淡出）过渡到下一个场景。常用于章节分隔、时间流逝表示。",
                        "keywords": ["fade in", "fade out", "淡入", "淡出", "渐显", "渐隐"]
                    },
                    {
                        "sub": "叠化",
                        "detail": "前一个镜头逐渐透明化露出下一个镜头，两画面短暂重叠。常用于表现时间流逝、回忆、梦境过渡。",
                        "keywords": ["dissolve", "叠化", "溶接", "cross dissolve"]
                    },
                    {
                        "sub": "相似体转场",
                        "detail": "两个完全不同场景中以形状相似的主体连接过渡（如圆形物体→圆形物体），视觉巧妙流畅。",
                        "keywords": ["match dissolve", "shape match", "相似体", "形体匹配"]
                    },
                    {
                        "sub": "动作转场",
                        "detail": "利用人物/物体的延续动作连接两个不同空间（如人物向右走出画→从另一场景左侧入画）。",
                        "keywords": ["action match", "动作匹配", "动作转场", "whip pan"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "叙事",
        "categories": [
            {
                "category": "因果剪辑",
                "subcategories": [
                    {
                        "sub": "事件逻辑",
                        "detail": "以事件之间的因果关系（原因→结果）驱动剪辑决策，确保叙事因果链清晰完整。连续剪辑派的核心理念。",
                        "keywords": ["cause effect", "因果", "逻辑剪辑", "continuity"]
                    },
                ]
            },
            {
                "category": "动机剪辑",
                "subcategories": [
                    {
                        "sub": "视觉驱动",
                        "detail": "由画内视觉元素（眼神方向、动作指向、画面焦点）触发剪辑。如人物望向画外的下一个场景，观众自然期待切过去。",
                        "keywords": ["visual driven", "视觉驱动", "eyeline match"]
                    },
                    {
                        "sub": "声音驱动",
                        "detail": "由声音（画外音、对白、音效、音乐）触发剪辑动机。如听到敲门声切到门口，或对白提及某物时切过去。",
                        "keywords": ["sound driven", "声音驱动", "audio lead"]
                    },
                    {
                        "sub": "情绪驱动",
                        "detail": "以角色或场景的情绪节奏为剪辑依据，而非严格执行叙事逻辑。情感共鸣优先于因果连贯。",
                        "keywords": ["emotion driven", "情绪驱动", "emotional cut"]
                    },
                ]
            },
            {
                "category": "视点剪辑",
                "subcategories": [
                    {
                        "sub": "客观视点",
                        "detail": "摄像机像「隐藏的观察者」一样记录场景，观众看到的是全知视角，角色不直接面向镜头。",
                        "keywords": ["objective", "客观", "omniscient"]
                    },
                    {
                        "sub": "主观POV",
                        "detail": "镜头模拟某个人物的视角（第一人称），观众看到该人物所看到的画面。增强代入感和沉浸体验。",
                        "keywords": ["POV", "point of view", "主观", "第一人称"]
                    },
                    {
                        "sub": "上帝视角",
                        "detail": "高角度俯瞰或航拍大全景，镜头完全脱离任何具体角色的视角限制，呈现出「上帝俯瞰万物」的宏观视点。",
                        "keywords": ["god view", "上帝视角", "aerial", "俯瞰"]
                    },
                ]
            },
            {
                "category": "悬念剪辑",
                "subcategories": [
                    {
                        "sub": "延迟揭示",
                        "detail": "故意不在第一时间展示关键信息，通过延长揭秘过程制造悬念。如先拍角色惊恐表情，延迟切到他所看到的恐怖画面。",
                        "keywords": ["delayed reveal", "延迟揭示", "slow reveal"]
                    },
                    {
                        "sub": "信息差",
                        "detail": "让观众知道比角色更多的信息（戏剧反讽），或比角色更少的信息（神秘感），通过信息不对称制造张力。",
                        "keywords": ["dramatic irony", "信息差", "观众知道更多"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "节奏",
        "categories": [
            {
                "category": "快剪",
                "subcategories": [
                    {
                        "sub": "紧张激烈",
                        "detail": "极短镜头快速交替切换（0.3-1秒），制造紧张、急迫、高强度情绪。常见于预告片、动作高潮、打斗场景。",
                        "keywords": ["fast cutting", "fast-paced", "快剪", "rapid", "intense"]
                    },
                    {
                        "sub": "动作快剪",
                        "detail": "专门针对动作场景的快速剪辑，每个打击/跳跃/撞击对应一个镜头切换，强化动作冲击力。",
                        "keywords": ["action cutting", "动作剪辑", "fight scene", "追逐"]
                    },
                ]
            },
            {
                "category": "慢剪",
                "subcategories": [
                    {
                        "sub": "舒缓长镜",
                        "detail": "使用较长时长镜头（3-30秒或更长），少切少跳，让观众有足够时间沉浸于画面。营造宁静、诗意或沉思氛围。",
                        "keywords": ["long take", "长镜头", "slow pace", "舒缓", "lingering"]
                    },
                    {
                        "sub": "沉重凝滞",
                        "detail": "通过静态构图和极少的剪辑（甚至固定机位一动不动），传达沉重、压抑、停滞不前的情感状态。",
                        "keywords": ["heavy", "weight", "沉重", "stillness", "静态"]
                    },
                ]
            },
            {
                "category": "节奏变化",
                "subcategories": [
                    {
                        "sub": "加速",
                        "detail": "镜头切换速率逐渐加快，节奏由慢到快的递进式变化。常见于情绪/情节从平静过渡到高潮的段落。",
                        "keywords": ["accelerating", "加速", "渐快", "building"]
                    },
                    {
                        "sub": "减速",
                        "detail": "镜头切换速率逐渐放慢，节奏由快到慢的递减式变化。常用于高潮之后回到平静、或故事结尾的收束。",
                        "keywords": ["decelerating", "减速", "渐慢", "winding down"]
                    },
                    {
                        "sub": "停顿对比",
                        "detail": "在快速剪辑中突然插入一个静止帧或长停顿，形成节奏断点以放大情感冲击。静帧/停顿产生强烈对比效果。",
                        "keywords": ["pause", "停顿", "freeze frame", "静帧", "beat"]
                    },
                ]
            },
            {
                "category": "音乐节拍",
                "subcategories": [
                    {
                        "sub": "节拍精准对齐",
                        "detail": "画面切换点精确对齐音乐节拍（鼓点、贝斯、旋律变化点），形成视听同步的节奏快感。常见于MV、音乐类剪辑。",
                        "keywords": ["beat sync", "节拍对齐", "cut to beat", "rhythm edit"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "视听",
        "categories": [
            {
                "category": "声画关系",
                "subcategories": [
                    {
                        "sub": "声画同步",
                        "detail": "声音与画面严格对应（如人物张嘴说话音频同步、物体碰撞声音同步），是最基本、最自然的视听关系。",
                        "keywords": ["sync sound", "声画同步", "diegetic", "lip sync"]
                    },
                    {
                        "sub": "声画分立",
                        "detail": "声音来源不在当前画面中（画外音、旁白、环境音来自下一场景），声音与画面在同一时空但不同源。",
                        "keywords": ["sound separation", "声画分立", "off-screen sound"]
                    },
                    {
                        "sub": "声画对位",
                        "detail": "声音与画面存在刻意的不协调/矛盾关系（如欢乐画面配悲伤音乐），通过反差创造深层次含义或讽刺效果。",
                        "keywords": ["counterpoint", "对位", "讽刺", "contrast sound"]
                    },
                ]
            },
            {
                "category": "声音转场",
                "subcategories": [
                    {
                        "sub": "先声夺人",
                        "detail": "下一场景的声音提前进入（在画面切换前已可听到），以声音引领视觉过渡。专业的J-Cut手法。",
                        "keywords": ["sound advance", "先声", "J cut", "audio lead"]
                    },
                    {
                        "sub": "声音延续",
                        "detail": "当前场景的声音延续到下一场景画面中（画面已切换声音还在），营造画面和声音的短暂分离感。专业的L-Cut手法。",
                        "keywords": ["sound linger", "声音延续", "L cut", "audio tail"]
                    },
                    {
                        "sub": "声音桥",
                        "detail": "通过一段连续的声音（音乐、环境音、对白）连接前后两个不同场景的画面，起到桥梁式的平滑过渡作用。",
                        "keywords": ["sound bridge", "声音桥", "audio bridge"]
                    },
                ]
            },
            {
                "category": "画面匹配",
                "subcategories": [
                    {
                        "sub": "色彩连贯",
                        "detail": "前后镜头的色调、色温、饱和度保持视觉一致性，避免色彩跳变。常用于营造统一的情绪或特定调色风格。",
                        "keywords": ["color match", "色彩匹配", "color continuity"]
                    },
                    {
                        "sub": "光影连贯",
                        "detail": "前后镜头的光源方向、光比、光色保持一致。违反光向连贯会让观众潜意识感到不安或断裂。",
                        "keywords": ["lighting match", "光影匹配"]
                    },
                    {
                        "sub": "构图对比",
                        "detail": "利用前后镜头在构图上的强烈差异（如对称→不对称、拥挤→空旷）制造视觉冲击和叙事含义。",
                        "keywords": ["composition contrast", "构图对比"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "表现",
        "categories": [
            {
                "category": "表现蒙太奇",
                "subcategories": [
                    {
                        "sub": "对比蒙太奇",
                        "detail": "将内容/画面/情绪截然相反的两个镜头并置，通过对比产生超越单个镜头的第三层含义。如贫→富、生→死。",
                        "keywords": ["contrast montage", "对比", "juxtaposition"]
                    },
                    {
                        "sub": "隐喻蒙太奇",
                        "detail": "借助某一事物/画面来暗示另一事物，隐藏的比喻关系通过镜头组接体现。如枯树→老人，浪潮→激情。",
                        "keywords": ["metaphor montage", "隐喻", "symbolic"]
                    },
                    {
                        "sub": "象征蒙太奇",
                        "detail": "通过特定的视觉符号/元素（如鸽子、十字架、红旗）反复出现，赋予片段超出画面本身的象征意义。",
                        "keywords": ["symbol montage", "象征", "symbolism"]
                    },
                    {
                        "sub": "重复蒙太奇",
                        "detail": "同一镜头/同一构图的镜头间隔性反复出现，形成节奏性回响。用于强化主题、建立母题、暗示命运循环。",
                        "keywords": ["repetition", "重复", "recurring", "motif"]
                    },
                ]
            },
            {
                "category": "情绪剪辑",
                "subcategories": [
                    {
                        "sub": "特写放大",
                        "detail": "在情感关键时刻切入人物面部特写或手部细节，放大内在情绪，迫使观众近距离「看见」角色的感受。",
                        "keywords": ["close-up emotion", "特写", "表情", "reaction shot"]
                    },
                    {
                        "sub": "空镜抒情",
                        "detail": "在情感高潮后切入无人物的自然/环境空镜头，给观众留出「情感呼吸」的空间，让情绪沉淀和发酵。",
                        "keywords": ["establishing shot emotion", "空镜头", "景观抒情", "breathing room"]
                    },
                ]
            },
        ]
    },
    {
        "dimension": "技术",
        "categories": [
            {
                "category": "无缝转场",
                "subcategories": [
                    {
                        "sub": "遮挡转场",
                        "detail": "利用前景物体（行人、墙壁、树木、背包等）短暂遮挡画面，在这个瞬间切换到下一场景，观众几乎察觉不到。",
                        "keywords": ["wipe transition", "遮挡", "object wipe"]
                    },
                    {
                        "sub": "运动模糊转场",
                        "detail": "利用摄像机快速摇移/旋转产生的运动模糊作为切换点，模糊中自然过渡到新场景。Vlog和动感视频常用手法。",
                        "keywords": ["motion blur transition", "运动模糊", "smear"]
                    },
                    {
                        "sub": "数字特效转场",
                        "detail": "使用后期特效制作的转场（变形/粒子/光效/故障风等），形成高度风格化的视觉过渡。适合炫酷、科技感内容。",
                        "keywords": ["digital transition", "数字转场", "morph", "glitch"]
                    },
                ]
            },
            {
                "category": "数字合成",
                "subcategories": [
                    {
                        "sub": "分屏",
                        "detail": "同一画面同时显示两个或多个独立视频画面，各自占据屏幕的一部分。适合多线并行的叙事或对比展示。",
                        "keywords": ["split screen", "分屏", "split-screen"]
                    },
                    {
                        "sub": "叠印",
                        "detail": "一个画面上叠加另一层半透明画面（双重曝光效果），两层同时可见。营造梦幻、回忆、关联的视觉效果。",
                        "keywords": ["superimpose", "叠印", "double exposure", "双重曝光"]
                    },
                    {
                        "sub": "绿幕抠像",
                        "detail": "利用色键技术去除绿色/蓝色背景替换为任何画面，实现人物与虚拟/合成背景的融合。影视工业基础技术。",
                        "keywords": ["green screen", "chroma key", "绿幕", "抠像", "keying"]
                    },
                ]
            },
            {
                "category": "AI辅助",
                "subcategories": [
                    {
                        "sub": "自动剪辑",
                        "detail": "使用AI技术根据音频节拍、画面内容、预设风格自动完成粗剪。提升剪辑效率，保持风格一致性。",
                        "keywords": ["AI editing", "auto edit", "自动剪辑"]
                    },
                    {
                        "sub": "智能转场",
                        "detail": "AI自动识别最优切换点并生成平滑的视觉效果转场。分析画面内容以选择最佳转场类型。",
                        "keywords": ["AI transition", "智能转场"]
                    },
                    {
                        "sub": "画质修复",
                        "detail": "利用深度学习超分辨率技术对低清/老画面进行画质提升，包括去噪、锐化、帧率提升、分辨率放大。",
                        "keywords": ["upscale", "超分", "画质修复", "enhance"]
                    },
                ]
            },
        ]
    },
]


def get_all_taxonomy_entries():
    """将7维分类树展开为扁平行列表，每行为(dimension, category, subcategory, detail, keywords_json, weight)"""
    entries = []
    for dim in TAXONOMY:
        dimension = dim["dimension"]
        for cat in dim["categories"]:
            category = cat["category"]
            for sub_entry in cat["subcategories"]:
                entries.append({
                    "dimension": dimension,
                    "category": category,
                    "subcategory": sub_entry["sub"],
                    "detail": sub_entry.get("detail", ""),
                    "keywords": json.dumps(sub_entry["keywords"], ensure_ascii=False),
                    "weight": sub_entry.get("weight", 1.00),
                })
    return entries


def seed_taxonomy(db_config):
    """将分类体系预填到 MySQL technique_taxonomy 表中（幂等，已存在则跳过）"""
    import pymysql

    entries = get_all_taxonomy_entries()
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    try:
        # Ensure the table exists (schema.sql may have been run by docker-entrypoint-initdb)
        for entry in entries:
            # Check if this taxonomy node already exists by unique key
            cursor.execute(
                "SELECT id FROM technique_taxonomy WHERE dimension=%s AND category=%s AND subcategory=%s",
                (entry["dimension"], entry["category"], entry["subcategory"])
            )
            existing = cursor.fetchone()
            if existing:
                skipped += 1
                continue

            # Insert new taxonomy entry
            cursor.execute(
                """INSERT INTO technique_taxonomy (dimension, category, subcategory, detail, keywords, weight)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (entry["dimension"], entry["category"], entry["subcategory"],
                 entry["detail"], entry["keywords"], entry["weight"])
            )
            inserted += 1

        conn.commit()
        print(f"Taxonomy seeding complete: {inserted} inserted, {skipped} skipped (already exist)")

    except Exception as e:
        conn.rollback()
        print(f"Taxonomy seeding failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Allow running directly to seed taxonomy into a running MySQL container
    from clip_trends.config import MYSQL_CONFIG

    seed_taxonomy(MYSQL_CONFIG)
