// Crazy3DS 美女提示词大师 (v69) —— 商业人像级自定义 DOM 面板
// 1) 五档摄影套系模式 + 已锁/变化双色徽章 + 实时段号回显 + 一键重置
// 2) 26 类服装主题细分自动联动过滤（选现代只看现代子主题，选古风只看古风子主题）
// 3) 互斥参数自动置灰 + 悬停高亮冲突原因
// 4) 参数标题两端对齐 + 面板留白 6px + 中键可在面板上直接拖动画布
// 5) 数量为「左右箭头 + 中间数值」步进框，可长按连续加减
// 6) 相机滤镜自定义下拉：悬停即时弹出 16×16 色彩/特效预览
// 7) 零内部滚动条 + 支持自由拖拽缩放节点宽高

function appSources() {
  const out = [];
  if (typeof window === "undefined") return out;
  if (window.app) out.push(["window.app", window.app]);
  const capi = window.comfyAPI;
  if (capi && capi.app && capi.app.app) out.push(["comfyAPI.app.app", capi.app.app]);
  return out;
}

function appSync() {
  if (globalThis.__c3dsAppOverride) return globalThis.__c3dsAppOverride;
  for (const [src, a] of appSources()) {
    if (a && typeof a.registerExtension === "function") {
      if (!appSync.logged) {
        appSync.logged = true;
        console.log("[Crazy3DS PromptMaster] app 来源:", src);
      }
      return a;
    }
  }
  return null;
}

const APP_CANDIDATES = [
  "../../scripts/app.js",
  "../../../scripts/app.js",
  "/scripts/app.js",
];

async function appAsync() {
  for (let i = 0; i < 200; i++) {
    const a = appSync();
    if (a) return a;
    await new Promise((r) => setTimeout(r, 50));
  }
  for (const path of APP_CANDIDATES) {
    try {
      const mod = await import(/* @vite-ignore */ path);
      if (mod?.app && typeof mod.app.registerExtension === "function") {
        return mod.app;
      }
    } catch (_) {}
  }
  return null;
}

let APP = null;

const TARGET_NODES = new Set(["Crazy3DS_PairPromptPlus", "美女提示词PLUS"]);
const P = "c3ds-mpp";
const KEEP_NATIVE = new Set(["随机种子", "control_after_generate", "生成后控制"]);

const MIN_WIDTH = 340;
const DEFAULT_WIDTH = 400;
const TOTAL_SEGMENTS = 50000;

/* ---------------------------------------------------------------- 默认值表（供一键重置） */
const DEFAULTS = {
  "穿衣服": true,
  "场景偏好": "不限",
  "数量": 4,
  "生成模式": "写真套图",
  "姿势去重": true,
  "景别轮转": true,
  "罩杯": "B~C随机",
  "领口": "跟随服装",
  "锁定身材": true,
  "美姿机位": true,
  "露肤度": "关闭",
  "服装风格": "现代",
  "主题细分": "自动随机",
  "发型": "跟随服装",
  "发色": "跟随发型",
  "光影氛围": "跟随场景",
  "情绪眼神": "自然随机",
  "相机滤镜": "关闭",
  "滤镜强度": "强",
  "编号": true,
  "追加词": "",
  "保存txt": false,
};

/* ---------------------------------------------------------------- 模式锁定语义说明
   仅「已锁 / 变化」两个标题保留图标，其余条目标签一律纯文字，避免图标挤在一起分不清。 */
const MODE_META = {
  "盲盒抽卡": {
    locked: ["无（全部随机）"],
    changed: ["人物", "服装", "场景", "姿势", "机位"],
    tip: "【盲盒抽卡】（原：完全随机）\n每张图都是全新的模特、穿搭、场景与动作，适合快速测试灵感。",
  },
  "模特换装": {
    locked: ["人物"],
    changed: ["服装", "场景", "姿势", "机位"],
    tip: "【模特换装】（原：同人不同姿势）\n固定同一个模特（脸/发型/肤色/身材不变），去不同场景换穿不同衣服摆拍。",
  },
  "旅拍转场": {
    locked: ["人物", "服装"],
    changed: ["场景", "姿势", "机位"],
    tip: "【旅拍转场】（新增高频模式）\n固定同一个模特和同一套穿搭，穿梭在不同场景中摆拍，适合故事感外景分镜。",
  },
  "写真套图": {
    locked: ["人物", "服装", "场景"],
    changed: ["姿势", "机位"],
    tip: "【写真套图】（原：同场景不同姿势）\n固定模特、服装和当前场景，围绕人物切换不同机位与动作拍出一套写真。",
  },
  "定点连拍": {
    locked: ["人物", "服装", "场景", "机位"],
    changed: ["姿势"],
    tip: "【定点连拍】（原：只变姿势）\n三脚架固定机位（人/衣/景/机位角度全锁死），模特在镜头前连续换动作，适合做视频首尾帧或动作表。",
  },
};

/* ---------------------------------------------------------------- 悬停说明文案 */
const TIPS = {
  "穿衣服":
    "开 = 有衣服，关 = 没衣服。\n" +
    "同一种子（段号）下场景、姿势、机位完全一致，只换服装。\n" +
    "关掉后「领口 / 露肤度」自动置灰；「罩杯」在有衣/无衣下均生效。",
  "场景偏好": "筛选最终场景（不限 / 室内 / 户外）。\n泳装触发的水景、礼服触发的厅堂、婚纱触发的礼堂都严格遵守此偏好。",
  "数量": "一次输出几条提示词（1-200）。\n左右箭头单步加减，长按可连续加减。\n提示词列表口可直接连 CLIP Text Encode 自动出 N 张图。",
  "生成模式":
    "五档商业摄影套系模式：\n" +
    "• 盲盒抽卡：人/衣/景/姿/镜全变\n" +
    "• 模特换装：锁人，换衣换景\n" +
    "• 旅拍转场：锁人+锁衣，换场景\n" +
    "• 写真套图：锁人+锁衣+锁景，换姿势与机位\n" +
    "• 定点连拍：人/衣/景/机位全锁，只换动作",
  "姿势去重": "开 = 同一批里姿势绝不重复（五档模式全部生效）。\n关 = 允许重复。",
  "景别轮转":
    "开 = 景别按 全身 / 七分身 / 半身 / 远景 / 中全景 依次轮转（所有模式下均生效）。\n" +
    "关 = 整批保持同一个景别。\n" +
    "想做「绝对同一机位」的定点连拍，可把它关掉，景别也会一起锁死。",
  "罩杯":
    "穿衣版描述「隔着布料的胸型轮廓」，无衣版描述「自然胸型」，两个版本均生效。\n" +
    "选「关闭」时使用自然匀称体态描述，不再强调胸围。",
  "领口":
    "跟随服装 = 按单品自动判断。\n" +
    "古风模式下会自动将领口映射为交领/坦领/诃子抹胸，不会串味。\n" +
    "「露肤度」开启时，高领 / 圆领会自动置灰。",
  "锁定身材":
    "开 = 整批锚定同一套身高骨架（160/165/170cm），避免忽高忽低。\n" +
    "盲盒模式下仅锁身高体态，不锁五官与发型。",
  "美姿机位": "开 = 切换为显腿长、显比例的人像摄影机位池，过滤俯拍/仰拍，并自动根據景别匹配 35mm/50mm/85mm 镜头。",
  "露肤度": "关闭 / 微露 / 适中。\n优先于「领口」：开启露肤度后，高领 / 圆领会自动退回「跟随服装」。\n没衣服时自动置灰。",
  "服装风格": "现代 / 古风。\n服装池与场景池物理隔离，古风绝不会抽到现代街景或酒店大堂。",
  "主题细分":
    "26 档主题：\n" +
    "现代 15 档：日常穿搭 / 纯欲御姐 / 通勤OL / 私密居家 / 运动休闲 / 甜酷街头 / 泳装度假 / 晚礼服 /\n" +
    "新中式旗袍 / 校园清纯 / 法式优雅 / 街头机能 / 婚纱白纱 / 度假亚麻 / 暗夜酷感\n" +
    "古风 10 档：华丽宫廷 / 清雅书卷 / 飒爽侠女 / 妩媚风情 / 魏晋宽袖 / 飘逸仙侠 /\n" +
    "婚嫁红妆 / 异域胡旋 / 禅意道袍 / 女扮男装\n" +
    "每个主题都带场景倾向，不会出现「泳装逛超市」这种串味。",
  "发型": "跟随服装（推荐）= 现代装抽现代发型、古风装自动配古风发髻，杜绝穿汉服顶波波头。\n也可手动指定 经典 / 现代 / 古风。",
  "发色": "跟随发型 = 不额外加染发描述；现代 / 古风 = 从对应色板随机取色。",
  "光影氛围": "跟随场景 = 自动识别白天/夜景/日落匹配合理光效（夜景不再发灰）。\n也可强制指定自然柔光、落日逆光、暗调情绪、闪光直打、霓虹夜景。",
  "情绪眼神": "控制模特的面部微表情与视线互动（直视互动、松弛抓拍、清冷高级、温婉甜美、微醺慵懒）。",
  "相机滤镜":
    "叠加真实相机的色彩科学与滤镜质感：\n" +
    "• 佳能 R5 / 5D4：奶油肤色、胶片暖调\n" +
    "• 尼康 Z8 / D850：通透中性、高解析\n" +
    "• 索尼 A7RV / A7M4：锐利清冷、电影青橙\n" +
    "• 富士 XT5 / X100VI / GFX100：Classic Chrome / Classic Neg / Pro Neg\n" +
    "• 徕卡 M11 / SL2：德味浓郁、微反差\n" +
    "• 哈苏 X2D / 飞思 IQ4：中画幅自然肤色、商业级肤色\n" +
    "• 胶片：柯达 Portra400 / Gold200 / Ektar100、富士 Pro400H、CineStill 800T、依尔福 HP5 黑白\n" +
    "• 滤镜：黑柔 1/4、白柔 Glimmerglass、柔焦 Softar、星光镜\n" +
    "选「关闭」= 只输出焦段与光影描述。\n" +
    "下拉里把鼠标移到任一选项上，右侧会弹出 16×16 色彩/特效预览方块；\n" +
    "右侧 🎲 随机抽一支滤镜；旁边的「滤镜强度」控制描述浓度（弱/中/强）。",
  "滤镜强度":
    "调的是「描述浓度」，不是模型强度：\n" +
    "弱 = 只保留一句核心色彩科学 + subtle（不加颗粒、光晕、散景等特征）；\n" +
    "中 = 核心 + 前 2 个特征（多为对比 / 肤色 / 高光）；\n" +
    "强 = 全部特征（等同旧版默认效果）。\n" +
    "黑柔 / 白柔 / 柔焦 / 星光会随强度切换真实密度：\n" +
    "黑柔 1/8 → 1/4、Glimmerglass 2 → 4、Softar I → III、星芒 4 → 8 线。\n" +
    "滤镜选「关闭」时此项不生效。",
  "编号": "开 = 「段信息」和保存的 txt 每行带 #01 前缀。\n「提示词」列表输出口永远保持纯净无前缀，不污染 CLIP。",
  "追加词": "非空时拼在每条提示词最末尾。\n例：film grain, Fujifilm XT4, bokeh",
  "保存txt": "开 = 额外落盘一份到 output/crazy3ds_pair_XXXXX_NN_clothed.txt。",
};

