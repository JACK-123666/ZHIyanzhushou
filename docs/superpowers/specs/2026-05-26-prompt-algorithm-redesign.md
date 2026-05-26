# Prompt 生成算法深度重写 — 设计规格

## 目标

基于 Seedance 2.0 和 Seedream 5.0 官方最佳实践，重写 3 个 System Prompt（BIBLE / PROMPT_GEN / 相关注入逻辑），提升视频质量、全局一致性、动作稳定性，同时控制成本（零额外 API 调用）。

## 改动范围

| 文件 | 改动 | 影响 |
|------|------|------|
| `services/llm_service.py` | 重写 `BIBLE_SYSTEM`/`BIBLE_USER`、`PROMPT_GEN_SYSTEM`/`PROMPT_GEN_USER`、`_inject_character_cards`、`_inject_master_references` | 核心 Prompt 模板和注入逻辑 |

不改 `config.py`、`app.py`、前端、composer。

---

## Section B：video_prompt 重写（最高优先级）

### B.1 新 video_prompt 格式

**从 4 段中文 80-150 字 → 5 段中文 50-80 字（更短更稳定）：**

```
[主体] 角色名 + 位置 + 姿势（从参考图出）
[动作] 单一微动作 + 幅度 + 速度 + 明确不动部分
[镜头] 一种运镜 + 节奏 + 量化幅度
[风格] 光线+色调锚点（从视觉圣经取）
[禁止] 按运镜类型动态选择的负面提示词
```

### B.2 运镜-负面词映射表

PROMPT_GEN_SYSTEM 内嵌映射表：

| 运镜 | 专属禁止词 |
|------|-----------|
| push-in / pull-out | `no jitter, no speed change, no edge wobble` |
| handheld | `no excessive shake, no motion blur, no focus drift` |
| orbit / crane | `no background warp, no perspective shift, no distortion` |
| static | `no camera movement, no frame drift, no subtle shift` |
| pan / tracking | `no vertical drift, no speed variation, no rolling shutter` |

通用禁止词（所有视频 prompt 必含）：
`no face drift, no limb warp, no texture flicker, no added objects, no color shift`

### B.3 微运动设计原则

PROMPT_GEN_SYSTEM 强调：
- 每镜只有 1 个动作 + 1 个运镜
- 动作幅度量化为百分比或距离：`抬杯约5cm` `转头约30度` `推镜2-5%`
- "几乎不动"策略——追求干净 4-8s 微动片段，不追求大幅复杂运动
- 优先 static + 主体微动（呼吸感），其次 slow push-in

---

## Section C：全局一致性增强

### C.1 BIBLE 输出模板化

BIBLE_SYSTEM 输出从自由文本改为严格结构化：

```json
{
  "global_style": "色温+主色调+光线质量（2-3句英文）",
  "characters": {
    "角色名": {
      "appearance": "枚举模板: 年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰（50-80字英文）",
      "anchor_shot": "SC01"
    }
  },
  "locations": {
    "场景名": {
      "layout": "空间大小+道具位置+标志物（30-50字英文）",
      "lighting": "主光方向+色温+光比",
      "color_palette": "3-4色 英文"
    }
  },
  "shot_connections": ["SC01→SC02: 过渡说明"]
}
```

### C.2 场景数据注入（代码级）

`generate_prompts()` 在构建 `shots_with_context` 时：
- 每镜附加其对应 location 的 `layout` / `lighting` / `color_palette`
- PROMPT_GEN_USER 指令改为："image_prompt 中场景部分从视觉圣经**逐字复制**，不得改写"

### C.3 角色外貌模板化

`character_summary` 格式从自由文本改为枚举模板：
`"年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰"`

`_inject_character_cards` 保持不变（逐字替换），但确保模板格式在 LLM 生成阶段就被遵守。

---

## Section A：image_prompt 增强

### A.1 新 image_prompt 格式

**从自由结构英文 250-400 词 → Seedream 7 段式英文 200-300 词：**

```
1. [主体] 角色身份证 + 姿势 + 位置（词序=权重，放最前）
2. [动作/姿态] 静态起始帧描述，明确"frozen / still / positioned"
3. [场景环境] 从视觉圣经逐字复制 layout + color_palette
4. [构图] camera_hint + 镜头焦距 + 景深
5. [光影氛围] 从视觉圣经逐字复制 lighting
6. [风格] style_prefix + global_style
7. [品质] 精简一行: "sharp focus, consistent character design, clean background, cinematic lighting"
```

### A.2 关键优化

- 主体放第 1 位（Seedream 词序=权重）
- 场景/光影从视觉圣经注入，不靠 LLM 现编
- 去空泛词（"high quality, detailed textures"）→ 换精确指令（"85mm lens, shallow DOF"）
- 长度 200-300 词，远低于 800 截断线

---

## 不改的部分

- `_inject_character_cards` 逻辑不变（占位符替换机制已验证有效）
- `_inject_master_references` 逻辑不变（主镜锚定已验证有效）
- `_validate_prompts` 验证维度不变（占位符残留/角色完整性/中文占比/防错词）
- `_call_llm` 重试机制不变
- 两轮调用结构不变（1 次视觉圣经 + 1 次逐镜 prompt）
- API 调用次数零增加

## 验证方式

1. `python -m py_compile services/llm_service.py`
2. 启动服务器，上传测试文档，跑完 6 步
3. 检查生成的 video_prompt 是否 ≤ 80 字、是否包含专属负面词
4. 检查生成的 image_prompt 是否 7 段式、场景是否从视觉圣经逐字复制
5. 检查角色外貌是否枚举模板格式
