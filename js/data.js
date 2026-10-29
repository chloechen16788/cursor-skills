/* 恒星光谱生命推演 — 光谱数据与讲解知识库 */
const ASSET = "assets/";

function stage(name, years, dur, diam, diamText, sprite, extra) {
  return Object.assign(
    { name, years, dur, diam, diamText, sprite, filter: "", jets: false, sn: false, ring: false, note: "" },
    extra || {}
  );
}

const EPI = 0;

const CLASSES = {
  L: {
    id: "L", cost: 1, title: "褐矮星 L", color: "暗红偏橙",
    mass: "73–84 MJup",
    density: "主序段 70–140 g/cm³；沉寂后 80–150 g/cm³",
    aliases: ["L", "褐矮星", "褐矮", "L型", "L型星"],
    endingText: "只有两段：准恒星亚主序之后直接成为低温沉寂残体，再在残骸屏里冷却成暗沉球体，没有白矮星、中子星或黑洞。",
    remnant: { kind: "cool-dead", from: "star-l.png", to: "dead.png", left: "低温沉寂残体", right: "完全冷却残体", spin: false },
    stages: [
      stage("准恒星亚主序", 5e11, "5000亿年", 133000, "12.6万–14.0万km", "star-l.png", {
        note: "暗红偏橙，对流热斑，淡红弥散光晕，氘聚变，碱金属蒸汽。质量 73–84 MJup，密度 70–140 g/cm³"
      }),
      stage("低温沉寂残体", EPI, "永久冷却", 112000, "约11.2万km", "star-l.png", {
        filter: "brightness(0.45) saturate(0.35)",
        note: "均匀暗沉，无热斑，光晕褪尽，半径收到约 0.8 RJ，密度 80–150 g/cm³"
      })
    ]
  },
  M9: {
    id: "M9", cost: 3, title: "红矮星 M9", color: "深暗红",
    mass: "0.08–0.2 M☉；氦白矮星残留 0.07–0.18 M☉",
    density: "主序 20–50 g/cm³；氦白矮星 >1 t/cm³",
    aliases: ["M9", "晚型红矮星", "暗红矮星", "极冷红矮星", "红矮星", "红矮"],
    endingText: "走完红巨星后留下氦白矮星，再在残骸屏冷却成低温沉寂残体。",
    remnant: { kind: "cool-dead", from: "star-a.png", to: "dead.png", left: "氦白矮星", right: "低温沉寂残体" },
    stages: [
      stage("暗红主序星", 7e10, "700亿年", 208500, "13.9万–27.8万km", "star-m9.png", {
        note: "深暗红，密集小耀斑，完全对流。质量 0.08–0.2 M☉，密度 20–50 g/cm³"
      }),
      stage("SGB", 1.2e9, "12亿年", 626500, "55.7万–69.6万km", "star-m9.png", {
        filter: "saturate(1.1) hue-rotate(-6deg)",
        note: "耀斑大减，光晕变宽。密度 5–12 g/cm³"
      }),
      stage("RGB", 8e8, "8亿年", 1252500, "83.5万–167万km", "star-m9.png", {
        filter: "saturate(1.35) hue-rotate(-16deg) brightness(1.05)",
        note: "亮橙红。密度 <0.5 g/cm³"
      }),
      stage("氦白矮星", EPI, "永久冷却", 12700, "约1.27万km", "star-a.png", {
        note: "质量 0.07–0.18 M☉，密度 >1 t/cm³，纯白死寂"
      })
    ]
  },
  M0: {
    id: "M0", cost: 5, title: "红矮星 M0", color: "橙红",
    mass: "0.2–0.4 M☉；碳氧白矮星 0.25–0.35 M☉",
    density: "主序 12–28 g/cm³",
    aliases: ["M0", "早型红矮星", "橙红矮星", "M0红矮星"],
    endingText: "红团簇之后留下碳氧白矮星，没有蓝回圈，再冷却成低温沉寂残体。",
    remnant: { kind: "cool-dead", from: "star-pale.png", to: "dead.png", left: "碳氧白矮星", right: "低温沉寂残体" },
    stages: [
      stage("橙红主序星", 4.5e10, "450亿年", 382500, "27.8万–48.7万km", "star-m0.png", {
        note: "质量 0.2–0.4 M☉，密度 12–28 g/cm³"
      }),
      stage("SGB", 1.8e9, "18亿年", 696000, "约69.6万km", "star-m0.png", { note: "密度 4–9 g/cm³" }),
      stage("HG", 1.2e8, "1.2亿年", 1740000, "69.6万–278.4万km", "star-k.png", { note: "密度 0.3–4 g/cm³" }),
      stage("RGB", 1.2e9, "12亿年", 90480000, "6960万–1.1136亿km", "star-m9.png", {
        filter: "saturate(1.4) hue-rotate(-18deg)",
        note: "深红，第一掘取。密度 <0.01 g/cm³"
      }),
      stage("HB红团簇", 6e8, "6亿年", 16010000, "1114万–2088万km", "star-g-alt.png", {
        note: "橙黄，无蓝回圈。密度 0.02–0.1 g/cm³"
      }),
      stage("碳氧白矮星", EPI, "永久冷却", 12700, "1.27万km", "star-pale.png", { note: "残留 0.25–0.35 M☉" })
    ]
  },
  K: {
    id: "K", cost: 10, title: "橙矮星 K", color: "暖橙",
    mass: "0.4–0.8 M☉；白矮星 0.5–0.7 M☉",
    density: "主序 2.8–7.5 g/cm³",
    aliases: ["K", "橙矮星", "橙矮", "K型", "K型星"],
    endingText: "经热脉冲 AGB 与后 AGB 留下碳氧白矮星，再冷却。水平分支里有大约 4000 万年的蓝回圈。",
    remnant: { kind: "cool-dead", from: "star-pale.png", to: "dead.png", left: "碳氧白矮星", right: "低温沉寂残体" },
    stages: [
      stage("暖橙主序星", 1.8e10, "180亿年", 1044000, "83.5万–125.3万km", "star-k.png", {
        note: "质量 0.4–0.8 M☉，密度 2.8–7.5 g/cm³"
      }),
      stage("SGB", 8e8, "8亿年", 2088000, "139.2万–278.4万km", "star-k.png", { note: "密度 1–3 g/cm³" }),
      stage("HG", 5e7, "5000万年", 8352000, "278.4万–1392万km", "star-m0.png", { note: "密度 0.05–1 g/cm³" }),
      stage("RGB", 6e8, "6亿年", 111360000, "8352万–1.392亿km", "star-m9.png", {
        filter: "saturate(1.3) hue-rotate(-12deg)",
        note: "密度 <0.01 g/cm³"
      }),
      stage("HB红团簇", 3e8, "3亿年", 27840000, "1392万–4176万km", "star-g-alt.png", {
        note: "橙黄。蓝回圈约 4000 万年，回圈时短暂黄白。密度 0.01–0.08 g/cm³"
      }),
      stage("AGB E-AGB→TP-AGB", 1.2e8, "1.2亿年", 278500000, "2.09亿–3.48亿km", "star-m9.png", {
        filter: "saturate(1.25) hue-rotate(-8deg) brightness(0.95)",
        note: "热脉冲约 2000 万年。质量约 0.5–0.7 M☉，暗红，热脉冲闪烁。密度 1e-7–1e-6 g/cm³"
      }),
      stage("后AGB", 1e5, "10万年", 208500, "13.9万–27.8万km", "star-b9.png", {
        ring: true,
        note: "高温蓝白核心加膨胀星云壳。密度 10–100 kg/cm³"
      }),
      stage("碳氧白矮星", EPI, "永久冷却", 12700, "1.27万km", "star-a.png", { note: "0.5–0.7 M☉" })
    ]
  },
  G: {
    id: "G", cost: 20, title: "黄矮星 G", color: "金黄",
    mass: "0.8–1.2 M☉；白矮星 0.55–0.7 M☉",
    density: "主序 1.0–1.8 g/cm³",
    aliases: ["G", "黄矮星", "类太阳星", "太阳型星", "G型", "G型星", "类日恒星"],
    endingText: "类太阳路径：红巨星、水平分支（蓝回圈约 1500 万年）、AGB、后 AGB，留下碳氧白矮星后冷却。",
    remnant: { kind: "cool-dead", from: "star-a.png", to: "dead.png", left: "碳氧白矮星", right: "低温沉寂残体" },
    stages: [
      stage("金黄主序星", 1e10, "100亿年", 1392000, "111.4万–167万km", "star-g.png", {
        note: "质量 0.8–1.2 M☉，密度 1.0–1.8 g/cm³"
      }),
      stage("SGB", 2e9, "20亿年", 2297000, "181万–278.4万km", "star-g.png", { note: "密度 0.6–1.1 g/cm³" }),
      stage("HG", 2e8, "2亿年", 11832000, "278.4万–2088万km", "star-g-alt.png", { note: "壳层氢燃烧，恒星迅速膨胀" }),
      stage("RGB", 1e9, "10亿年", 195000000, "1.39亿–2.51亿km", "star-m9.png", {
        filter: "saturate(1.2) hue-rotate(-10deg)",
        note: "密度 <0.005 g/cm³"
      }),
      stage("HB", 1e8, "1亿年", 38280000, "2088万–5568万km", "star-g-alt.png", {
        note: "黄橙。蓝回圈约 1500 万年，回圈时短暂黄白"
      }),
      stage("AGB", 8e7, "8000万年", 348000000, "2.78亿–4.18亿km", "star-m9.png", {
        note: "热脉冲约 1500 万年。质量 0.55–0.7 M☉"
      }),
      stage("后AGB", 3e4, "数万年", 139000, "约13.9万km", "star-b9.png", {
        ring: true, note: "蓝白核心，行星状星云前身"
      }),
      stage("碳氧白矮星", EPI, "永久冷却", 12700, "1.27万km", "star-a.png", { note: "0.55–0.7 M☉" })
    ]
  },
  F: {
    id: "F", cost: 35, title: "黄白星 F", color: "亮黄白",
    mass: "1.2–2.5 M☉；残留 0.8–1.1 M☉",
    density: "主序 0.9–1.3 g/cm³",
    aliases: ["F", "黄白星", "黄白矮星", "F型", "F型星", "亮黄白星"],
    endingText: "红巨星没有氦闪。高质量端留下氧氖镁白矮星，低质量端留下碳氧白矮星，残留 0.8–1.1 M☉，然后冷却。",
    remnant: { kind: "cool-dead", from: "star-a.png", to: "dead.png", left: "氧氖镁或碳氧白矮星", right: "低温沉寂残体" },
    stages: [
      stage("亮黄白主序星", 3.5e9, "35亿年", 2365000, "167万–306万km", "star-f.png", {
        note: "质量 1.2–2.5 M☉，密度 0.9–1.3 g/cm³"
      }),
      stage("SGB", 4e8, "4亿年", 4175000, "278万–557万km", "star-f.png", { note: "密度 0.4–0.8 g/cm³" }),
      stage("HG", 6e6, "600万年", 16705000, "557万–2784万km", "star-g-alt.png", { note: "壳层膨胀" }),
      stage("RGB", 2.5e8, "2.5亿年", 125280000, "8352万–1.6704亿km", "star-m0.png", {
        filter: "saturate(1.25) hue-rotate(-8deg)",
        note: "橙红，无氦闪"
      }),
      stage("蓝回圈", 1.2e7, "1200万年", 48720000, "2784万–6960万km", "star-b9.png", {
        note: "亮黄白，造父脉动。密度 0.02–0.1 g/cm³"
      }),
      stage("AGB", 4e7, "4000万年", 348000000, "2.09亿–4.87亿km", "star-m9.png", {
        note: "热脉冲约 800 万年。质量 0.7–1.0 M☉"
      }),
      stage("后AGB", 3e4, "数万年", 139000, "约13.9万km", "star-b5.png", {
        ring: true, note: "核心 0.7–1.0 M☉"
      }),
      stage("氧氖镁或碳氧白矮星", EPI, "永久冷却", 12700, "1.27万km", "star-a.png", {
        note: "近 8 M☉ 的前身留下氧氖镁白矮星，低质量端为碳氧白矮星。残留 0.8–1.1 M☉"
      })
    ]
  },
  A: {
    id: "A", cost: 60, title: "白星 A", color: "纯白高温",
    mass: "2.5–8 M☉；氧氖镁白矮星 1.0–1.4 M☉",
    density: "主序 0.7–1.1 g/cm³",
    aliases: ["A", "白色主序星", "A型", "A型星", "纯白主序星"],
    endingText: "造父脉动主产区在蓝回圈。终局是氧氖镁白矮星（1.0–1.4 M☉），然后冷却，不爆炸。",
    remnant: { kind: "cool-dead", from: "star-b9.png", to: "dead.png", left: "氧氖镁白矮星", right: "低温沉寂残体" },
    stages: [
      stage("纯白高温主序星", 2.5e8, "2.5亿年", 3345000, "251万–418万km", "star-a.png", {
        note: "质量 2.5–8 M☉，密度 0.7–1.1 g/cm³"
      }),
      stage("SGB", 2.5e7, "2500万年", 6265000, "418万–835万km", "star-a.png", { note: "核心氢耗尽，壳层氢燃烧" }),
      stage("HG", 4e6, "400万年", 25055000, "835万–4176万km", "star-f.png", { note: "赫氏空隙快速穿过" }),
      stage("RGB", 1.2e8, "1.2亿年", 160000000, "1.11亿–2.09亿km", "star-g.png", {
        filter: "saturate(1.3) hue-rotate(-14deg)", note: "红巨星"
      }),
      stage("蓝回圈", 8e6, "800万年", 59160000, "3480万–8352万km", "star-b5.png", { note: "亮蓝白，造父变星主产区" }),
      stage("AGB", 2e7, "2000万年", 417500000, "2.78亿–5.57亿km", "star-m9.png", { note: "热脉冲约 400 万年。质量 0.8–1.1 M☉" }),
      stage("后AGB", 3e4, "数万年", 139000, "约13.9万km", "star-b9.png", { ring: true, note: "高温核心露出" }),
      stage("氧氖镁白矮星", EPI, "永久冷却", 12700, "1.27万km", "star-b9.png", { note: "1.0–1.4 M☉" })
    ]
  },
  B9: {
    id: "B9", cost: 80, title: "蓝白星 B9", color: "浅蓝白",
    mass: "8–12 M☉；中子星残留 1.44–3 M☉",
    density: "主序 0.5–0.8 g/cm³；红超巨星约 1e-7 g/cm³",
    aliases: ["B9", "B9型", "浅蓝白星"],
    endingText: "核心坍缩超新星，留下中子星（图十四，直径 20–30 km），再在残骸屏旋转并冷却成暗灰中子星。",
    remnant: { kind: "cool-ns", from: "neutron.png", to: "ns-cool.png", left: "核心坍缩超新星+中子星", right: "冷却中子星" },
    stages: [
      stage("浅蓝白主序星", 1.8e7, "1800万年", 5570000, "418万–696万km", "star-b9.png", {
        note: "质量 8–12 M☉，密度 0.5–0.8 g/cm³"
      }),
      stage("SGB", 3e6, "300万年", 11830000, "696万–1670万km", "star-b9.png", { note: "核心氢耗尽" }),
      stage("HG", 8e5, "80万年", 36190000, "1670万–5568万km", "star-b5.png", { note: "跨过赫氏空隙" }),
      stage("RSG", 2.5e6, "250万年", 696000000, "5.57亿–8.35亿km", "star-m9.png", {
        filter: "saturate(1.45) hue-rotate(-20deg)", note: "密度约 1e-7 g/cm³"
      }),
      stage("大质量蓝回圈蓝超巨星", 1.2e6, "120万年", 146260000, "8352万–2.09亿km", "star-b5.png", {
        note: "质量 7–10 M☉"
      }),
      stage("红超巨星回归+多层壳超新星前身", 3e5, "几十万年", 600000000, "仍为红超巨星量级", "star-m9.png", {
        filter: "saturate(1.4) hue-rotate(-18deg) brightness(0.95)",
        note: "质量 6–9 M☉，铁核 1.4–2 M☉"
      }),
      stage("核心坍缩超新星+中子星", EPI, "爆发瞬间", 25, "20–30km", "neutron.png", {
        sn: true, note: "残留 1.44–3 M☉"
      })
    ]
  },
  B5: {
    id: "B5", cost: 105, title: "蓝星 B5", color: "亮蓝",
    mass: "12–18 M☉；中子星 1.44–3 M☉",
    density: "主序较高，红超巨星极低",
    aliases: ["B5", "B5型", "亮蓝星"],
    endingText: "Ib/Ic 超新星加中子星（图十四），残骸屏里自转并冷却。",
    remnant: { kind: "cool-ns", from: "neutron.png", to: "ns-cool.png", left: "Ib/Ic超新星+中子星", right: "冷却中子星" },
    stages: [
      stage("亮蓝主序星", 1e7, "1000万年", 8355000, "557万–1114万km", "star-b5.png", { note: "质量 12–18 M☉" }),
      stage("SGB", 1.8e6, "180万年", 18100000, "1114万–2506万km", "star-b5.png", { note: "核心氢耗尽" }),
      stage("HG", 4e5, "40万年", 54290000, "2506万–8352万km", "star-b0.png", { note: "快速膨胀" }),
      stage("RSG", 1.2e6, "120万年", 903000000, "6.96亿–11.1亿km", "star-m9.png", {
        filter: "saturate(1.4) hue-rotate(-18deg)", note: "红超巨星"
      }),
      stage("蓝回圈蓝超巨星", 6e5, "60万年", 194500000, "1.11亿–2.78亿km", "star-b0.png", {
        jets: true, note: "质量 11–15 M☉，双向喷流"
      }),
      stage("红超巨星回归+硅壳前身", 1.5e5, "十几万年", 800000000, "红超巨星量级", "star-m9.png", {
        filter: "hue-rotate(-16deg) saturate(1.3)", note: "质量 10–14 M☉"
      }),
      stage("Ib/Ic超新星+中子星", EPI, "爆发瞬间", 25, "20–30km", "neutron.png", {
        sn: true, note: "1.44–3 M☉"
      })
    ]
  },
  B0: {
    id: "B0", cost: 120, title: "深蓝星 B0", color: "深蓝",
    mass: "18–25 M☉；黑洞 >3 M☉",
    density: "星风强烈，包层被吹薄",
    aliases: ["B0", "B0型", "深蓝星"],
    endingText: "Ic 超新星后留下黑洞（正面对吸积盘）。残骸屏停留 30 秒，白闪之后黑洞消失，回到首页。",
    remnant: { kind: "bh", bh: "bh-face.png", left: "Ic超新星+黑洞", right: "黑洞" },
    stages: [
      stage("深蓝主序星", 6e6, "600万年", 13915000, "974万–1809万km", "star-b0.png", {
        filter: "brightness(0.82) saturate(1.3) hue-rotate(12deg)", note: "质量 18–25 M☉"
      }),
      stage("SGB", 1e6, "100万年", 26445000, "1809万–3480万km", "star-b0.png", { note: "核心氢耗尽" }),
      stage("HG", 2.5e5, "25万年", 72900000, "3480万–1.11亿km", "star-b5.png", { note: "赫氏空隙" }),
      stage("RSG", 7e5, "70万年", 1112500000, "8.35亿–13.9亿km", "star-m9.png", {
        filter: "saturate(1.35) hue-rotate(-14deg)", note: "星风吹氢"
      }),
      stage("蓝回圈", 3.5e5, "35万年", 243500000, "1.39亿–3.48亿km", "star-b0.png", {
        note: "质量 12–18 M☉，氢包层几乎吹净"
      }),
      stage("WR", 1.5e5, "15万年", 48720000, "2784万–6960万km", "star-w.png", {
        jets: true, filter: "contrast(1.15) brightness(1.05)",
        note: "裸露氦碳氮，双向喷流。质量 10–15 M☉"
      }),
      stage("硅燃烧前身", 2e4, "数万年", 40000000, "致密核心前身", "star-o9.png", {
        note: "质量 8–12 M☉，铁核 1.5–2 M☉"
      }),
      stage("Ic超新星+黑洞", EPI, "爆发瞬间", 9, "视界≥9km", "bh-face.png", {
        sn: true, note: "黑洞 >3 M☉，正面对吸积盘"
      })
    ]
  },
  O9: {
    id: "O9", cost: 135, title: "藏青星 O9", color: "藏青深蓝",
    mass: "25–35 M☉；黑洞 >5 M☉",
    density: "不形成大红超巨星",
    aliases: ["O9", "O9型", "藏青星"],
    endingText: "Ic 极超新星加黑洞，视界 ≥15 km。吸积盘取侧视（边缘对向）。30 秒后白闪，黑洞消失。",
    remnant: { kind: "bh", bh: "bh-edge.png", left: "Ic极超新星+黑洞", right: "黑洞" },
    stages: [
      stage("藏青深蓝主序星", 3.5e6, "350万年", 22270000, "1670万–2784万km", "star-o9.png", {
        filter: "saturate(1.2) hue-rotate(16deg) brightness(0.8)", note: "质量 25–35 M☉"
      }),
      stage("SGB", 6e5, "60万年", 38280000, "2784万–4872万km", "star-o9.png", { note: "核心氢耗尽" }),
      stage("HG", 1.5e5, "15万年", 93860000, "4872万–1.39亿km", "star-b0.png", { note: "不形成大红超巨星" }),
      stage("蓝超巨星", 2.5e5, "25万年", 278500000, "1.39亿–4.18亿km", "star-b5.png", { note: "质量 15–25 M☉" }),
      stage("WR", 8e4, "8万年", 69600000, "4176万–9744万km", "star-w.png", {
        jets: true, note: "质量 10–20 M☉，双向喷流"
      }),
      stage("硅燃烧前身", 2e4, "数万年", 50000000, "致密前身", "star-o5.png", { note: "铁核 1.5–2 M☉" }),
      stage("Ic极超新星+黑洞", EPI, "爆发瞬间", 15, "视界≥15km", "bh-edge.png", {
        sn: true, note: "黑洞 >5 M☉，侧视吸积盘"
      })
    ]
  },
  O5: {
    id: "O5", cost: 150, title: "纯蓝星 O5", color: "纯蓝",
    mass: "35–50 M☉；黑洞 >8 M☉",
    density: "高光度星风",
    aliases: ["O5", "O5型", "纯蓝星"],
    endingText: "极超新星加大质量黑洞，视界 ≥24 km，侧视吸积盘。30 秒后白闪消失。",
    remnant: { kind: "bh", bh: "bh-edge.png", left: "极超新星+大质量黑洞", right: "黑洞" },
    stages: [
      stage("纯蓝主序星", 1.5e6, "150万年", 33410000, "2784万–3898万km", "star-o5.png", { note: "质量 35–50 M☉" }),
      stage("SGB", 2.5e5, "25万年", 55680000, "4176万–6960万km", "star-o5.png", { note: "核心氢耗尽" }),
      stage("HG", 6e4, "6万年", 139300000, "6960万–2.09亿km", "star-b0.png", { note: "快速膨胀" }),
      stage("蓝超超巨星", 1.2e5, "12万年", 383000000, "2.09亿–5.57亿km", "star-b5.png", { note: "质量 20–35 M☉" }),
      stage("高光度WR WN→WC", 4e4, "4万年", 90340000, "5568万–1.25亿km", "star-w.png", {
        jets: true, filter: "contrast(1.2) brightness(1.1)",
        note: "质量 15–30 M☉，双向宇宙级喷流"
      }),
      stage("硅燃烧前身", 2e4, "数万年", 60000000, "致密前身", "star-o2.png", { note: "铁核 1.5–2.5 M☉" }),
      stage("极超新星+大质量黑洞", EPI, "爆发瞬间", 24, "视界≥24km", "bh-edge.png", {
        sn: true, note: "黑洞 >8 M☉，侧视吸积盘"
      })
    ]
  },
  O2: {
    id: "O2", cost: 180, title: "墨蓝星 O2", color: "墨蓝",
    mass: "50–80 M☉",
    density: "极高光度，正负电子对隐患",
    aliases: ["O2", "O2型", "墨蓝星", "超热主序星"],
    endingText: "每次推演掷一次：90% 核心坍缩成巨型黑洞（侧视，视界 ≥44 km），残骸屏 30 秒后白闪消失；10% 对不稳定极超新星把星体撕碎，只留星云，没有致密残骸。",
    branches: {
      p: 0.9,
      collapse: {
        stage: stage("核心坍缩+巨型黑洞", EPI, "爆发瞬间", 44, "视界≥44km", "bh-edge.png", {
          sn: true, note: ">15 M☉，侧视吸积盘"
        }),
        remnant: { kind: "bh", bh: "bh-edge.png", left: "核心坍缩+巨型黑洞", right: "黑洞" }
      },
      disrupt: {
        stage: stage("对不稳定极超新星", EPI, "爆发瞬间", 400000000, "星体被撕碎", "star-o9.png", {
          sn: true, note: "彻底撕碎，留下星云，无致密残骸"
        })
      }
    },
    stages: [
      stage("墨蓝超热主序星", 7e5, "70万年", 41760000, "3480万–4872万km", "star-o2.png", { note: "质量 50–80 M☉" }),
      stage("SGB", 1.2e5, "12万年", 76560000, "5568万–9744万km", "star-o2.png", { note: "核心氢耗尽" }),
      stage("HG", 3e4, "3万年", 187700000, "9744万–2.78亿km", "star-o5.png", { note: "几乎不泛红" }),
      stage("墨蓝极超巨星", 5e4, "5万年", 487000000, "2.78亿–6.96亿km", "star-lbv.png", { note: "质量 30–60 M☉" }),
      stage("超大质量WC WR", 1.5e4, "1.5万年", 118300000, "6960万–1.67亿km", "star-w.png", {
        jets: true, note: "质量 20–50 M☉"
      }),
      stage("重核燃烧前身", 1e4, "数千年–数万年", 80000000, "仍很庞大", "star-o2.png", {
        note: "质量 15–40 M☉，铁核 1.5–2.5 M☉，正负电子对隐患"
      })
    ]
  },
  W: {
    id: "W", cost: 200, title: "沃尔夫-拉叶星 W", color: "极蓝",
    mass: "80–150 M☉；黑洞 >15 M☉",
    density: "主序 0.1–0.2 g/cm³",
    aliases: ["W", "沃尔夫-拉叶", "沃尔夫拉叶", "沃尔夫拉叶星", "沃尔夫", "WR", "W型"],
    endingText: "Ic 极超新星加大质量黑洞，视界 ≥44 km。残骸屏 30 秒后白闪，黑洞消失。兑换码可免质量解锁。",
    remnant: { kind: "bh", bh: "bh-face.png", left: "Ic极超新星+大质量黑洞", right: "黑洞" },
    stages: [
      stage("极蓝主序星", 5e5, "50万年", 59160000, "4872万–6960万km", "star-w.png", {
        note: "质量 80–150 M☉，密度 0.1–0.2 g/cm³"
      }),
      stage("强星风亚巨星", 8e4, "8万年", 104300000, "6960万–1.39亿km", "star-w.png", {
        jets: true, note: "质量 70–130 M☉"
      }),
      stage("HG", 2e4, "2万年", 208500000, "1.39亿–2.78亿km", "star-b0.png", { note: "质量 60–120 M☉" }),
      stage("蓝回圈蓝超巨星", 1.2e5, "12万年", 208500000, "1.39亿–2.78亿km", "star-b5.png", { note: "质量 50–100 M☉" }),
      stage("WN", 1e5, "10万年", 125260000, "8352万–1.67亿km", "star-w.png", {
        jets: true, note: "氮序沃尔夫-拉叶。质量 40–80 M☉"
      }),
      stage("WC", 4e4, "4万年", 97300000, "6960万–1.25亿km", "star-o9.png", {
        jets: true, filter: "contrast(1.15)", note: "碳序。质量 30–60 M☉"
      }),
      stage("多层壳超新星前身", 5e3, "数千年", 80000000, "多层壳", "star-o5.png", {
        note: "质量 20–40 M☉，铁核 2–2.5 M☉"
      }),
      stage("Ic极超新星+大质量黑洞", EPI, "爆发瞬间", 44, "视界≥44km", "bh-face.png", {
        sn: true, note: "黑洞 >15 M☉"
      })
    ]
  },
  LBV: {
    id: "LBV", cost: 300, title: "高光度蓝变星 LBV / WO", color: "极蓝",
    mass: "150–300 M☉；黑洞 >25 M☉",
    density: "极强星风与抛射",
    aliases: ["LBV", "WO", "高光度蓝变星", "亮蓝变星", "高光度蓝变星WO", "WO星"],
    endingText: "WO 是这条轨道上的富氧沃尔夫-拉叶阶段，不是另一条主序。每次推演掷一次：95% 坍缩成超大质量黑洞（视界 ≥74 km），白闪后消失；5% 对不稳定超新星撕碎恒星，留下巨型星云。兑换码同时解锁 W 与 WO。",
    branches: {
      p: 0.95,
      collapse: {
        stage: stage("坍缩+超大质量黑洞", EPI, "爆发瞬间", 74, "视界≥74km", "bh-face.png", {
          sn: true, note: ">25 M☉"
        }),
        remnant: { kind: "bh", bh: "bh-face.png", left: "坍缩+超大质量黑洞", right: "黑洞" }
      },
      disrupt: {
        stage: stage("对不稳定撕碎", EPI, "爆发瞬间", 500000000, "巨型星云", "star-lbv.png", {
          sn: true, note: "无致密残骸"
        })
      }
    },
    stages: [
      stage("极蓝特超巨星主序", 2.5e5, "25万年", 83520000, "6960万–9744万km", "star-lbv.png", {
        note: "质量 150–300 M☉"
      }),
      stage("LBV爆发抛射", 8e4, "8万年", 180760000, "8352万–2.78亿km", "star-b5.png", {
        note: "质量 100–200 M☉，亮度不规则起伏"
      }),
      stage("蓝回圈极超巨星", 5e4, "5万年", 208500000, "1.39亿–2.78亿km", "star-b0.png", { note: "质量 80–150 M☉" }),
      stage("WO富氧WR", 2e4, "2万年", 104260000, "8352万–1.25亿km", "star-o5.png", {
        jets: true, filter: "contrast(1.25) brightness(1.05)",
        note: "极强氧碳线，喷流可达 0.1c。质量 50–100 M☉"
      }),
      stage("重核燃烧前身", 5e3, "数千年", 70000000, "致密前身", "star-o2.png", {
        note: "质量 30–60 M☉，铁核 2.5–3 M☉"
      })
    ]
  }
};

