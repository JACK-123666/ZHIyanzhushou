const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "智演助手";

const C = {
  bg: "0D0D0D",
  gold: "D4AF37",
  goldDark: "8B7320",
  white: "FFFFFF",
  grey: "999999",
  greyDark: "333333",
  accent: "1A1A1A",
  green: "22C55E",
  blue: "6366F1",
};

const makeShadow = () => ({ type: "outer", color: "000000", blur: 8, offset: 3, angle: 135, opacity: 0.4 });

const slide = pres.addSlide();
slide.background = { color: C.bg };

// Title
slide.addText("财务预测", { x: 0.8, y: 0.3, w: 4, h: 0.5, fontSize: 28, fontFace: "Arial Black", color: C.white, margin: 0 });
// Gold line
slide.addShape(pres.shapes.RECTANGLE, { x: 0.8, y: 0.85, w: 1.0, h: 0.03, fill: { color: C.gold } });

// === LEFT COLUMN: Unit Economics ===
slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.2, w: 4.3, h: 4.2, fill: { color: C.accent }, rectRadius: 0.05, line: { color: C.greyDark, width: 0.5 } });

slide.addText("单位经济模型", { x: 0.6, y: 1.3, w: 3.9, h: 0.35, fontSize: 14, fontFace: "Microsoft YaHei", color: C.gold, bold: true, margin: 0 });

const unitData = [
  ["API 调用成本", "¥10 / 分钟"],
  ["服务器 + 带宽", "¥500 / 月"],
  ["单客户获客成本", "¥30 (社群/SEO)"],
  ["Pro 月订阅价", "¥99 / 月"],
  ["企业版年费", "¥4,999 / 年"],
  ["毛利率", "85%"],
];
unitData.forEach((row, i) => {
  slide.addText(row[0], { x: 0.7, y: 1.8 + i * 0.48, w: 2.1, h: 0.35, fontSize: 11, color: C.grey, fontFace: "Microsoft YaHei", margin: 0 });
  slide.addText(row[1], { x: 2.8, y: 1.8 + i * 0.48, w: 1.7, h: 0.35, fontSize: 11, color: C.white, fontFace: "Microsoft YaHei", bold: true, align: "right", margin: 0 });
});

// === RIGHT COLUMN: Revenue Forecast Chart ===
slide.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.2, w: 4.5, h: 4.2, fill: { color: C.accent }, rectRadius: 0.05, line: { color: C.greyDark, width: 0.5 } });

slide.addText("营收预测（万元）", { x: 5.3, y: 1.3, w: 4.1, h: 0.35, fontSize: 14, fontFace: "Microsoft YaHei", color: C.gold, bold: true, margin: 0 });

// Bar chart
slide.addChart(pres.charts.BAR, [{
  name: "营收",
  labels: ["Year 1", "Year 2", "Year 3"],
  values: [120, 500, 2000],
}], {
  x: 5.3, y: 1.8, w: 4.1, h: 2.5, barDir: "col",
  chartColors: [C.gold],
  chartArea: { fill: { color: C.accent } },
  catAxisLabelColor: C.grey,
  valAxisLabelColor: C.grey,
  valGridLine: { color: C.greyDark, size: 0.5 },
  catGridLine: { style: "none" },
  showValue: true,
  dataLabelPosition: "outEnd",
  dataLabelColor: C.white,
  dataLabelFontSize: 12,
  showLegend: false,
  showTitle: false,
});

// === BOTTOM: 3 Key Metrics ===
const metrics = [
  { label: "Year 1 目标用户", value: "500+", sub: "Pro + 企业" },
  { label: "回本周期", value: "6 个月", sub: "单人运营" },
  { label: "成本优势", value: "1/3", sub: "vs 即梦/Seko" },
];
metrics.forEach((m, i) => {
  const x = 0.6 + i * 3.1;
  slide.addShape(pres.shapes.RECTANGLE, { x, y: 4.65, w: 2.8, h: 0.35, fill: { color: C.greyDark }, rectRadius: 0.03 });
  slide.addText(m.value, { x, y: 4.65, w: 2.8, h: 0.35, fontSize: 13, fontFace: "Arial Black", color: C.gold, bold: true, align: "center", valign: "middle", margin: 0 });
  slide.addText(`${m.label}  ·  ${m.sub}`, { x, y: 5.0, w: 2.8, h: 0.2, fontSize: 9, color: C.grey, fontFace: "Microsoft YaHei", align: "center", margin: 0 });
});

// Footer source line
slide.addText("数据参考：可灵AI ARR $2.4-3亿 · 即梦Q1月活1352万 · 爱诗科技ARR $4000万 | 中国AI视频市场2026年突破200亿元", {
  x: 0.5, y: 5.35, w: 9, h: 0.2, fontSize: 7, color: C.greyDark, fontFace: "Microsoft YaHei", align: "center", margin: 0,
});

pres.writeFile({ fileName: "d:/PYTHON/simple_webpage/docs/财务预测_单页.pptx" })
  .then(() => console.log("✅ Finance slide generated!"))
  .catch(err => console.error("❌", err));
