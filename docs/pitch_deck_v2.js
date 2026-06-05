const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "智演助手";
pres.title = "智演助手 OPC 路演";

// ======== DESIGN TOKENS ========
const C = {
  bg: "0D0D0D",
  gold: "D4AF37",
  goldDark: "8B7320",
  white: "FFFFFF",
  grey: "999999",
  greyDark: "333333",
  accent: "1A1A1A",
};

const makeShadow = () => ({
  type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.4,
});

// Helper: gold accent line
function addGoldLine(slide, x, y, w) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: w || 1.5, h: 0.04,
    fill: { color: C.gold },
  });
}

// Helper: rounded card
function addCard(slide, x, y, w, h, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: opts.fill || C.accent },
    line: { color: C.greyDark, width: 0.5 },
    shadow: makeShadow(),
    rectRadius: 0.05,
  });
}


// ================================================================
// SLIDE 1: 封面
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Large geometric decorative circle (top right)
  s.addShape(pres.shapes.OVAL, {
    x: 7.5, y: -1.5, w: 4.5, h: 4.5,
    fill: { color: C.gold, transparency: 92 },
  });

  // Main title
  s.addText("智演助手", {
    x: 1, y: 1.5, w: 8, h: 1.4,
    fontSize: 60, fontFace: "Arial Black", color: C.white,
    bold: true, align: "center", margin: 0,
  });

  // Gold line under title
  addGoldLine(s, 4, 2.9, 2);

  // Subtitle
  s.addText("AI 驱动的剪辑智能体", {
    x: 1, y: 3.1, w: 8, h: 0.6,
    fontSize: 22, fontFace: "Microsoft YaHei", color: C.gold,
    align: "center", margin: 0,
  });

  // Tagline
  s.addText("每天自学最新剪辑技法 · 持续进化", {
    x: 1, y: 3.6, w: 8, h: 0.5,
    fontSize: 14, fontFace: "Microsoft YaHei", color: C.grey,
    align: "center", margin: 0,
  });

  // Bottom text
  s.addText("1 人  +  AI  =  一家动画工作室", {
    x: 1, y: 4.6, w: 8, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", color: C.white,
    align: "center", margin: 0,
  });

  // Corner info
  s.addText("OPC 创新创业大赛", { x: 0.5, y: 5.1, w: 3, h: 0.3, fontSize: 10, color: C.grey, fontFace: "Microsoft YaHei" });
  s.addText("路演人：______", { x: 7, y: 5.1, w: 2.5, h: 0.3, fontSize: 10, color: C.grey, fontFace: "Microsoft YaHei", align: "right" });
})();


