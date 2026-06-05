/**
 * 智演助手 — OPC 路演PPT
 * 主题: 1人 + AI = 一家动画工作室
 * 赛制: 5分钟 (3min项目 + 1min演示 + 1min未来)
 */
const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "智演助手";
pres.title = "智演助手 — 1人+AI=动画工作室";

const C = {
  black: "0A0A0A",
  dark:  "1A1A2E",
  gold:  "E8B830",   // 金色-OPC主题
  goldL: "F5D061",
  white: "FFFFFF",
  gray:  "888899",
  light: "F0F0F5",
  red:   "E05555",
  teal:  "2EC4B6",
};
const T = 12;

function darkSlide(s, num) {
  s.background = { color: C.black };
  s.addText(`${num} / ${T}`, { x: 8.8, y: 5.25, w: 1, h: 0.25, fontSize: 8, color: C.gray, align: "right" });
}

// ===== SLIDE 1: 封面 =====
{
  const s = pres.addSlide();
  s.background = { color: C.black };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.gold } });
  s.addText("智演助手", { x: 0.8, y: 1.2, w: 8.4, h: 1.2, fontSize: 52, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 2.45, w: 1.0, h: 0.04, fill: { color: C.gold } });
  s.addText("1 人  +  AI  =  一家动画工作室", { x: 0.8, y: 2.8, w: 8.4, h: 0.6, fontSize: 22, fontFace: "Arial", color: C.gold, margin: 0 });
  s.addText("OPC 创业大赛", { x: 0.8, y: 4.6, w: 8.4, h: 0.4, fontSize: 12, fontFace: "Arial", color: C.gray, margin: 0 });
  darkSlide(s, 1);
}