/* ---------------------------------------------------------------- 相机滤镜色板
   每一项都是对应机身/胶片/滤镜的代表性色彩倾向，用于下拉选项与悬停预览方块。 */
const FILTER_SWATCH = {
  "关闭": "repeating-linear-gradient(45deg, #4a4a52 0 3px, #26262c 3px 6px)",
  "佳能 R5·奶油肤色": "linear-gradient(135deg, #ffe9d8 0%, #ffd0ae 55%, #e8a985 100%)",
  "佳能 5D4·胶片暖调": "linear-gradient(135deg, #ffe3c4 0%, #e8bf8f 50%, #b98a5c 100%)",
  "尼康 Z8·通透中性": "linear-gradient(135deg, #eef1f4 0%, #cfd6dc 50%, #a8b2ba 100%)",
  "尼康 D850·高解析": "linear-gradient(135deg, #e6ebef 0%, #c2cbd3 50%, #98a4ae 100%)",
  "索尼 A7RV·锐利清冷": "linear-gradient(135deg, #dff1f7 0%, #a9cdd9 50%, #6f96a6 100%)",
  "索尼 A7M4·电影青橙": "linear-gradient(135deg, #0f5f6b 0%, #1f8a8f 45%, #d97b34 100%)",
  "富士 XT5·Classic Chrome": "linear-gradient(135deg, #b9c3c2 0%, #8e9a9b 50%, #6f7f86 100%)",
  "富士 X100VI·Classic Neg": "linear-gradient(135deg, #f0c986 0%, #9aa47f 50%, #3f5a58 100%)",
  "富士 GFX100·Pro Neg 柔肤": "linear-gradient(135deg, #f6e3e0 0%, #dcc9cd 50%, #b7b0bb 100%)",
  "徕卡 M11·德味浓郁": "linear-gradient(135deg, #e6b98f 0%, #b5694f 50%, #6d3326 100%)",
  "徕卡 SL2·微反差": "linear-gradient(135deg, #e4e2dd 0%, #b3b0a9 50%, #7d7a74 100%)",
  "哈苏 X2D·中画幅自然": "linear-gradient(135deg, #f3e7d8 0%, #d8c6ae 50%, #b09a80 100%)",
  "飞思 IQ4·商业肤色": "linear-gradient(135deg, #fbf1ea 0%, #e8d2c4 50%, #c9ada0 100%)",
  "柯达 Portra400·柔肤": "linear-gradient(135deg, #fde6d6 0%, #f2c9b2 50%, #d8a48c 100%)",
  "柯达 Gold200·暖黄怀旧": "linear-gradient(135deg, #ffe9a8 0%, #f5c96b 50%, #c9913c 100%)",
  "富士 Pro400H·青调柔肤": "linear-gradient(135deg, #e6f6f0 0%, #c3e3d7 50%, #93bfb4 100%)",
  "CineStill800T·夜景钨丝": "linear-gradient(135deg, #14346b 0%, #2a6f9e 45%, #d4442f 100%)",
  "柯达 Ektar100·高饱和": "linear-gradient(135deg, #e33f2f 0%, #e0a03a 50%, #2456a8 100%)",
  "依尔福 HP5·黑白颗粒": "linear-gradient(135deg, #dcdcdc 0%, #8b8b8b 50%, #2e2e2e 100%)",
  "黑柔 1/4·Black Mist": "radial-gradient(circle at 30% 30%, #fff8e0 0%, #ffe6a6 22%, #3a3a44 66%, #101014 100%)",
  "白柔·Glimmerglass": "radial-gradient(circle at 35% 35%, #ffffff 0%, #f2f4ff 26%, #b9c4d6 62%, #6d778a 100%)",
  "柔焦·Softar 朦胧": "radial-gradient(circle at 50% 50%, #ffffff 0%, #f0e6f2 30%, #c9b6d1 66%, #8f8299 100%)",
  "星光镜·十字星芒": "radial-gradient(circle at 50% 50%, #ffffff 0 18%, #cfe3ff 19%, #22303f 72%)",
};

function swatchFor(name) {
  return FILTER_SWATCH[name] || "linear-gradient(135deg, #9aa0aa 0%, #4a4f58 100%)";
}

/* ---------------------------------------------------------------- 面板分区布局
   pair + cols：显式两列宽度，避免「场景偏好」被挤到换行；gap 独立控制两栏间距。 */