const CLASS_LIST = ["L", "M9", "M0", "K", "G", "F", "A", "B9", "B5", "B0", "O9", "O5", "O2", "W", "LBV"];

const WHEEL_SECTORS = [
  { label: "质量-15", delta: -15, color: "#37c43a" },
  { label: "谢谢光临", delta: 0, color: "#3aa6e6" },
  { label: "质量-5", delta: -5, color: "#ff8ec2" },
  { label: "质量+10", delta: 10, color: "#ffe34a" },
  { label: "质量+80", delta: 80, color: "#ff3d86" },
  { label: "质量+35", delta: 35, color: "#37c43a" },
  { label: "质量+10", delta: 10, color: "#3aa6e6" },
  { label: "谢谢光临", delta: 0, color: "#ff8ec2" },
  { label: "质量+10", delta: 10, color: "#ffe34a" },
  { label: "质量+180", delta: 180, color: "#ff2e2e" }
];

const CODES = {
  "这个就不告诉你了": { kind: "mass", amount: 120, text: "质量 +120 ☀️" },
  "VIP666": { kind: "spins", amount: 20, text: "免广告免费转动 +20" },
  "WR102最热！": { kind: "credits", amount: 200000, text: "讲解额度 +200000" },
  "来自中原的一群伙伴": { kind: "mass", amount: 1800, text: "质量 +1800 ☀️" },
  "HXGP20261001": { kind: "unlock", ids: ["W", "LBV"], text: "已永久解锁 W 与 WO" }
};