// ================================================================
// SLIDE 2: 市场机会
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Title
  s.addText("市场机会", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Big number
  s.addText("1200 亿", {
    x: 2.5, y: 1.3, w: 5, h: 1.2,
    fontSize: 64, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", margin: 0,
  });
  s.addText("全球短视频市场规模", { x: 2.5, y: 2.5, w: 5, h: 0.4, fontSize: 14, color: C.grey, fontFace: "Microsoft YaHei", align: "center" });

  // 3 cards
  const cards = [
    { x: 0.4, icon: "🏢", title: "中小企业", desc: "缺视频\n请不起团队" },
    { x: 3.55, icon: "📱", title: "自媒体", desc: "追热点\n剪辑赶不上" },
    { x: 6.7, icon: "🎓", title: "教育/培训", desc: "课件视频化\n需求暴增" },
  ];
  cards.forEach(c => {
    addCard(s, c.x, 3.2, 2.8, 1.8);
    s.addText(c.icon, { x: c.x, y: 3.3, w: 2.8, h: 0.6, fontSize: 28, align: "center", margin: 0 });
    s.addText(c.title, { x: c.x + 0.2, y: 3.85, w: 2.4, h: 0.4, fontSize: 16, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", margin: 0 });
    s.addText(c.desc, { x: c.x + 0.2, y: 4.2, w: 2.4, h: 0.6, fontSize: 12, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });
  });

  // Bottom line
  s.addText("他们不缺创意，缺效率", { x: 1, y: 5.2, w: 8, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.gold, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 3: 竞品对比
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("为什么不用即梦 / Seko？", { x: 0.8, y: 0.4, w: 8, h: 0.6, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Table
  const tableData = [
    [
      { text: "", options: { fill: { color: C.bg }, color: C.white, fontSize: 12, fontFace: "Arial" } },
      { text: "即梦", options: { fill: { color: C.accent }, color: C.grey, bold: true, fontSize: 14, fontFace: "Arial", align: "center" } },
      { text: "Seko", options: { fill: { color: C.accent }, color: C.grey, bold: true, fontSize: 14, fontFace: "Arial", align: "center" } },
      { text: "智演助手", options: { fill: { color: C.goldDark }, color: C.gold, bold: true, fontSize: 14, fontFace: "Arial", align: "center" } },
    ],
    ...([
      { dim: "视频生成", jm: "✅", sk: "✅", zy: "✅" },
      { dim: "自动学习剪辑", jm: "❌", sk: "❌", zy: "✅" },
      { dim: "文档一键成片", jm: "❌", sk: "❌", zy: "✅" },
      { dim: "自部署·数据自有", jm: "❌", sk: "❌", zy: "✅" },
      { dim: "每分钟成本", jm: "¥36-66", sk: "¥58", zy: "¥25" },
    ].map((r, i) => [
      { text: r.dim, options: { fill: { color: i % 2 === 0 ? C.accent : C.bg }, color: C.white, fontSize: 13, fontFace: "Microsoft YaHei" } },
      { text: r.jm, options: { fill: { color: i % 2 === 0 ? C.accent : C.bg }, color: r.jm === "✅" ? "22C55E" : C.grey, fontSize: 14, align: "center" } },
      { text: r.sk, options: { fill: { color: i % 2 === 0 ? C.accent : C.bg }, color: r.sk === "✅" ? "22C55E" : C.grey, fontSize: 14, align: "center" } },
      { text: r.zy, options: { fill: { color: i % 2 === 0 ? C.accent : C.bg }, color: r.zy === "✅" || r.zy === "¥25" ? C.gold : C.grey, fontSize: 14, align: "center", bold: r.zy === "¥25" } },
    ])),
  ];

  s.addTable(tableData, {
    x: 1, y: 1.4, w: 8, h: 3.2,
    colW: [2.2, 1.8, 1.8, 2.2],
    border: { pt: 0.5, color: C.greyDark },
    rowH: [0.45, 0.45, 0.45, 0.45, 0.45, 0.45],
  });

  // Bottom
  s.addText("一样的模型，多一层剪辑智能", { x: 1, y: 4.9, w: 8, h: 0.4, fontSize: 18, fontFace: "Microsoft YaHei", color: C.gold, bold: true, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 4: 产品怎么用
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("产品怎么用", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // 3 step boxes
  const steps = [
    { nr: "①", label: "上传文档", sub: ".docx / .txt" },
    { nr: "②", label: "AI 全自动处理", sub: "分镜 → 出图 → 生视频 → 合成" },
    { nr: "③", label: "下载成品", sub: "带字幕 · 转场 · 角色一致" },
  ];
  steps.forEach((st, i) => {
    const x = 0.6 + i * 3.2;
    addCard(s, x, 1.5, 2.9, 3.2);
    // Circle number
    s.addShape(pres.shapes.OVAL, {
      x: x + 1.05, y: 1.8, w: 0.8, h: 0.8,
      fill: { color: C.gold },
    });
    s.addText(st.nr, { x: x + 1.05, y: 1.8, w: 0.8, h: 0.8, fontSize: 22, color: C.bg, bold: true, fontFace: "Arial", align: "center", valign: "middle", margin: 0 });
    s.addText(st.label, { x: x + 0.15, y: 2.8, w: 2.6, h: 0.5, fontSize: 20, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", margin: 0 });
    s.addText(st.sub, { x: x + 0.15, y: 3.2, w: 2.6, h: 0.4, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });

    // Arrow between cards
    if (i < 2) {
      s.addText("→", { x: x + 2.9, y: 2.7, w: 0.35, h: 0.5, fontSize: 24, color: C.gold, align: "center", margin: 0 });
    }
  });

  s.addText("上传文档 → 全自动 → 成品视频", { x: 1, y: 5, w: 8, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 5: AI 自学习剪辑系统
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("核心技术", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Center brain circle
  s.addShape(pres.shapes.OVAL, {
    x: 3.8, y: 1.6, w: 2.4, h: 2.4,
    fill: { color: C.gold, transparency: 85 },
    line: { color: C.gold, width: 2 },
  });
  s.addText("AI\n剪辑\n引擎", { x: 3.8, y: 1.6, w: 2.4, h: 2.4, fontSize: 22, fontFace: "Microsoft YaHei", color: C.gold, bold: true, align: "center", valign: "middle", margin: 0 });

  // 7 dimension labels around the circle
  const dims = [
    { label: "时间", x: 4.15, y: 1.1 },
    { label: "空间", x: 6.4, y: 1.8 },
    { label: "叙事", x: 6.7, y: 2.5 },
    { label: "节奏", x: 6.4, y: 3.3 },
    { label: "视听", x: 4.15, y: 4.2 },
    { label: "表现", x: 2.0, y: 3.3 },
    { label: "技术", x: 1.6, y: 1.8 },
  ];
  dims.forEach(d => {
    s.addText(d.label, { x: d.x, y: d.y, w: 1.2, h: 0.4, fontSize: 12, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });
  });

  // Bottom text
  s.addText("AI 每天自学当下最火的剪辑手法，持续进化", { x: 1, y: 4.7, w: 8, h: 0.4, fontSize: 16, fontFace: "Microsoft YaHei", color: C.gold, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 6: 角色一致性 + 低成本
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("角色一致性 + 低成本", { x: 0.8, y: 0.4, w: 6, h: 0.6, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Left: 其他AI
  addCard(s, 0.5, 1.5, 4.2, 2.8, { fill: C.accent });
  s.addText("其他 AI", { x: 0.5, y: 1.6, w: 4.2, h: 0.4, fontSize: 14, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  // Draw 3 different face circles
  [1.3, 2.3, 3.3].forEach((cx, i) => {
    s.addShape(pres.shapes.OVAL, {
      x: cx + 0.8, y: 2.1, w: 0.6, h: 0.7,
      fill: { color: C.greyDark },
      line: { color: ["EF4444", "F97316", "EF4444"][i], width: 1.5 },
    });
  });
  s.addText("12 个镜头 = 12 张不同的脸", { x: 0.5, y: 3.2, w: 4.2, h: 0.4, fontSize: 12, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  s.addText("概率模型，越跑越漂", { x: 0.5, y: 3.5, w: 4.2, h: 0.3, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });

  // Right: 我们
  addCard(s, 5.3, 1.5, 4.2, 2.8);
  s.addText("智演助手", { x: 5.3, y: 1.6, w: 4.2, h: 0.4, fontSize: 14, color: C.gold, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  // 3 identical face circles
  [1.3, 2.3, 3.3].forEach(cx => {
    s.addShape(pres.shapes.OVAL, {
      x: cx + 5.6, y: 2.1, w: 0.6, h: 0.7,
      fill: { color: C.goldDark },
      line: { color: C.gold, width: 1.5 },
    });
  });
  s.addText("12 个镜头 = 同一张脸", { x: 5.3, y: 3.2, w: 4.2, h: 0.4, fontSize: 12, color: C.white, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  s.addText("代码注入，逐字相同", { x: 5.3, y: 3.5, w: 4.2, h: 0.3, fontSize: 11, color: C.gold, fontFace: "Microsoft YaHei", align: "center", margin: 0 });

  // 3 big numbers at bottom
  const nums = [
    { val: "100%", label: "角色一致" },
    { val: "0", label: "额外 API 调用" },
    { val: "¥25", label: "每分钟成本" },
  ];
  nums.forEach((n, i) => {
    const x = 1 + i * 3.2;
    s.addText(n.val, { x, y: 4.6, w: 2, h: 0.7, fontSize: 36, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", margin: 0 });
    s.addText(n.label, { x, y: 5.15, w: 2, h: 0.3, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  });
})();


// ================================================================
// SLIDE 7: 产品演示
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("产品演示", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Demo placeholder frame
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1, y: 1.5, w: 8, h: 3.5,
    fill: { color: C.accent },
    line: { color: C.greyDark, width: 1, dashType: "dash" },
    rectRadius: 0.1,
  });

  s.addText("🎬", { x: 1, y: 2, w: 8, h: 1, fontSize: 60, align: "center", margin: 0 });
  s.addText("产品界面截图 / 录屏 GIF", { x: 1, y: 2.8, w: 8, h: 0.5, fontSize: 16, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  s.addText("[此处放入产品操作录屏或关键界面截图]", { x: 1, y: 3.3, w: 8, h: 0.4, fontSize: 11, color: C.greyDark, fontFace: "Microsoft YaHei", align: "center", margin: 0 });

  s.addText("文档 → AI → 视频", { x: 1, y: 5.2, w: 8, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 8: 商业模式
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("商业模式", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Pyramid (4 tiers)
  const tiers = [
    { w: 2.5, color: C.gold, label: "定制部署", sub: "企业私有化 ¥5000起", opacity: 100 },
    { w: 4.0, color: C.gold, label: "API 按次计费", sub: "第三方平台调用 ¥5-15/次", opacity: 70 },
    { w: 5.5, color: C.gold, label: "SaaS 订阅 ¥99/月", sub: "基础免费 · Pro付费", opacity: 40 },
    { w: 7.0, color: C.gold, label: "趋势数据服务", sub: "剪辑趋势报告 · 技法模板库", opacity: 20 },
  ];

  tiers.forEach((t, i) => {
    const y = 1.5 + i * 0.9;
    const x = (10 - t.w) / 2;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: t.w, h: 0.7,
      fill: { color: C.gold, transparency: 100 - t.opacity },
      line: { color: C.gold, width: 1 },
    });
    s.addText(t.label, {
      x, y: y + 0.05, w: t.w, h: 0.35,
      fontSize: 18, fontFace: "Microsoft YaHei", color: t.opacity >= 40 ? C.white : C.grey,
      bold: true, align: "center", margin: 0,
    });
    s.addText(t.sub, {
      x, y: y + 0.38, w: t.w, h: 0.25,
      fontSize: 10, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0,
    });
  });

  s.addText("4 层收入结构 · 毛利 85%+", { x: 1, y: 5.2, w: 8, h: 0.3, fontSize: 14, fontFace: "Microsoft YaHei", color: C.gold, align: "center", margin: 0 });
})();


// ================================================================
// SLIDE 9: 怎么卖
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("怎么卖", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // 3 customer cards
  const customers = [
    { icon: "🏫", title: "教育机构", desc: "课件一键变视频", channel: "钉钉 / 飞书应用市场" },
    { icon: "📱", title: "自媒体", desc: "追热点快人一步", channel: "社群 + 免费版引流" },
    { icon: "🏢", title: "中小企业", desc: "一个人 = 一个团队", channel: "SEO + 案例营销" },
  ];
  customers.forEach((c, i) => {
    const x = 0.4 + i * 3.2;
    addCard(s, x, 1.4, 2.9, 2.8);
    s.addText(c.icon, { x, y: 1.5, w: 2.9, h: 0.6, fontSize: 30, align: "center", margin: 0 });
    s.addText(c.title, { x: x + 0.15, y: 2.1, w: 2.6, h: 0.4, fontSize: 18, fontFace: "Microsoft YaHei", color: C.white, bold: true, align: "center", margin: 0 });
    s.addText(c.desc, { x: x + 0.15, y: 2.5, w: 2.6, h: 0.4, fontSize: 16, fontFace: "Microsoft YaHei", color: C.gold, align: "center", margin: 0 });
    s.addText(c.channel, { x: x + 0.15, y: 3.5, w: 2.6, h: 0.3, fontSize: 10, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
  });

  // Funnel
  s.addText("免费引流  →  Pro 试用  →  付费转化  →  企业向上销售", { x: 0.5, y: 4.6, w: 9, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });

  // Arrow
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1.5, y: 5.0, w: 7, h: 0.04,
    fill: { color: C.goldDark },
  });
})();


// ================================================================
// SLIDE 10: 售后 — AI 客服
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText('AI 客服 "智小演"', { x: 0.8, y: 0.4, w: 6, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Chat UI mockup
  addCard(s, 0.8, 1.5, 4.5, 3.5);
  s.addText("💬 智小演 · 智能客服", { x: 1, y: 1.55, w: 4.1, h: 0.35, fontSize: 13, fontFace: "Microsoft YaHei", color: C.gold, bold: true, margin: 0 });

  // Chat bubbles
  const chatMsgs = [
    { user: "用户", text: "视频生成失败了怎么办？", align: "right", color: C.greyDark, x: 2.2 },
    { user: "智小演", text: "正在诊断… 您的分辨率设置过高，建议降为 1080p 重试 ✓", align: "left", color: C.goldDark, x: 1.2 },
    { user: "用户", text: "最近流行什么剪辑风格？", align: "right", color: C.greyDark, x: 2.2 },
    { user: "智小演", text: "本周趋势：快剪+跳切 ↑ 20%\n已为您推荐 3 个模板 👇", align: "left", color: C.goldDark, x: 1.2 },
  ];
  chatMsgs.forEach((msg, i) => {
    const y = 2.1 + i * 0.75;
    const w = 3.0;
    const x = msg.x;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w, h: 0.55, fill: { color: msg.color },
      rectRadius: 0.06,
    });
    s.addText(msg.text, { x: x + 0.1, y, w: w - 0.2, h: 0.55, fontSize: 9, color: C.white, fontFace: "Microsoft YaHei", valign: "middle", margin: 0 });
  });

  // Right side info
  s.addText("80%", { x: 5.8, y: 1.8, w: 3.5, h: 1, fontSize: 60, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", margin: 0 });
  s.addText("问题 AI 自动解决", { x: 5.8, y: 2.8, w: 3.5, h: 0.4, fontSize: 14, fontFace: "Microsoft YaHei", color: C.white, align: "center", margin: 0 });

  s.addText("7×24 小时在线", { x: 5.8, y: 3.3, w: 3.5, h: 0.3, fontSize: 18, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0 });

  // Features
  const features = ["自动诊断生成失败", "推送 Prompt 优化建议", "实时查剪辑趋势数据", "复杂问题转人工"];
  features.forEach((f, i) => {
    s.addText("✓  " + f, { x: 5.8, y: 3.8 + i * 0.35, w: 3.5, h: 0.3, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", margin: 0 });
  });
})();


// ================================================================
// SLIDE 11: 路线图
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addText("路线图", { x: 0.8, y: 0.4, w: 4, h: 0.6, fontSize: 32, fontFace: "Arial Black", color: C.white, margin: 0 });
  addGoldLine(s, 0.8, 1.05, 1.2);

  // Timeline
  s.addShape(pres.shapes.RECTANGLE, {
    x: 1, y: 2.7, w: 8, h: 0.04,
    fill: { color: C.gold },
  });

  // 3 nodes
  const nodes = [
    { x: 1.5, label: "打磨期", sub: "现在", done: true,
      items: "多语言 · Docker · BGM\n角色一致性 · 剪辑爬虫\nPro / 全自动双模式" },
    { x: 4.2, label: "商业化", sub: "半年内", done: false,
      items: "SaaS 付费订阅\nAPI 计费平台\n智小演客服上线\n钉钉 / 飞书渠道" },
    { x: 7, label: "规模化", sub: "一年后", done: false,
      items: "1000+ 付费客户\n移动端 App\n团队协作\n海外市场" },
  ];

  nodes.forEach(n => {
    const cx = n.x + 0.6;
    // Circle
    s.addShape(pres.shapes.OVAL, {
      x: cx - 0.2, y: 2.45, w: 0.4, h: 0.4,
      fill: { color: n.done ? C.gold : C.accent },
      line: { color: C.gold, width: 2 },
    });
    // Label
    s.addText(n.label, { x: n.x, y: 1.4, w: 1.8, h: 0.5, fontSize: 24, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", margin: 0 });
    s.addText(n.sub, { x: n.x, y: 1.85, w: 1.8, h: 0.3, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
    // Items
    s.addText(n.items, { x: n.x - 0.2, y: 3.1, w: 2.2, h: 2, fontSize: 10, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0, lineSpacingMultiple: 1.4 });
  });
})();


// ================================================================
// SLIDE 12: 结尾
// ================================================================
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Decorative circle
  s.addShape(pres.shapes.OVAL, {
    x: 3, y: -0.5, w: 4, h: 4,
    fill: { color: C.gold, transparency: 92 },
  });

  s.addText("智演助手", {
    x: 1, y: 1.2, w: 8, h: 1.2,
    fontSize: 54, fontFace: "Arial Black", color: C.white, bold: true, align: "center", margin: 0,
  });
  addGoldLine(s, 4, 2.4, 2);

  s.addText("1 人  +  AI  =  ∞", {
    x: 1, y: 2.8, w: 8, h: 1,
    fontSize: 40, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", margin: 0,
  });

  s.addText("每天自学最新剪辑技法 · 让 AI 跟上潮流的脚步", {
    x: 1, y: 3.8, w: 8, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0,
  });

  s.addText("联系方式：3280097009@qq.com", {
    x: 1, y: 4.7, w: 8, h: 0.3,
    fontSize: 12, fontFace: "Microsoft YaHei", color: C.grey, align: "center", margin: 0,
  });

  s.addText("Thank You", {
    x: 1, y: 5.1, w: 8, h: 0.3,
    fontSize: 14, fontFace: "Arial", color: C.gold, align: "center", margin: 0,
  });
})();


// ======== OUTPUT ========
pres.writeFile({ fileName: "d:/PYTHON/simple_webpage/docs/智演助手_OPC路演PPT_V2.pptx" })
  .then(() => console.log("✅ PPT generated successfully!"))
  .catch(err => console.error("❌ Error:", err));