const LAYOUT = [
  {
    title: "套系与批量",
    rows: [
      "生成模式",
      "__mode_badge__",
      { pair: ["场景偏好", "数量"], cols: "minmax(0,1fr) 152px", gap: 18 },
      ["姿势去重", "景别轮转"],
    ],
  },
  {
    title: "造型与风格",
    rows: [
      { pair: ["服装风格", "主题细分"], cols: "minmax(0,0.86fr) minmax(0,1.14fr)", gap: 14 },
      "发型",
      "发色",
    ],
  },
  {
    title: "人物与体态",
    rows: [
      { pair: ["罩杯", "领口"], cols: "minmax(0,1fr) minmax(0,1fr)", gap: 18 },
      "露肤度",
      ["锁定身材", "美姿机位"],
    ],
  },
  {
    title: "摄影与情绪",
    rows: [
      ["光影氛围", "情绪眼神"],
      { pair: ["相机滤镜", "滤镜强度"], cols: "minmax(0,1fr) 120px", gap: 18 },
    ],
  },
  {
    title: "输出与附加",
    rows: [["编号", "保存txt"], "追加词"],
  },
];

/* ---------------------------------------------------------------- 互斥规则 */
const RULES = [
  {
    id: "nude",
    when: (v) => v["穿衣服"] === false,
    disable: ["领口", "露肤度"],
    reason: "无衣模式下「领口 / 露肤度」不参与",
  },
  {
    id: "reveal",
    when: (v) => v["露肤度"] !== undefined && v["露肤度"] !== "关闭",
    guard: (v) => v["穿衣服"] !== false,
    disableOptions: { 领口: ["高领", "圆领"] },
    reason: "已开启露肤度，「高领 / 圆领」自动避让",
    onActive: (v, set) => {
      if (v["领口"] === "高领" || v["领口"] === "圆领") set("领口", "跟随服装");
    },
  },
];

/* ---------------------------------------------------------------- 样式 */
const CSS = `
.${P}-root {
  --${P}-fg: var(--fg-color, #e9e9ef);
  --${P}-bg: var(--comfy-input-bg, #1a1a1f);
  --${P}-bg2: var(--comfy-menu-bg, #282830);
  --${P}-bd: var(--border-color, #383842);
  --${P}-ac: #3b7d59;
  --${P}-ac-fg: #f4fbf7;
  --${P}-ok: #3b7d59;
  --${P}-no: #e0a03a;
  --${P}-labw: 46px;
  --${P}-pad: 6px;
  font: 11px/1.35 ui-sans-serif, system-ui, "Segoe UI", "Microsoft YaHei", sans-serif;
  color: var(--${P}-fg);
  width: 100%;
  overflow: hidden !important;
  padding: 0;
  margin: 0;
  box-sizing: border-box;
  user-select: none;
}
.${P}-root::-webkit-scrollbar { display: none !important; width: 0 !important; height: 0 !important; }
.${P}-root *, .${P}-root *::before, .${P}-root *::after { box-sizing: border-box; }
.${P}-stage {
  padding: 2px var(--${P}-pad) 6px var(--${P}-pad);
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* 顶部工具栏：主开关 + 段号显示 + 重置按钮（主开关也带 56px 标签槽，与其他行完全对齐） */
.${P}-topbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 3px;
}
.${P}-hero { flex: 1 1 auto; min-width: 0; }
.${P}-hero .${P}-seg { padding: 2px; border-radius: 7px; }
.${P}-hero .${P}-seg > button { font-size: 11px; font-weight: 600; padding: 4px 4px; }
.${P}-root.is-nude .${P}-hero .${P}-seg > button.on {
  background: #8e4654; border-color: #8e4654; color: #fff;
}
.${P}-seg-id {
  font-size: 10px;
  font-family: ui-monospace, Consolas, monospace;
  padding: 3px 6px;
  border-radius: 5px;
  background: var(--${P}-bg);
  border: 1px solid var(--${P}-bd);
  opacity: 0.8;
  white-space: nowrap;
}
.${P}-reset {
  border: 1px solid var(--${P}-bd);
  background: var(--${P}-bg);
  color: var(--${P}-fg);
  border-radius: 5px;
  padding: 3px 7px;
  font: inherit;
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  opacity: 0.85;
  white-space: nowrap;
}
.${P}-reset:hover { opacity: 1; background: var(--${P}-bg2); border-color: var(--${P}-ac); }

/* 模式状态徽章：已锁 / 变化 两块独立色块，间距明确 */
.${P}-badge {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 3px 0 4px;
}
.${P}-badge-g {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 9.5px;
  line-height: 1.35;
  white-space: nowrap;
}
.${P}-badge-g > b {
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: .02em;
  margin-right: 2px;
}
.${P}-badge-g.locked {
  background: rgba(59, 125, 89, 0.22);
  border: 1px solid rgba(89, 186, 131, 0.55);
  color: #bdeacf;
}
.${P}-badge-g.changed {
  background: rgba(224, 160, 58, 0.16);
  border: 1px solid rgba(224, 160, 58, 0.5);
  color: #f2d49b;
}

/* 分区标题：灰色系，与正文科技蓝/绿分离 */
.${P}-sec { margin-top: 6px; }
.${P}-sec-t {
  display: flex; align-items: center; gap: 5px;
  font-size: 9px; font-weight: 700; letter-spacing: .12em;
  opacity: 1; color: #8f96a2;
  margin: 0 0 3px; text-transform: uppercase;
}
.${P}-sec-t::after { content: ""; flex: 1; height: 1px; background: #6b7280; opacity: .55; }

/* 行与双列网格 */
.${P}-row {
  display: flex; align-items: center; gap: 4px;
  min-height: 22px; margin: 2px 0;
  transition: opacity .1s ease;
}
.${P}-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 2px 18px;
  align-items: center;
}
.${P}-grid > .${P}-row { min-width: 0; margin: 2px 0; gap: 4px; }
.${P}-grid .${P}-swtxt { display: none; }
.${P}-row.off { opacity: .32; filter: grayscale(1); }
.${P}-lab {
  width: var(--${P}-labw); flex: none;
  display: flex; align-items: center;
  font-size: 10.5px; font-weight: 600; opacity: .96;
  white-space: nowrap; overflow: hidden;
  cursor: help; border-bottom: 1px dotted transparent;
}
/* 标题两端对齐：逐字撑满标签槽，2 字与 4 字标题右边界一致 */
.${P}-lab-t {
  display: flex; width: 100%;
  justify-content: space-between;
}
.${P}-lab:hover { border-bottom-color: var(--${P}-bd); opacity: 1; }
.${P}-ctl { flex: 1; display: flex; align-items: center; min-width: 0; }

/* 分段按钮：按等分铺满一行，绝不换行（column 自动流 + minmax(0,1fr) 平均分） */
.${P}-seg {
  flex: 1; min-width: 0;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(0, 1fr);
  gap: 2px; padding: 1px;
  background: var(--${P}-bg); border: 1px solid var(--${P}-bd); border-radius: 6px;
}
.${P}-seg > button {
  min-width: 0; border: 0; border-radius: 4px;
  background: transparent; color: var(--${P}-fg);
  font: inherit; font-size: 10.5px; font-weight: 500; padding: 2.5px 3px;
  cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.${P}-seg > button:hover:not(:disabled):not(.on) { background: var(--${P}-bg2); }
.${P}-seg > button.on { background: var(--${P}-ac); color: var(--${P}-ac-fg); font-weight: 700; }
.${P}-seg > button:disabled { opacity: .25; cursor: not-allowed; text-decoration: line-through; }

/* 下拉框 */
.${P}-sel {
  width: 100%; appearance: none; -webkit-appearance: none;
  background: var(--${P}-bg); color: var(--${P}-fg);
  border: 1px solid var(--${P}-bd); border-radius: 6px;
  padding: 2px 18px 2px 7px; font: inherit; font-size: 10.5px; font-weight: 500;
  cursor: pointer; outline: none; height: 22px;
  text-overflow: ellipsis;
  background-image: linear-gradient(45deg, transparent 50%, currentColor 50%),
                    linear-gradient(135deg, currentColor 50%, transparent 50%);
  background-position: calc(100% - 11px) 50%, calc(100% - 7px) 50%;
  background-size: 4px 4px, 4px 4px; background-repeat: no-repeat;
}
.${P}-sel:focus { border-color: var(--${P}-ac); }
.${P}-sel option { background: var(--${P}-bg2); color: var(--${P}-fg); }
.${P}-sel option:disabled { opacity: .35; }

/* 相机滤镜自定义下拉（带色块 + 随机骰子） */
.${P}-swsel { display: flex; align-items: center; gap: 4px; width: 100%; min-width: 0; }
.${P}-swsel-f {
  flex: 1 1 auto; min-width: 0;
  display: flex; align-items: center; gap: 5px;
  height: 22px; padding: 0 6px;
  background: var(--${P}-bg); color: var(--${P}-fg);
  border: 1px solid var(--${P}-bd); border-radius: 6px;
  font: inherit; font-size: 10.5px; font-weight: 500;
  cursor: pointer; text-align: left; outline: none;
}
.${P}-swsel-f:hover { border-color: var(--${P}-ac); }
.${P}-swsel-r {
  flex: none; width: 22px; height: 22px; padding: 0;
  background: var(--${P}-bg); color: var(--${P}-fg);
  border: 1px solid var(--${P}-bd); border-radius: 6px;
  font-size: 11px; line-height: 1; cursor: pointer;
}
.${P}-swsel-r:hover { border-color: var(--${P}-ac); background: var(--${P}-bg2); }
.${P}-swsel-r:active { background: var(--${P}-ac); border-color: var(--${P}-ac); }
.${P}-swsel-sw {
  flex: none; width: 12px; height: 12px; border-radius: 3px;
  border: 1px solid rgba(255,255,255,.28);
  background: #333;
}
.${P}-swsel-t { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.${P}-swsel-c { flex: none; font-size: 8px; opacity: .7; }

.${P}-swmenu {
  position: fixed; z-index: 100002; display: none;
  max-height: 300px; overflow-y: auto; overflow-x: hidden;
  background: #1b1b21; border: 1px solid #4a4a55; border-radius: 6px;
  box-shadow: 0 10px 26px rgba(0,0,0,.62);
  padding: 3px; box-sizing: border-box;
}
.${P}-swmenu.on { display: block; }
.${P}-swmenu::-webkit-scrollbar { width: 6px; }
.${P}-swmenu::-webkit-scrollbar-thumb { background: #555; border-radius: 3px; }
.${P}-swi {
  display: flex; align-items: center; gap: 7px;
  padding: 4px 6px; border-radius: 4px; cursor: pointer;
  font-size: 10.5px; color: var(--${P}-fg); white-space: nowrap;
}
.${P}-swi:hover { background: #2f5d47; }
.${P}-swi.on { background: #3b7d59; color: #f4fbf7; font-weight: 700; }
.${P}-swi-sw {
  flex: none; width: 14px; height: 14px; border-radius: 3px;
  border: 1px solid rgba(255,255,255,.22);
}
/* 悬停时弹出的 16×16 色彩/特效预览 */
.${P}-swprev {
  position: fixed; z-index: 100003; display: none;
  width: 16px; height: 16px; border-radius: 3px;
  border: 1px solid rgba(255,255,255,.6);
  box-shadow: 0 2px 10px rgba(0,0,0,.65);
  pointer-events: none;
}
.${P}-swprev.on { display: block; }

/* 布尔开关 */
.${P}-sw {
  position: relative; width: 28px; height: 15px; flex: none;
  border-radius: 8px; background: var(--${P}-bg);
  border: 1px solid var(--${P}-bd); cursor: pointer; transition: background .12s;
}
.${P}-sw::after {
  content: ""; position: absolute; top: 1px; left: 1px;
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--${P}-fg); opacity: .6; transition: left .12s, opacity .12s;
}
.${P}-sw.on { background: var(--${P}-ok); border-color: var(--${P}-ok); }
.${P}-sw.on::after { left: 14px; background: #fff; opacity: 1; }
.${P}-swtxt { margin-left: 5px; font-size: 9.5px; opacity: .74; font-weight: 600; }

/* 输入框 */
.${P}-num, .${P}-txt {
  width: 100%; height: 22px;
  background: var(--${P}-bg); color: var(--${P}-fg);
  border: 1px solid var(--${P}-bd); border-radius: 6px;
  padding: 0 7px; font: inherit; font-size: 10.5px; font-weight: 500; outline: none;
}
.${P}-num { text-align: right; }
.${P}-txt::placeholder { color: var(--${P}-fg); opacity: .32; }
.${P}-num:focus, .${P}-txt:focus { border-color: var(--${P}-ac); }

/* 数量步进框：框两端左右箭头 */
.${P}-step {
  display: flex; align-items: center; width: 100%; height: 22px;
  background: var(--${P}-bg); border: 1px solid var(--${P}-bd); border-radius: 6px;
  overflow: hidden;
}
.${P}-step:focus-within { border-color: var(--${P}-ac); }
.${P}-step-b {
  flex: none; width: 20px; height: 100%;
  border: 0; background: transparent; color: var(--${P}-fg);
  font: inherit; font-size: 9px; line-height: 1;
  cursor: pointer; opacity: .8; padding: 0;
}
.${P}-step-b:hover:not(:disabled) { background: var(--${P}-bg2); opacity: 1; }
.${P}-step-b:active:not(:disabled) { background: var(--${P}-ac); color: var(--${P}-ac-fg); opacity: 1; }
.${P}-step-b:disabled { opacity: .22; cursor: not-allowed; }
.${P}-step-in {
  flex: 1; min-width: 0; height: 100%;
  border: 0; background: transparent; color: var(--${P}-fg);
  text-align: center; font: inherit; font-size: 10.5px; font-weight: 600;
  outline: none; padding: 0; appearance: textfield; -moz-appearance: textfield;
}
.${P}-step-in::-webkit-outer-spin-button,
.${P}-step-in::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

/* 底部冲突提示 */
.${P}-warn {
  margin-top: 5px; font-size: 9.5px; line-height: 1.45;
  padding: 4px 6px; border-radius: 5px;
  background: rgba(224,160,58,.1); border: 1px solid rgba(224,160,58,.25);
  color: var(--${P}-no); display: none; white-space: pre-line;
}
.${P}-warn.on { display: block; }

/* 悬停气泡 */
.${P}-tip {
  position: fixed; z-index: 100000; max-width: 300px;
  background: #16161a; color: #ececf0;
  border: 1px solid #43434d; border-radius: 7px;
  padding: 7px 9px; font-size: 11px; line-height: 1.55;
  white-space: pre-line; pointer-events: none;
  box-shadow: 0 8px 24px rgba(0,0,0,.55); opacity: 0;
  transition: opacity .1s ease;
}
.${P}-tip.on { opacity: 1; }
`;