function normQuery(raw) {
  return String(raw || "").trim().replace(/\s+/g, "");
}

function resolveQuery(raw) {
  const q = normQuery(raw);
  if (!q) return null;
  const up = q.toUpperCase();
  for (const id of CLASS_LIST) {
    for (const alias of CLASSES[id].aliases) {
      if (alias.toUpperCase() === up || alias === q) return id;
    }
  }
  if (/^\d+$/.test(q)) {
    const n = Number(q);
    const hit = CLASS_LIST.find((id) => CLASSES[id].cost === n);
    if (hit) return hit;
  }
  return null;
}

function fmtDiam(km) {
  if (km >= 1e8) {
    const v = km / 1e8;
    return (Math.round(v * 100) / 100) + "亿km";
  }
  if (km >= 10000) {
    const v = km / 10000;
    return (Math.round(v * 10) / 10) + "万km";
  }
  return Math.round(km) + "km";
}

function stageLines(spec) {
  const lines = spec.stages.map((s, i) => `${i + 1}. ${s.name}（${s.dur}，直径 ${s.diamText}）${s.note ? "：" + s.note : ""}`);
  if (spec.branches) {
    lines.push(`终局分支 ${Math.round(spec.branches.p * 100)}%：${spec.branches.collapse.stage.name}（${spec.branches.collapse.stage.note}）`);
    lines.push(`终局分支 ${Math.round((1 - spec.branches.p) * 100)}%：${spec.branches.disrupt.stage.name}（${spec.branches.disrupt.stage.note}）`);
  }
  return lines.join("\n");
}