// ===== SLIDE 2: 痛点——做一个视频要多少人 =====
{
  const s = pres.addSlide();
  darkSlide(s, 2);
  s.addText("一段 1 分钟动画视频，需要几个人？", { x: 0.8, y: 0.6, w: 8.4, h: 0.7, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  const roles = ["分镜师", "原画师", "动画师", "配音师", "剪辑师"];
  roles.forEach((r, i) => {
    const x = 0.5 + i * 1.9;
    s.addShape(pres.shapes.OVAL, { x: x + 0.45, y: 2.0, w: 1.0, h: 1.0, fill: { color: C.dark } });
    s.addShape(pres.shapes.OVAL, { x: x + 0.45, y: 2.0, w: 1.0, h: 1.0, line: { color: C.gold, width: 2 } });
    s.addText(r, { x: x + 0.45, y: 2.0, w: 1.0, h: 1.0, fontSize: 14, fontFace: "Arial", color: C.white, align: "center", valign: "middle", margin: 0 });
  });
  s.addText("5 个人 · 5 天 · ¥12,000", { x: 0.8, y: 3.5, w: 8.4, h: 0.6, fontSize: 20, fontFace: "Arial", color: C.gold, align: "center", margin: 0 });
  s.addText("如果只有一个人，AI 能不能把另外四个人的活都干了？", { x: 0.8, y: 4.5, w: 8.4, h: 0.5, fontSize: 14, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
}

// ===== SLIDE 3: 答案 =====
{
  const s = pres.addSlide();
  darkSlide(s, 3);
  s.addText("能。", { x: 0.8, y: 0.6, w: 8.4, h: 0.9, fontSize: 48, fontFace: "Arial", color: C.gold, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.5, w: 0.8, h: 0.04, fill: { color: C.gold } });
  const steps = ["上传文档\n(.docx/.txt)", "AI 分镜设计\nDeepSeek V4", "关键帧生成\nSeedream", "视频生成\nSeedance", "语音合成\nEdge TTS", "合成输出\nffmpeg"];
  steps.forEach((st, i) => {
    const x = 0.3 + i * 1.6;
    s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 2.2, w: 0.8, h: 0.8, fill: { color: C.gold } });
    s.addText(String(i + 1), { x: x + 0.25, y: 2.2, w: 0.8, h: 0.8, fontSize: 26, fontFace: "Arial", color: C.black, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText(st, { x: x - 0.1, y: 3.15, w: 1.5, h: 0.55, fontSize: 9, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
  });
  s.addText("6 步全自动 · 十几分钟 · ¥25", { x: 0.8, y: 4.2, w: 8.4, h: 0.5, fontSize: 18, fontFace: "Arial", color: C.white, align: "center", margin: 0 });
}

// ===== SLIDE 4: 演示 =====
{
  const s = pres.addSlide();
  darkSlide(s, 4);
  s.addText("产品演示", { x: 0.8, y: 0.4, w: 8.4, h: 0.6, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 0.95, w: 0.8, h: 0.04, fill: { color: C.gold } });

  const points = [
    { t: "双模式", d: "Pro 模式手动精细控制 / 全自动模式一键出片" },
    { t: "全自动", d: "只选总时长，AI 自主决定镜头/风格/运镜/灯光" },
    { t: "进度可视化", d: "6 步流水线实时反馈，多线程并行（5+10）" },
    { t: "多语言", d: "中英日韩 4 语言，UI + 视频产出全覆盖" },
  ];
  points.forEach((p, i) => {
    const y = 1.5 + i * 0.9;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 8.4, h: 0.75, fill: { color: C.dark } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 0.06, h: 0.75, fill: { color: C.gold } });
    s.addText(p.t, { x: 1.2, y: y + 0.08, w: 1.5, h: 0.3, fontSize: 16, fontFace: "Arial", color: C.gold, bold: true, margin: 0 });
    s.addText(p.d, { x: 1.2, y: y + 0.4, w: 7.8, h: 0.3, fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0 });
  });
}

// ===== SLIDE 5: AI 替我干了什么 =====
{
  const s = pres.addSlide();
  darkSlide(s, 5);
  s.addText("AI 到底替我干了什么？", { x: 0.8, y: 0.6, w: 8.4, h: 0.7, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  const rows = [
    ["分镜师", "DeepSeek V4 Pro", "通读文档→设计镜头/景别/运镜/灯光"],
    ["原画师", "Seedream 5.0 Lite", "文字→关键帧图片，5线程并行"],
    ["动画师", "Seedance 2.0 Fast", "图片→动态视频，10线程并行"],
    ["配音师", "Edge TTS", "中文语音合成，免费，4语言可选"],
    ["剪辑师", "ffmpeg", "字幕+混音+转场+合成"],
  ];
  rows.forEach((r, i) => {
    const y = 1.7 + i * 0.7;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 8.4, h: 0.6, fill: { color: C.dark } });
    s.addText(r[0], { x: 0.8, y: y + 0.05, w: 1.8, h: 0.5, fontSize: 15, fontFace: "Arial", color: C.gold, bold: true, align: "center", valign: "middle", margin: 0 });
    s.addText("→", { x: 2.6, y: y + 0.05, w: 0.4, h: 0.5, fontSize: 16, fontFace: "Arial", color: C.white, align: "center", valign: "middle", margin: 0 });
    s.addText(r[1], { x: 3.1, y: y + 0.05, w: 2.2, h: 0.5, fontSize: 13, fontFace: "Arial", color: C.white, valign: "middle", margin: 0 });
    s.addText(r[2], { x: 5.4, y: y + 0.05, w: 3.6, h: 0.5, fontSize: 11, fontFace: "Arial", color: C.gray, valign: "middle", margin: 0 });
  });
}

// ===== SLIDE 6: 核心壁垒 =====
{
  const s = pres.addSlide();
  darkSlide(s, 6);
  s.addText("如果 AI 生成的每个镜头里角色都不一样？", { x: 0.8, y: 0.4, w: 8.4, h: 0.7, fontSize: 22, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 1.1, w: 8.4, h: 0.04, fill: { color: C.red } });

  // Left - problem
  s.addText("传统 LLM 记忆", { x: 0.8, y: 1.5, w: 3.8, h: 0.4, fontSize: 14, fontFace: "Arial", color: C.red, bold: true, align: "center", margin: 0 });
  s.addText("镜头1: 白色衬衫\n镜头2: 浅色上衣 ← 忘了\n镜头3: ???\n\n12 个镜头 = 12 个不同的角色", { x: 0.8, y: 2.0, w: 3.8, h: 1.8, fontSize: 12, fontFace: "Arial", color: C.gray, align: "center", lineSpacingMultiple: 1.4, margin: 0 });

  // Divider
  s.addShape(pres.shapes.RECTANGLE, { x: 4.9, y: 1.5, w: 0.2, h: 2.5, fill: { color: C.gold } });

  // Right - solution
  s.addText("我们的方案", { x: 5.4, y: 1.5, w: 3.8, h: 0.4, fontSize: 14, fontFace: "Arial", color: C.gold, bold: true, align: "center", margin: 0 });
  s.addText("镜头1: {CHAR:张三}\n镜头2: {CHAR:张三}\n镜头12: {CHAR:张三}\n↓ Python 逐字注入\n12个镜头 = 100% 一致", { x: 5.4, y: 2.0, w: 3.8, h: 1.8, fontSize: 12, fontFace: "Arial", color: C.gray, align: "center", lineSpacingMultiple: 1.4, margin: 0 });

  s.addText("{CHAR} 占位符替代 LLM 记忆 · 代码保证逐字一致 · 零额外 API · Sora/Runway 未解决", { x: 0.8, y: 4.5, w: 8.4, h: 0.4, fontSize: 13, fontFace: "Arial", color: C.gold, align: "center", margin: 0 });
}

// ===== SLIDE 7: 竞品 =====
{
  const s = pres.addSlide();
  darkSlide(s, 7);
  s.addText("为什么不是别人？", { x: 0.8, y: 0.4, w: 8.4, h: 0.6, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 0.95, w: 0.8, h: 0.04, fill: { color: C.gold } });
  const cols = ["", "MoneyPrinter", "Runway / Sora", "智演助手"];
  const rows = [["视频来源", "网上搜素材拼", "AI生成/无角色", "AI生成/角色一致"], ["角色系统", "无", "需手动参考图", "{CHAR}占位符 100%"], ["成本/分钟", "免费+自备API", "$20-50", "¥25"], ["全自动", "需写脚本", "需逐段描述", "文档→一键出片"]];
  const colW = [1.5, 2.2, 2.2, 2.5];
  let y = 1.3;
  [cols].concat(rows).forEach((row, ri) => {
    let x = 0.8;
    row.forEach((cell, ci) => {
      s.addShape(pres.shapes.RECTANGLE, { x, y, w: colW[ci], h: 0.42, fill: { color: ri === 0 ? C.gold : (ri % 2 ? C.dark : C.black) } });
      s.addText(cell, { x: x + 0.1, y, w: colW[ci] - 0.2, h: 0.42, fontSize: 10, fontFace: "Arial", color: ri === 0 ? C.black : (ci === 3 ? C.gold : C.gray), bold: ci === 3 || ri === 0, valign: "middle", margin: 0 });
      x += colW[ci];
    });
    y += 0.45;
  });
}

// ===== SLIDE 8: 数据验证 =====
{
  const s = pres.addSlide();
  darkSlide(s, 8);
  s.addText("不是概念，已经跑起来了", { x: 0.8, y: 0.6, w: 8.4, h: 0.7, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  const nums = [
    { n: "¥25", l: "1分钟视频成本" },
    { n: "400x", l: "成本优势 vs 人工" },
    { n: "100%", l: "角色外貌一致率" },
    { n: "4", l: "语言支持" },
  ];
  nums.forEach((o, i) => {
    const x = 0.3 + i * 2.4;
    s.addText(o.n, { x, y: 2.2, w: 2.2, h: 0.8, fontSize: 40, fontFace: "Arial", color: C.gold, bold: true, align: "center", margin: 0 });
    s.addText(o.l, { x, y: 3.1, w: 2.2, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
  });
  s.addText("已完成 20+ 次全流程测试 · 支持 Docker 一键部署 · 日/英/韩 多语言", { x: 0.8, y: 4.2, w: 8.4, h: 0.4, fontSize: 14, fontFace: "Arial", color: C.white, align: "center", margin: 0 });
}

// ===== SLIDE 9: 商业模式 =====
{
  const s = pres.addSlide();
  darkSlide(s, 9);
  s.addText("怎么赚钱", { x: 0.8, y: 0.4, w: 8.4, h: 0.6, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 0.95, w: 0.8, h: 0.04, fill: { color: C.gold } });
  const models = [
    { t: "SaaS 订阅", d: "基础免费 · Pro ¥99/月 · 企业 ¥499/月", c: C.gold },
    { t: "API 分成", d: "开放 API 给第三方平台 · 按次计费 ¥5-15", c: C.white },
    { t: "增值服务", d: "角色定制 ¥2000 · 企业模板 ¥5000 · 后期精修", c: C.gray },
  ];
  models.forEach((m, i) => {
    const y = 1.5 + i * 1.3;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 8.4, h: 1.1, fill: { color: C.dark } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y, w: 0.06, h: 1.1, fill: { color: m.c } });
    s.addText(m.t, { x: 1.2, y: y + 0.1, w: 2.0, h: 0.35, fontSize: 18, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(m.d, { x: 1.2, y: y + 0.5, w: 7.8, h: 0.4, fontSize: 13, fontFace: "Arial", color: C.gray, margin: 0 });
  });
}

// ===== SLIDE 10: 路线图 =====
{
  const s = pres.addSlide();
  darkSlide(s, 10);
  s.addText("下一步", { x: 0.8, y: 0.4, w: 8.4, h: 0.6, fontSize: 28, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 0.95, w: 0.8, h: 0.04, fill: { color: C.gold } });
  const phases = [
    { t: "打磨期", time: "2025 Q3-Q4", items: "多语言 · Docker · BGM\nPro模式 · 安全加固" },
    { t: "商业化", time: "2026 Q1-Q2", items: "SaaS 订阅上线\nAPI 开放平台\n企业定制服务" },
    { t: "规模化", time: "2026 Q3-Q4", items: "移动端适配\n实时协作\n1000+ 企业客户" },
  ];
  phases.forEach((p, i) => {
    const x = 0.5 + i * 3.2;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w: 2.8, h: 3.5, fill: { color: C.dark } });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w: 2.8, h: 0.06, fill: { color: C.gold } });
    s.addText(p.t, { x: x + 0.2, y: 1.8, w: 2.4, h: 0.4, fontSize: 20, fontFace: "Arial", color: C.white, bold: true, margin: 0 });
    s.addText(p.time, { x: x + 0.2, y: 2.2, w: 2.4, h: 0.3, fontSize: 12, fontFace: "Arial", color: C.gold, margin: 0 });
    s.addText(p.items, { x: x + 0.2, y: 2.8, w: 2.4, h: 1.5, fontSize: 13, fontFace: "Arial", color: C.gray, lineSpacingMultiple: 1.5, margin: 0 });
  });
}

// ===== SLIDE 11: OPC 升华 =====
{
  const s = pres.addSlide();
  darkSlide(s, 11);
  s.addText("1 人", { x: 0.8, y: 1.0, w: 8.4, h: 1.2, fontSize: 72, fontFace: "Arial", color: C.gold, bold: true, align: "center", margin: 0 });
  s.addText("+", { x: 0.8, y: 2.2, w: 8.4, h: 0.8, fontSize: 40, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
  s.addText("AI", { x: 0.8, y: 3.0, w: 8.4, h: 1.2, fontSize: 72, fontFace: "Arial", color: C.white, bold: true, align: "center", margin: 0 });
  s.addText("=  一家动画工作室", { x: 0.8, y: 4.2, w: 8.4, h: 0.6, fontSize: 20, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
}
// Note: the function is called darkSlide but we need page numbers - skip on this slide

// ===== SLIDE 12: 致谢 =====
{
  const s = pres.addSlide();
  s.background = { color: C.black };
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.04, fill: { color: C.gold } });
  s.addText("1 人 + AI = ∞", { x: 0.8, y: 1.5, w: 8.4, h: 1.2, fontSize: 52, fontFace: "Arial", color: C.white, bold: true, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.8, y: 2.8, w: 2.4, h: 0.04, fill: { color: C.gold } });
  s.addText("智演助手", { x: 0.8, y: 3.2, w: 8.4, h: 0.6, fontSize: 24, fontFace: "Arial", color: C.gold, align: "center", margin: 0 });
  s.addText("谢谢", { x: 0.8, y: 4.2, w: 8.4, h: 0.4, fontSize: 14, fontFace: "Arial", color: C.gray, align: "center", margin: 0 });
}

// ===== 输出 =====
const outPath = "D:/PYTHON/simple_webpage/docs/智演助手_OPC路演PPT.pptx";
pres.writeFile({ fileName: outPath }).then(() => console.log("Done: " + outPath)).catch(e => console.error(e));