let stylesReady = false;
function ensureStyles() {
  if (stylesReady || document.getElementById(`${P}-style`)) return;
  const s = document.createElement("style");
  s.id = `${P}-style`;
  s.textContent = CSS;
  document.head.appendChild(s);
  stylesReady = true;
}

/* ---------------------------------------------------------------- 悬停气泡 */
let tipEl = null;
function getTip() {
  if (tipEl) return tipEl;
  tipEl = document.createElement("div");
  tipEl.className = `${P}-tip`;
  document.body.appendChild(tipEl);
  return tipEl;
}
function showTipAt(el, text) {
  if (!text) return;
  const t = getTip();
  t.textContent = text;
  t.classList.add("on");
  const r = el.getBoundingClientRect();
  const tw = t.offsetWidth, th = t.offsetHeight;
  let x = r.left + r.width / 2 - tw / 2;
  let y = r.bottom + 8;
  x = Math.max(8, Math.min(x, window.innerWidth - tw - 8));
  if (y + th > window.innerHeight - 8) y = r.top - th - 8;
  t.style.left = `${x}px`;
  t.style.top = `${Math.max(8, y)}px`;
}
function bindTip(el, getTextFn) {
  if (!getTextFn) return;
  el.addEventListener("mouseenter", () => {
    const txt = typeof getTextFn === "function" ? getTextFn() : getTextFn;
    showTipAt(el, txt);
  });
  el.addEventListener("mouseleave", () => getTip().classList.remove("on"));
}

/* ---------------------------------------------------------------- 读写 Widget */
function findWidget(node, name) {
  return (node.widgets || []).find((w) => w.name === name);
}

function rowOffNow(node, name) {
  return node.__c3ds?.rows?.[name]?.classList.contains("off") === true;
}