function summary(spec) {
  return `${spec.title}，解锁消耗 ${spec.cost} ☀️。主序颜色${spec.color}，质量 ${spec.mass}，密度 ${spec.density}。阶段：${spec.stages.map((s) => s.name).join(" → ")}${spec.branches ? " → 终局分支" : ""}。${spec.endingText}`;
}

function mentionedClasses(q) {
  const n = normQuery(q);
  const up = n.toUpperCase();
  const ids = [];
  const add = (id) => { if (!ids.includes(id)) ids.push(id); };
  if (/高光度蓝变|亮蓝变|LBV/i.test(n)) add("LBV");
  if (/WO/i.test(up)) add("LBV");
  if (/沃尔夫/.test(n) || /WR/i.test(up)) add("W");
  if (/O2/i.test(up)) add("O2");
  if (/O5/i.test(up)) add("O5");
  if (/O9/i.test(up)) add("O9");
  if (/B0/i.test(up)) add("B0");
  if (/B5/i.test(up)) add("B5");
  if (/B9/i.test(up)) add("B9");
  if (/M0/i.test(up)) add("M0");
  if (/M9/i.test(up)) add("M9");
  if (/褐矮/.test(n)) add("L");
  if (/红矮/.test(n) && !/晚型|暗红|极冷/.test(n)) add("M9");
  if (/橙矮/.test(n)) add("K");
  if (/黄矮|类太阳|太阳型|类日/.test(n)) add("G");
  if (/黄白/.test(n)) add("F");
  if (/白色主序|纯白主序|A型/.test(n)) add("A");
  const stripped = up.replace(/O2|O5|O9|B0|B5|B9|M0|M9|LBV|WO|WR/g, " ");
  const has = (ch) => new RegExp("(^|[^A-Z])" + ch + "([^A-Z]|$)").test(stripped);
  if (has("L")) add("L");
  if (has("K")) add("K");
  if (has("G")) add("G");
  if (has("F")) add("F");
  if (has("A")) add("A");
  if (has("W")) add("W");
  return ids;
}