function writeWidget(node, name, value) {
  const w = findWidget(node, name);
  if (!w || w.value === value) return false;
  w.value = value;
  try {
    w.callback?.(value, APP?.canvas, node, null, null);
  } catch (_) {}
  APP?.graph?.setDirtyCanvas?.(true, false);
  return true;
}

/* ---------------------------------------------------------------- 控件生成 */
function makeBoolSeg(node, name, labels) {
  const box = document.createElement("div");
  box.className = `${P}-seg`;
  const vals = [true, false];
  const btns = [];
  vals.forEach((val, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = labels[i];
    b.onclick = () => {
      if (rowOffNow(node, name)) return;
      writeWidget(node, name, val);
      refresh(node);
    };
    box.appendChild(b);
    btns.push([val, b]);
  });
  return {
    el: box,
    update(v) {
      for (const [val, b] of btns) b.classList.toggle("on", v === val);
    },
  };
}

function makeToggle(node, name) {
  const wrap = document.createElement("div");
  wrap.style.cssText = "display:flex;align-items:center";
  const sw = document.createElement("div");
  sw.className = `${P}-sw`;
  const txt = document.createElement("span");
  txt.className = `${P}-swtxt`;
  wrap.append(sw, txt);
  sw.onclick = () => {
    if (rowOffNow(node, name)) return;
    const w = findWidget(node, name);
    if (!w) return;
    writeWidget(node, name, !w.value);
    refresh(node);
  };
  return {
    el: wrap,
    update(v) {
      const on = v === true;
      sw.classList.toggle("on", on);
      txt.textContent = on ? "开" : "关";
    },
  };
}

function makeSeg(node, name) {
  const box = document.createElement("div");
  box.className = `${P}-seg`;
  const w = findWidget(node, name);
  const opts = (w?.options?.values || []).slice();
  const btns = new Map();
  for (const opt of opts) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = opt;
    if (name === "生成模式" && MODE_META[opt]) {
      bindTip(b, () => MODE_META[opt].tip);
    }
    b.onclick = () => {
      if (b.disabled || rowOffNow(node, name)) return;
      writeWidget(node, name, opt);
      refresh(node);
    };
    box.appendChild(b);
    btns.set(opt, b);
  }
  return {
    el: box,
    update(v, offOpts) {
      for (const [opt, b] of btns) {
        b.classList.toggle("on", opt === v);
        const off = offOpts?.has(opt) === true;
        b.disabled = off;
      }
    },
  };
}

function makeSelect(node, name) {
  const sel = document.createElement("select");
  sel.className = `${P}-sel`;
  const w = findWidget(node, name);
  const opts = (w?.options?.values || []).slice();
  const items = new Map();
  for (const opt of opts) {
    const o = document.createElement("option");
    o.value = opt;
    o.textContent = opt;
    sel.appendChild(o);
    items.set(opt, o);
  }
  sel.onchange = () => {
    if (rowOffNow(node, name)) return;
    if (sel.value) writeWidget(node, name, sel.value);
    refresh(node);
  };
  return {
    el: sel,
    update(v, offOpts, hiddenOpts) {
      for (const [opt, o] of items) {
        const off = offOpts?.has(opt) === true;
        const hide = hiddenOpts?.has(opt) === true;
        o.disabled = off || hide;
        o.hidden = hide;
        o.textContent = off ? `${opt}（已避让）` : opt;
      }
      if (document.activeElement !== sel) sel.value = v;
    },
  };
}

/* 相机滤镜：自定义下拉（带色块），悬停选项弹出 16×16 预览方块 */
let swatchMenuCloser = null;

function makeSwatchSelect(node, name) {
  const wrap = document.createElement("div");
  wrap.className = `${P}-swsel`;

  const w = findWidget(node, name);
  const opts = (w?.options?.values || []).slice();
  const pickPool = opts.filter((o) => o !== "关闭");

  const field = document.createElement("button");
  field.type = "button";
  field.className = `${P}-swsel-f`;
  const sw = document.createElement("span");
  sw.className = `${P}-swsel-sw`;
  const txt = document.createElement("span");
  txt.className = `${P}-swsel-t`;
  const caret = document.createElement("span");
  caret.className = `${P}-swsel-c`;
  caret.textContent = "▾";
  field.append(sw, txt, caret);

  // 随机开关：点一下就从全部滤镜里随机抽一个（不含「关闭」）
  const dice = document.createElement("button");
  dice.type = "button";
  dice.className = `${P}-swsel-r`;
  dice.textContent = "🎲";
  dice.title = "随机选一个相机滤镜（不含「关闭」）";
  dice.onclick = () => {
    if (!pickPool.length) return;
    const pick = pickPool[Math.floor(Math.random() * pickPool.length)];
    writeWidget(node, name, pick);
    closeMenu();
    refresh(node);
  };

  wrap.append(field, dice);

  // 菜单与预览挂在 body 上：面板 overflow:hidden，画布又是缩放容器，
  // 只有 body 层的 fixed 元素既不会被裁切也不会跟着画布缩放。
  const menu = document.createElement("div");
  menu.className = `${P}-swmenu`;
  const prev = document.createElement("div");
  prev.className = `${P}-swprev`;
  document.body.append(menu, prev);

  const items = new Map();
  for (const opt of opts) {
    const row = document.createElement("div");
    row.className = `${P}-swi`;
    const chip = document.createElement("span");
    chip.className = `${P}-swi-sw`;
    chip.style.background = swatchFor(opt);
    const label = document.createElement("span");
    label.textContent = opt;
    row.append(chip, label);
    row.addEventListener("mouseenter", () => {
      prev.style.background = swatchFor(opt);
      prev.classList.add("on");
      const r = row.getBoundingClientRect();
      const m = menu.getBoundingClientRect();
      let x = m.right + 8;
      if (x + 16 > window.innerWidth - 4) x = m.left - 24;
      prev.style.left = `${Math.max(2, Math.round(x))}px`;
      prev.style.top = `${Math.round(r.top + (r.height - 16) / 2)}px`;
    });
    row.addEventListener("mouseleave", () => prev.classList.remove("on"));
    row.onclick = () => {
      writeWidget(node, name, opt);
      closeMenu();
      refresh(node);
    };
    menu.appendChild(row);
    items.set(opt, row);
  }

  let opened = false;

  const onDocDown = (e) => {
    const t = e.target;
    const insideMenu = menu.contains && menu.contains(t);
    const insideWrap = wrap.contains && wrap.contains(t);
    if (insideMenu || insideWrap) return;
    closeMenu();
  };
  const onKey = (e) => {
    if (e.key === "Escape") closeMenu();
  };
  const onViewportChange = () => closeMenu();

  function closeMenu() {
    if (!opened) return;
    opened = false;
    menu.classList.remove("on");
    prev.classList.remove("on");
    document.removeEventListener("pointerdown", onDocDown, true);
    window.removeEventListener("keydown", onKey, true);
    window.removeEventListener("resize", onViewportChange);
    if (swatchMenuCloser === closeMenu) swatchMenuCloser = null;
  }

  function openMenu() {
    if (opened) return;
    if (swatchMenuCloser) swatchMenuCloser();
    const r = field.getBoundingClientRect();
    menu.style.width = `${Math.max(170, Math.round(r.width) + 40)}px`;
    menu.classList.add("on");
    const mh = menu.getBoundingClientRect().height || 280;
    let top = r.bottom + 4;
    if (mh && top + mh > window.innerHeight - 6) {
      top = Math.max(6, r.top - mh - 4);
    }
    menu.style.left = `${Math.round(r.left)}px`;
    menu.style.top = `${Math.round(top)}px`;
    opened = true;
    swatchMenuCloser = closeMenu;
    document.addEventListener("pointerdown", onDocDown, true);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", onViewportChange);
  }

  field.onclick = () => (opened ? closeMenu() : openMenu());

  // 节点被删除时带走挂在 body 上的菜单与预览，避免残留
  const prevRemoved = node.onRemoved;
  node.onRemoved = function () {
    try {
      menu.remove?.();
      prev.remove?.();
    } catch (_) {}
    return prevRemoved?.apply(this, arguments);
  };

  return {
    el: wrap,
    update(v) {
      const val = v ?? "关闭";
      txt.textContent = val;
      sw.style.background = swatchFor(val);
      for (const [opt, row] of items) row.classList.toggle("on", opt === val);
    },
  };
}

function makeNum(node, name) {
  const inp = document.createElement("input");
  inp.type = "number";
  inp.className = `${P}-num`;
  const w = findWidget(node, name);
  const o = w?.options || {};
  const MIN = Number.isFinite(o.min) ? o.min : 1;
  const MAX = Number.isFinite(o.max) ? o.max : 200;

  inp.setAttribute("min", String(MIN));
  inp.setAttribute("max", String(MAX));
  inp.setAttribute("step", "1");
  inp.setAttribute("inputmode", "numeric");

  const clamp = (v) => Math.min(MAX, Math.max(MIN, Math.round(v)));

  const commit = (rewrite) => {
    if (rowOffNow(node, name)) return;
    let n = Number(inp.value);
    if (!Number.isFinite(n)) n = MIN;
    n = clamp(n);
    if (rewrite) inp.value = String(n);
    writeWidget(node, name, n);
    refresh(node);
  };

  inp.oninput = () => commit(false);
  inp.onchange = () => commit(true);
  inp.onblur = () => commit(true);

  inp.addEventListener("keydown", (e) => {
    if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
    e.preventDefault();
    const cur = Number(inp.value);
    const base = Number.isFinite(cur) ? cur : MIN;
    inp.value = String(clamp(base + (e.key === "ArrowUp" ? 1 : -1)));
    commit(true);
  });

  return {
    el: inp,
    update(v) {
      if (document.activeElement !== inp) inp.value = String(v ?? MIN);
    },
  };
}

/* 数量：框两头的左右箭头步进框（长按连续加减，无原生上下箭头） */
function makeStepper(node, name) {
  const box = document.createElement("div");
  box.className = `${P}-step`;

  const dec = document.createElement("button");
  dec.type = "button";
  dec.className = `${P}-step-b`;
  dec.textContent = "◀";
  dec.setAttribute("aria-label", "减少");
  dec.title = "减少";

  const inp = document.createElement("input");
  inp.type = "number";
  inp.className = `${P}-step-in`;
  inp.setAttribute("inputmode", "numeric");
  inp.setAttribute("step", "1");

  const inc = document.createElement("button");
  inc.type = "button";
  inc.className = `${P}-step-b`;
  inc.textContent = "▶";
  inc.setAttribute("aria-label", "增加");
  inc.title = "增加";

  const w = findWidget(node, name);
  const o = w?.options || {};
  const MIN = Number.isFinite(o.min) ? o.min : 1;
  const MAX = Number.isFinite(o.max) ? o.max : 200;
  inp.setAttribute("min", String(MIN));
  inp.setAttribute("max", String(MAX));

  const clamp = (v) => Math.min(MAX, Math.max(MIN, Math.round(v)));
  const current = () => {
    const n = Number(inp.value);
    return Number.isFinite(n) ? clamp(n) : MIN;
  };

  const push = (dir) => {
    if (rowOffNow(node, name)) return;
    const next = clamp(current() + dir);
    inp.value = String(next);
    writeWidget(node, name, next);
    syncDisabled(next);
    refresh(node);
  };

  const syncDisabled = (v) => {
    const val = v ?? current();
    dec.disabled = val <= MIN;
    inc.disabled = val >= MAX;
  };

  const commit = () => {
    if (rowOffNow(node, name)) return;
    const n = current();
    inp.value = String(n);
    writeWidget(node, name, n);
    syncDisabled(n);
    refresh(node);
  };

  inp.oninput = () => commit();
  inp.onblur = () => commit();
  inp.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      push(-1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      push(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      push(1);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      push(-1);
    } else if (e.key === "Enter") {
      commit();
      inp.blur();
    }
  });

  let holdDelay = 0;
  let holdRepeat = 0;
  const stopHold = () => {
    if (holdDelay) clearTimeout(holdDelay);
    if (holdRepeat) clearInterval(holdRepeat);
    holdDelay = 0;
    holdRepeat = 0;
  };
  const bindHold = (btn, dir) => {
    btn.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      if (btn.disabled) return;
      push(dir);
      stopHold();
      holdDelay = setTimeout(() => {
        holdRepeat = setInterval(() => push(dir), 80);
      }, 360);
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach((t) =>
      btn.addEventListener(t, stopHold)
    );
    btn.addEventListener("selectstart", (e) => e.preventDefault());
  };
  bindHold(dec, -1);
  bindHold(inc, 1);

  box.append(dec, inp, inc);

  return {
    el: box,
    update(v) {
      if (document.activeElement !== inp) inp.value = String(v ?? MIN);
      syncDisabled(v);
    },
  };
}

function makeText(node, name) {
  const inp = document.createElement("input");
  inp.type = "text";
  inp.className = `${P}-txt`;
  inp.placeholder = "留空 = 不加（例：film grain, bokeh）";
  inp.oninput = () => {
    if (rowOffNow(node, name)) return;
    writeWidget(node, name, inp.value);
  };
  inp.onchange = () => refresh(node);
  return {
    el: inp,
    update(v) {
      if (document.activeElement !== inp) inp.value = v ?? "";
    },
  };
}

function makeControl(node, name) {
  const w = findWidget(node, name);
  if (!w) return null;
  if (typeof w.value === "boolean" || w.type === "toggle") return makeToggle(node, name);
  if (Array.isArray(w.options?.values)) {
    if (name === "相机滤镜") return makeSwatchSelect(node, name);
    // 生成模式固定使用分段按钮；其余超过 4 项用下拉框
    if (name === "生成模式" || w.options.values.length <= 4) {
      return makeSeg(node, name);
    }
    return makeSelect(node, name);
  }
  if (typeof w.value === "number") {
    if (name === "数量") return makeStepper(node, name);
    return makeNum(node, name);
  }
  return makeText(node, name);
}

/* ---------------------------------------------------------------- 模式徽章 */
function renderModeBadge(el, meta) {
  const key = `${meta.locked.join(",")}|${meta.changed.join(",")}`;
  if (el.dataset.key === key) return;
  el.dataset.key = key;
  el.textContent = "";

  const gLock = document.createElement("span");
  gLock.className = `${P}-badge-g locked`;
  const bLock = document.createElement("b");
  bLock.textContent = "🔒 已锁";
  const sLock = document.createElement("span");
  sLock.textContent = meta.locked.join(" · ");
  gLock.append(bLock, sLock);

  const gChg = document.createElement("span");
  gChg.className = `${P}-badge-g changed`;
  const bChg = document.createElement("b");
  bChg.textContent = "🔄 变化";
  const sChg = document.createElement("span");
  sChg.textContent = meta.changed.join(" · ");
  gChg.append(bChg, sChg);

  el.append(gLock, gChg);
}

/* ---------------------------------------------------------------- 刷新状态 */
const LEGACY_MODE_MAP = {
  "完全随机": "盲盒抽卡",
  "同人不同姿势": "模特换装",
  "同场景不同姿势": "写真套图",
  "锁场景锁人只变姿势": "定点连拍",
};