function answerLecturer(raw, state) {
  const q = normQuery(raw);
  if (!q) return "你猜";
  const up = q.toUpperCase();

  if (q.includes("这个就不告诉你了")) return "这句暗语的效果是质量 +120 ☀️。到左上角兑换才会入账。";
  if (up.includes("VIP666")) return "VIP666 的效果是免广告免费转动 +20。到左上角兑换才会入账。";
  if (q.includes("WR102最热")) return "这条码的效果是讲解额度 +200000。本讲解不扣次数，额度会记在存档里。";
  if (q.includes("来自中原的一群伙伴")) return "这句的效果是质量 +1800 ☀️。到左上角兑换才会入账。";
  if (up.includes("HXGP20261001")) return "HXGP20261001 会永久解锁 W 和 WO（LBV 轨道），不用支付质量。";

  const off = /吃|喝|天气|股票|电影|足球|篮球|音乐|睡觉|笑话|政治|新闻|恋爱|漂亮|你好|你是谁|几岁|饭|奶茶|游戏推荐/;
  const game = /恒星|光谱|转盘|解锁|演化|质量|白矮|黑洞|中子|超新星|褐矮|红矮|沃尔夫|兑换|阶段|密度|直径|喷流|星风|氦|蓝回|残体|主序|星云|坍缩|塌缩|对不稳定|视界|造父|光度|对流|氘|太阳|广告|免费|转动|抽奖|讲解|沉寂|星风|硅|铁核|团簇|亚巨星|超巨星|奖|扇|格|码/;
  if (off.test(q) && !game.test(q) && mentionedClasses(q).length === 0) return "扎啤吧";

  if (/精确温度|开尔文|金属丰度|色指数|磁场|自转周期|视星等|发现者|波长/.test(q)) return "你猜";

  if (/兑换码|兑换|暗语|礼包码/.test(q)) {
    return "兑换码写在左上角，立刻生效，每个码只能用一次。效果有：增加太阳质量、增加 20 次免广告转动、增加 20 万次讲解额度、永久解锁 W 与 WO。其中一句暗语我不会主动写出来；你要是已经把那句话打在问题里，我可以告诉你它做什么。";
  }

  if (/转盘|抽奖|幸运转|奖品|扇区|格子/.test(q)) {
    const labels = WHEEL_SECTORS.map((s) => s.label).join("、");
    return `幸运大转盘固定不转，虚线箭头绕着中间五个字转 5 秒。起步每 0.5 秒一圈，然后减速，停在哪一格就是哪一格。顺时针从顶上起：${labels}。增加的质量直接加上；谢谢光临质量不变；减少的质量如果会变成负数，就归零。上海时间每个自然日 3 次免费，另外的免广告次数用完之后，再转要先看大约 3 秒、可以跳过的广告。`;
  }

  if (/免费|每天|广告|还能转|次数/.test(q) && /转|抽|盘|广告|免费/.test(q)) {
    return "按亚洲/上海的日历日计算，每天 3 次免费转动。当天用完后，再转需要看一段约 3 秒、可跳过的广告。兑换得到的免广告次数单独计算，用完才进入广告。";
  }

  if (/当前质量|我的质量|现在多少质量|质量是多少|还有多少质量/.test(q) && !mentionedClasses(q).length) {
    return `你现在的质量是 ${state.mass} ☀️。质量存在本机，刷新不会丢。`;
  }

  if (/解锁了什么|已经解锁|哪些解锁|永久解锁/.test(q) && !mentionedClasses(q).length) {
    const got = CLASS_LIST.filter((id) => state.unlocks[id]);
    if (!got.length) return "还没有永久解锁任何光谱型。搜索光谱型并付质量，或者使用解锁码。";
    return "已经永久解锁：" + got.join("、") + "。再搜它们可以直接推演，不用再付质量。";
  }

  if (/氦闪/.test(q)) {
    return "氦闪发生在低质量红巨星顶端：M9、M0、K、G 会氦闪。F 型红巨星明确无氦闪，更重的星氦是安静点燃的。氦闪之后，M0 的水平分支是红团簇，没有蓝回圈；K 和 G 的水平分支里各有一段较短的蓝回圈。";
  }
  if (/蓝回圈|蓝环/.test(q)) {
    return "蓝回圈是水平分支或蓝超巨星阶段往蓝端走再回来。M0 红团簇没有蓝回圈。K 的红团簇里蓝回圈约 4000 万年，G 约 1500 万年。F、A 有独立的蓝回圈阶段，也是造父脉动所在。B9、B5、B0、W、LBV 的大质量星也会蓝回圈，但那是蓝超巨星，不是低质量水平分支。";
  }
  if (/白矮/.test(q) && !mentionedClasses(q).length) {
    return "M9 留下氦白矮星。M0、K、G 留下碳氧白矮星。F 在高质量端是氧氖镁白矮星、低质量端是碳氧白矮星。A 留下氧氖镁白矮星。白矮星出现后会在残骸屏里用 30 秒冷却成暗沉残体。L 不形成白矮星，而是褐矮星直接沉寂。B 型及以上不走白矮星。";
  }
  if (/中子星/.test(q) && !mentionedClasses(q).length) {
    return "本推演里只有 B9 和 B5 留下中子星：B9 是核心坍缩超新星，B5 是 Ib/Ic 超新星，残留都是 1.44–3 M☉、直径 20–30 km。残骸屏里中子星先自转，再在 30 秒里冷却成暗灰小球。B0 及更重的星留下黑洞，不是中子星。";
  }
  if (/黑洞/.test(q) && !mentionedClasses(q).length) {
    return "B0、O9、O5、W，以及 O2 的 90% 支、LBV 的 95% 支，终局是黑洞。B0 和 W、LBV 坍缩支用正面对的吸积盘；O9、O5 和 O2 坍缩支用侧视吸积盘。黑洞在残骸屏停 30 秒，然后白闪、洞消失，回到首页。对不稳定支不会留下黑洞。";
  }
  if (/对不稳定|撕碎|无致密/.test(q)) {
    return "只有 O2 和 LBV/WO 有对不稳定支。O2 每次推演 10% 概率被极超新星彻底撕碎，只留星云；LBV 是 5%。其余概率坍缩成黑洞。撕碎的那一支没有致密残骸，星云闪过之后直接回首页。";
  }
  if (/沃尔夫|WR|星风|喷流/.test(q) && !mentionedClasses(q).length) {
    return "星风剥掉氢包层之后才进入沃尔夫-拉叶。B0 及更热的星会经历 WR：裸露氦、碳、氮，常常带双向喷流。W 型本身从极蓝主序走到 WN 再走到 WC。LBV 轨道的 WO 阶段富氧，喷流可达 0.1c。搜索 W 或 WO/LBV 可以推演，首页列表里不显示它们。";
  }
  if (/主序/.test(q) && /耗尽|区别|下一|SGB|次巨星/.test(q)) {
    return "主序阶段核心在烧氢。核心氢耗尽后进入次巨星 SGB：核心收缩，壳层氢燃烧，恒星变亮变大。再往后低质量星慢慢爬上红巨星，大质量星可能直接成为蓝超巨星或被星风剥成沃尔夫-拉叶，而不形成大红超巨星。O9 明确不形成大红超巨星。";
  }

  const ids = mentionedClasses(q);
  if (ids.length >= 2) {
    return ids.map((id) => {
      const s = CLASSES[id];
      return `${s.id}：解锁 ${s.cost} ☀️，${s.color}，质量 ${s.mass}。${s.endingText}`;
    }).join("\n");
  }
  if (ids.length === 1) {
    const spec = CLASSES[ids[0]];
    if (/阶段|演化|顺序|寿命|过程|怎么走|生命/.test(q)) return `${spec.title}的阶段：\n${stageLines(spec)}\n${spec.endingText}`;
    if (/解锁|花费|消耗|要多少|价钱|价格/.test(q)) return `${spec.title}永久解锁需要 ${spec.cost} ☀️。${state.unlocks[spec.id] ? "你已经解锁了，可以免费再推演。" : "质量不够时确定不会扣，也不会解锁。"}`;
    if (/密度/.test(q)) return `${spec.title}的密度：${spec.density}。`;
    if (/直径|半径|多大|多宽/.test(q)) return `${spec.title}各阶段直径：\n` + spec.stages.map((s) => `${s.name} ${s.diamText}`).join("；");
    if (/质量范围|多重|初始质量|多少太阳|多少倍/.test(q)) return `${spec.title}的质量：${spec.mass}。解锁花费是另一回事，要 ${spec.cost} ☀️。`;
    if (/结局|残骸|最后|死亡|变成|终局/.test(q)) return spec.endingText;
    if (/颜色|看起来|长什么样/.test(q)) return `${spec.title}主序是${spec.color}。后面的阶段会膨胀、变色，再收缩到结局。`;
    return summary(spec);
  }

  if (game.test(q) || /[OBAFGKMLW]/.test(up)) return "你猜";
  return "扎啤吧";
}