function refresh(node) {
  const ui = node.__c3ds;
  if (!ui) return;

  // 兼容旧工作流的模式名
  const modeW = findWidget(node, "生成模式");
  if (modeW && LEGACY_MODE_MAP[modeW.value]) {
    writeWidget(node, "生成模式", LEGACY_MODE_MAP[modeW.value]);
  }

  const v = {};
  for (const w of node.widgets || []) v[w.name] = w.value;

  // 主题细分与「现代 / 古风」自动联动：选现代时隐藏古风子项，选古风时隐藏现代子项
  const isGufeng = v["服装风格"] === "古风";
  const curTheme = v["主题细分"] || "自动随机";
  if (isGufeng && curTheme.startsWith("现代·")) {
    writeWidget(node, "主题细分", "自动随机");
    v["主题细分"] = "自动随机";
  } else if (!isGufeng && curTheme.startsWith("古风·")) {
    writeWidget(node, "主题细分", "自动随机");
    v["主题细分"] = "自动随机";
  }

  // 1) 纠正互斥冲突值
  let guard = 0, changed = true;
  while (changed && guard < 4) {
    changed = false;
    guard += 1;
    for (const rule of RULES) {
      if (!rule.onActive) continue;
      if (!rule.when(v)) continue;
      if (rule.guard && !rule.guard(v)) continue;
      rule.onActive(v, (name, val) => {
        if (writeWidget(node, name, val)) {
          v[name] = val;
          changed = true;
        }
      });
    }
  }

  // 2) 计算禁用项与原因
  const rowOff = new Set();
  const rowReason = {};
  const optOff = {};
  const reasons = [];
  for (const rule of RULES) {
    if (!rule.when(v)) continue;
    if (rule.guard && !rule.guard(v)) continue;
    reasons.push(rule.reason);
    for (const n of rule.disable || []) {
      rowOff.add(n);
      rowReason[n] = rule.reason;
    }
    for (const [n, opts] of Object.entries(rule.disableOptions || {})) {
      if (rowOff.has(n)) continue;
      (optOff[n] ||= new Set());
      for (const o of opts) optOff[n].add(o);
    }
  }
  ui.rowReason = rowReason;

  // 3) 过滤主题细分隐藏项
  const hiddenSubThemes = new Set();
  const subW = findWidget(node, "主题细分");
  for (const opt of subW?.options?.values || []) {
    if (opt === "自动随机") continue;
    if (isGufeng && opt.startsWith("现代·")) hiddenSubThemes.add(opt);
    if (!isGufeng && opt.startsWith("古风·")) hiddenSubThemes.add(opt);
  }

  // 4) 更新所有 DOM 控件
  for (const [name, ctl] of Object.entries(ui.controls)) {
    ui.rows[name]?.classList.toggle("off", rowOff.has(name));
    ctl.update(
      v[name],
      optOff[name],
      name === "主题细分" ? hiddenSubThemes : undefined
    );
  }

  // 5) 更新模式锁定徽章与段号回显
  const meta = MODE_META[v["生成模式"]] || MODE_META["写真套图"];
  if (ui.modeBadge) renderModeBadge(ui.modeBadge, meta);

  const seedVal = Math.max(0, Number(v["随机种子"]) || 0);
  const segIdx = 1 + (seedVal % TOTAL_SEGMENTS);
  if (ui.segIdEl) ui.segIdEl.textContent = `段 #${String(segIdx).padStart(5, "0")}`;

  // 6) 更新冲突提示栏与高度
  ui.root.classList.toggle("is-nude", v["穿衣服"] === false);
  ui.warn.classList.toggle("on", reasons.length > 0);
  ui.warn.textContent = reasons.length ? `已按规则自动避让：${reasons.join("；")}` : "";

  requestAnimationFrame(() => ui.fitHeightIfNeeded?.());
  node.setDirtyCanvas?.(true, false);
}

/* ---------------------------------------------------------------- 构建面板 */
function buildPanel(node) {
  if (node.__c3ds) return;
  if (typeof node.addDOMWidget !== "function") {
    node.color = "#7a2b2b";
    node.bgcolor = "#3a1d1d";
    return;
  }
  ensureStyles();

  const root = document.createElement("div");
  const stage = document.createElement("div");
  stage.className = `${P}-stage`;
  root.className = `${P}-root`;

  const controls = {};
  const rows = {};

  // 顶部栏：有衣/无衣（带标签槽）+ 实时段号 + 一键重置
  const topbar = document.createElement("div");
  topbar.className = `${P}-topbar`;

  if (findWidget(node, "穿衣服")) {
    const heroLab = document.createElement("div");
    heroLab.className = `${P}-lab`;
    const heroTxt = document.createElement("span");
    heroTxt.className = `${P}-lab-t`;
    for (const ch of Array.from("穿衣服")) {
      const c = document.createElement("span");
      c.textContent = ch;
      heroTxt.appendChild(c);
    }
    heroLab.appendChild(heroTxt);
    bindTip(heroLab, () => `穿衣服\n\n${TIPS["穿衣服"]}`);

    const hero = document.createElement("div");
    hero.className = `${P}-ctl ${P}-hero`;
    const ctl = makeBoolSeg(node, "穿衣服", ["👗 有衣服", "🌸 没衣服"]);
    hero.appendChild(ctl.el);
    topbar.append(heroLab, hero);
    controls["穿衣服"] = ctl;
    rows["穿衣服"] = hero;
    bindTip(hero, () => `穿衣服\n\n${TIPS["穿衣服"]}`);
  }

  const segIdEl = document.createElement("div");
  segIdEl.className = `${P}-seg-id`;
  segIdEl.textContent = "段 #00001";
  bindTip(segIdEl, () => "当前种子对应的基准段号（共 50000 段）。\n同一种子切换「有衣服 / 没衣服」必定共享同一段号。");
  topbar.appendChild(segIdEl);

  const resetBtn = document.createElement("button");
  resetBtn.type = "button";
  resetBtn.className = `${P}-reset`;
  resetBtn.textContent = "↺ 重置";
  bindTip(resetBtn, () => "一键将所有参数恢复为推荐默认值（不改动随机种子）");
  resetBtn.onclick = () => {
    for (const [k, defVal] of Object.entries(DEFAULTS)) {
      writeWidget(node, k, defVal);
    }
    refresh(node);
  };
  topbar.appendChild(resetBtn);
  stage.appendChild(topbar);

  let modeBadge = null;

  // 渲染分区
  for (const sec of LAYOUT) {
    const secEl = document.createElement("div");
    secEl.className = `${P}-sec`;
    const t = document.createElement("div");
    t.className = `${P}-sec-t`;
    t.textContent = sec.title;
    secEl.appendChild(t);

    const addRow = (parent, name) => {
      if (name === "__mode_badge__") {
        modeBadge = document.createElement("div");
        modeBadge.className = `${P}-badge`;
        parent.appendChild(modeBadge);
        return;
      }
      const ctl = makeControl(node, name);
      if (!ctl) return;
      const row = document.createElement("div");
      row.className = `${P}-row`;

      const lab = document.createElement("div");
      lab.className = `${P}-lab`;
      // 逐字排布 + space-between：2 字标题与 4 字标题的右边界对齐
      const labTxt = document.createElement("span");
      labTxt.className = `${P}-lab-t`;
      for (const ch of Array.from(name)) {
        const c = document.createElement("span");
        c.textContent = ch;
        labTxt.appendChild(c);
      }
      lab.appendChild(labTxt);

      const ctlBox = document.createElement("div");
      ctlBox.className = `${P}-ctl`;
      ctlBox.appendChild(ctl.el);

      if (TIPS[name]) {
        bindTip(lab, () => {
          const r = node.__c3ds?.rowReason?.[name];
          const prefix = r ? `⚠️ 当前已置灰：${r}\n\n` : "";
          return `${prefix}${name}\n\n${TIPS[name]}`;
        });
      }

      row.append(lab, ctlBox);
      parent.appendChild(row);
      controls[name] = ctl;
      rows[name] = row;
    };

    for (const entry of sec.rows) {
      if (Array.isArray(entry)) {
        const grid = document.createElement("div");
        grid.className = `${P}-grid`;
        for (const name of entry) addRow(grid, name);
        secEl.appendChild(grid);
        continue;
      }
      if (entry && typeof entry === "object" && Array.isArray(entry.pair)) {
        const grid = document.createElement("div");
        grid.className = `${P}-grid`;
        if (entry.cols) grid.style.gridTemplateColumns = entry.cols;
        if (Number.isFinite(entry.gap)) grid.style.columnGap = `${entry.gap}px`;
        for (const name of entry.pair) addRow(grid, name);
        secEl.appendChild(grid);
        continue;
      }
      addRow(secEl, entry);
    }
    stage.appendChild(secEl);
  }

  const warn = document.createElement("div");
  warn.className = `${P}-warn`;
  stage.appendChild(warn);
  root.appendChild(stage);

  // 监听原生随机种子变化以实时刷新段号回显
  const seedW = findWidget(node, "随机种子");
  if (seedW && !seedW.__c3dsHooked) {
    seedW.__c3dsHooked = true;
    const prevCb = seedW.callback;
    seedW.callback = function () {
      const r = prevCb?.apply(this, arguments);
      refresh(node);
      return r;
    };
  }

  // 1) 在 addDOMWidget 之前隐藏非保留的原生控件，抵消 4px 间距
  for (const w of node.widgets || []) {
    if (KEEP_NATIVE.has(w.name)) continue;
    w.computeSize = () => [0, -4];
    w.draw = () => {};
  }

  // 2) 测量 stage 自然高度
  let lastNaturalH = 460;
  const getNaturalH = () => {
    const h = stage.offsetHeight;
    if (h > 20) lastNaturalH = h;
    return lastNaturalH;
  };

  const domWidget = node.addDOMWidget(`${P}_panel`, `${P}_panel`, root, {
    serialize: false,
    hideOnZoom: false,
    getHeight: () => getNaturalH() + 6,
  });

  try {
    domWidget.serialize = false;
  } catch (_) {}

  const getTopOffset = () => {
    return domWidget.last_y != null && domWidget.last_y > 40 ? domWidget.last_y : 140;
  };

  const getMinNodeHeight = () => {
    return Math.ceil(getTopOffset() + getNaturalH() + 14);
  };

  let userExtraH = 0;
  let internalResize = false;

  const fitHeightIfNeeded = () => {
    if (internalResize || !node.size || node.flags?.collapsed) return;
    if (stage.offsetHeight <= 20) return;
    internalResize = true;
    try {
      const minH = getMinNodeHeight();
      const targetW = Math.max(node.size[0], MIN_WIDTH);
      const targetH = minH + userExtraH;
      if (Math.abs(node.size[0] - targetW) > 1 || Math.abs(node.size[1] - targetH) > 1) {
        node.setSize([targetW, targetH]);
        node.setDirtyCanvas?.(true, true);
      }
    } finally {
      internalResize = false;
    }
  };

  const prevResize = node.onResize;
  node.onResize = function (size) {
    const r = prevResize?.apply(this, arguments);
    if (!internalResize && size && !this.flags?.collapsed && stage.offsetHeight > 20) {
      if (size[0] < MIN_WIDTH) size[0] = MIN_WIDTH;
      const minH = getMinNodeHeight();
      if (size[1] < minH) {
        size[1] = minH;
        userExtraH = 0;
      } else {
        userExtraH = Math.max(0, size[1] - minH);
      }
    }
    this.setDirtyCanvas?.(true, true);
    return r;
  };

  if (typeof ResizeObserver !== "undefined") {
    let lastW = 0;
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      if (Math.abs(rect.width - lastW) > 1) {
        lastW = rect.width;
        requestAnimationFrame(fitHeightIfNeeded);
      }
    });
    ro.observe(stage);
  }

  root.addEventListener(
    "wheel",
    (e) => {
      if (swatchMenuCloser) swatchMenuCloser();
      const t = e.target;
      if (t && t.closest && t.closest("input,select,textarea")) return;
      const canvas = APP && APP.canvas;
      if (!canvas) return;
      e.preventDefault();
      e.stopPropagation();
      if (typeof canvas.processMouseWheel === "function") {
        canvas.processMouseWheel(e);
      } else if (canvas.ds) {
        const k = e.deltaY > 0 ? 0.92 : 1.08;
        canvas.ds.scale = Math.max(0.2, Math.min(5, canvas.ds.scale * k));
        canvas.setDirty?.(true, true);
      }
    },
    { passive: false }
  );

  /* ---- 中键拖拽透传：DOM 面板默认会吃掉中键，这里把事件转给画布 ---- */
  const forwardMouseToCanvas = (e) => {
    const canvasEl = APP && APP.canvas && APP.canvas.canvas;
    if (!canvasEl) return;
    const PE = typeof window !== "undefined" ? window.PointerEvent : null;
    const ME = typeof window !== "undefined" ? window.MouseEvent : null;
    const Ctor = PE && e instanceof PE ? PE : ME;
    if (!Ctor) return;
    try {
      canvasEl.dispatchEvent(
        new Ctor(e.type, {
          bubbles: true,
          cancelable: true,
          view: typeof window !== "undefined" ? window : undefined,
          clientX: e.clientX,
          clientY: e.clientY,
          screenX: e.screenX,
          screenY: e.screenY,
          button: e.button,
          buttons: e.buttons,
          ctrlKey: e.ctrlKey,
          shiftKey: e.shiftKey,
          altKey: e.altKey,
          metaKey: e.metaKey,
          pointerId: e.pointerId || 1,
          pointerType: e.pointerType || "mouse",
          isPrimary: true,
        })
      );
    } catch (_) {}
  };

  root.addEventListener(
    "pointerdown",
    (e) => {
      if (e.button !== 1) return; // 只接管中键
      if (!APP || !APP.canvas || !APP.canvas.canvas) return;
      e.preventDefault();
      e.stopPropagation();
      if (swatchMenuCloser) swatchMenuCloser();
      // 拖拽期间让面板不再命中，后续 pointermove 全部落到画布
      root.style.pointerEvents = "none";
      forwardMouseToCanvas(e);
      const restore = () => {
        root.style.pointerEvents = "";
        window.removeEventListener("pointerup", restore, true);
        window.removeEventListener("pointercancel", restore, true);
        window.removeEventListener("blur", restore, true);
      };
      window.addEventListener("pointerup", restore, true);
      window.addEventListener("pointercancel", restore, true);
      window.addEventListener("blur", restore, true);
    },
    true
  );

  // 中键松开时浏览器默认触发自动滚动，一并吞掉
  root.addEventListener(
    "auxclick",
    (e) => {
      if (e.button !== 1) return;
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );

  node.__c3ds = {
    root, stage, controls, rows, warn, domWidget,
    modeBadge, segIdEl, fitHeightIfNeeded, rowReason: {},
  };

  refresh(node);

  requestAnimationFrame(() => {
    internalResize = true;
    const w = Math.max(node.size ? node.size[0] : 0, DEFAULT_WIDTH);
    node.setSize([w, getMinNodeHeight()]);
    internalResize = false;
    node.setDirtyCanvas?.(true, true);
    setTimeout(fitHeightIfNeeded, 100);
  });
}

/* ---------------------------------------------------------------- 注册扩展 */
function patchNodeType(nodeType) {
  if (!nodeType || nodeType.__c3dsPatched) return;
  nodeType.__c3dsPatched = true;

  const onNodeCreated = nodeType.prototype.onNodeCreated;
  nodeType.prototype.onNodeCreated = function () {
    const r = onNodeCreated?.apply(this, arguments);
    try {
      buildPanel(this);
    } catch (e) {
      console.error("[Crazy3DS PromptMaster] 面板构建失败", e);
    }
    return r;
  };

  const onConfigure = nodeType.prototype.onConfigure;
  nodeType.prototype.onConfigure = function () {
    const r = onConfigure?.apply(this, arguments);
    requestAnimationFrame(() => {
      try {
        refresh(this);
        this.__c3ds?.fitHeightIfNeeded?.();
      } catch (_) {}
    });
    return r;
  };
}

function boot(app) {
  APP = app;

  const isOurs = (node) =>
    !!node && (TARGET_NODES.has(node.comfyClass) || TARGET_NODES.has(node.type));

  app.registerExtension({
    name: "Crazy3DS.PairPromptPlus.UI",

    beforeRegisterNodeDef(nodeType, nodeData) {
      const cls = nodeData?.name || nodeType?.comfyClass;
      if (!TARGET_NODES.has(cls)) return;
      patchNodeType(nodeType);
    },

    nodeCreated(node) {
      if (!isOurs(node)) return;
      try {
        buildPanel(node);
      } catch (e) {
        console.error("[Crazy3DS PromptMaster] nodeCreated 异常", e);
      }
    },

    loadedGraphNode(node) {
      if (!isOurs(node)) return;
      try {
        buildPanel(node);
      } catch (e) {
        console.error("[Crazy3DS PromptMaster] loadedGraphNode 异常", e);
      }
    },
  });

  for (const name of TARGET_NODES) {
    const t = app.nodeTypes && app.nodeTypes[name];
    if (t) patchNodeType(t);
  }
}

const _app = appSync();
if (_app) {
  boot(_app);
} else {
  appAsync().then((a) => {
    if (a) boot(a);
  });
}
