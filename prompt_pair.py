# -*- coding: utf-8 -*-
"""Crazy3DS 美女提示词大师 (v69) —— 商业人像级双版提示词生成器。
支持：五档摄影套系模式 / 26 类服装主题细分 / 智能焦段与光影适配 / 相机滤镜色彩科学 + 强度分档 /
情绪眼神控制 / 场景-姿势-服装三重冲突消解 / 组合相关负面词 / 有衣无衣同构图对拍。
"""
import os
import random


def _flat_map(mapping):
    """把 {键: [条目...]} 摊平成条目列表（保持定义顺序）。"""
    out = []
    for v in mapping.values():
        out.extend(v)
    return out


def _uniq(seq):
    """按原顺序去重，合并池子时不产生重复条目。"""
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


__version__ = "v69"

NODE_ID = "Crazy3DS_PairPromptPlus"
TOTAL_SEGMENTS = 50000
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# v67：原有词库里并没有任何「乳头/乳晕」相关词，也就谈不上被屏蔽；
# 真正让模型自发打码的是「无衣版本从不描述乳头」+「负向词没禁止打码/胸贴」。
# 这里补齐负向词，无衣渲染再显式写出乳头与乳晕（见 _render）。
NEGATIVE = (
    "low quality, bad anatomy, extra limbs, deformed hands, extra fingers, fused fingers, "
    "bad feet, blurred genitals, text, watermark, distorted face, asymmetric eyes, "
    "plastic skin, over-smoothed skin, heavy beauty filter, doll face, overly large eyes, "
    "pointed chin, uncanny, censored, censorship bar, mosaic censoring, pixelated breasts, "
    "pasties, nipple tape, bra covering nipples, airbrushed chest, "
    "anatomically incorrect nipples, merged nipples, extra breasts, "
    "cartoon, anime, 3d render, cgi, painting, sketch, illustration, mannequin, "
    "jpeg artifacts, washed out colors, flat lighting"
)


def build_negative(
    clothed=True, outfit_style="现代", sub_theme="自动随机",
    lighting="跟随场景", cam_filter="关闭", scene_pref="不限"
):
    """负面提示词 = 统一画质基线 + 按当前组合追加的专项词。

    同一组参数永远得到同一串负面词（可复现、可保存），
    但古风/现代、有衣/无衣、室内/户外、光效、滤镜各自带上针对性的排除项。
    """
    extra = []

    # 服装风格：古风最容易混进现代道具，现代最容易混进古装
    if outfit_style in ("古风",) or (sub_theme or "").startswith("古风·"):
        extra.append(
            "modern objects, sneakers, wristwatch, car, power lines, "
            "plastic bag, air conditioner, latin signage"
        )
    else:
        extra.append("hanfu, ancient chinese costume")

    # 有衣 / 无衣
    if clothed:
        extra.append("nude, topless, exposed nipples")
    else:
        extra.append("clothing, underwear, bra straps, fabric folds")

    # 场景偏好
    if scene_pref in ("户外", "户外日常"):
        extra.append("indoor room, studio backdrop")
    elif scene_pref in ("室内", "室内日常"):
        extra.append("open landscape, wilderness")

    # 光影：压掉与所选光效相反的成分
    diffusion = ("黑柔 1/4·Black Mist", "白柔·Glimmerglass", "柔焦·Softar 朦胧")
    if lighting == "霓虹夜景":
        extra.append("daylight, flat gray light")
    elif lighting == "自然柔光":
        extra.append("harsh flash, harsh shadows, blown highlights")
    elif lighting == "落日逆光":
        extra.append("flat frontal light, dull color")
    elif lighting == "闪光直打":
        # 闪光 + 柔光镜是常见商业搭配，此时不要再压「soft haze」
        if cam_filter not in diffusion:
            extra.append("soft dreamy haze, low contrast")

    # 滤镜：黑白不能带彩噪，柔光镜不能过度锐化
    if cam_filter == "依尔福 HP5·黑白颗粒":
        extra.append("color, color cast, rainbow halation, oversaturated")
    elif cam_filter in ("黑柔 1/4·Black Mist", "白柔·Glimmerglass", "柔焦·Softar 朦胧"):
        extra.append("over-sharpened, crunchy detail, harsh edges")

    extra = [e for e in extra if e]
    return ", ".join([NEGATIVE] + extra)

SHOTS = [
    "full body shot, whole figure in frame, both feet visible",
    "cowboy shot, mid-thigh framing, upper legs visible",
    "medium shot, waist up",
    "wide shot, full body small in frame",
    "full body shot, camera slightly below eye level",
]

FRONT_ANGLES = [
    "frontal view",
    "three-quarter front view",
    "eye-level view",
    "low-angle view",
    "high-angle view",
]
BACK_ANGLES = [
    "from behind",
    "over-the-shoulder view",
    "side view",
    "three-quarter back view",
]

FRONT_ANGLES_BEAUTY = [
    "frontal view",
    "three-quarter front view",
    "eye-level view",
    "camera at chest height, straight-on view",
    "slightly turned three-quarter view, shoulders angled to camera",
    "full-length frontal view, camera at waist height",
    "over-the-shoulder glance, body angled three-quarter to camera",
    "side-lit three-quarter view, face turned to camera",
]
BACK_ANGLES_BEAUTY = [
    "from behind",
    "over-the-shoulder view, face turned back to camera",
    "side view, profile silhouette",
    "three-quarter back view, shoulders angled away from camera",
]

FACES = [
    "soft oval face, gentle natural makeup",
    "defined oval face, subtle eyeliner, calm expression",
    "round youthful face, bright eyes, natural makeup",
    "narrow long eyes, minimal makeup, composed expression",
    "classical oval face, soft almond eyes, rose nude lip",
    "angular jawline, natural full brows, confident expression",
    "heart-shaped face, clear eyes, soft smile",
    "high cheekbones, deep-set eyes, elegant expression",
    "delicate features, small nose, natural lips",
    "mature oval face, calm gaze, understated makeup",
]

# 经典现代发型池（剔除古风发簪项，防止与现代/古风串味）
HAIRS = [
    "long straight black hair",
    "long wavy dark brown hair",
    "chestnut hair with soft highlights, half-up",
    "ash-gray hair in a high ponytail",
    "wine-red hair in loose waves",
    "pink-brown gradient hair, loose",
    "short black bob",
    "wet black hair pushed back",
    "light brown hair in a low ponytail",
    "deep brown hair with side-swept bangs",
]

HAIR_STYLES = ["跟随服装", "经典", "现代", "古风"]
HAIR_STYLE_TEXT = {
    "法式刘海": "medium-length hair with curtain bangs, soft French fringe framing the face, slightly messy texture",
    "八字刘海": "long hair parted in the middle with face-framing curtain bangs swept outward, soft volume at the crown",
    "锁骨发": "collarbone-length hair, blunt ends, light face-framing layers, tucked behind one ear",
    "高层次剪裁": "layered cut with high graduation, wispy ends, airy volume, textured movement",
    "狼尾": "shaggy wolf cut, layered choppy ends, longer strands at the nape, tousled texture",
    "公主切": "hime cut, straight cheek-length side locks with blunt ends, long straight back hair",
    "羊毛卷": "tight wool-wave perm, dense soft curls, voluminous and airy",
    "水波纹": "loose water-wave perm, soft S-shaped ripples, glossy finish",
}
HAIR_STYLE_POOL = _uniq([
    "collarbone-length hair with curtain bangs, light face-framing layers, natural movement",
    "medium-length layered cut with airy wispy ends, soft volume at the crown",
    "long hair in loose water waves, glossy and soft, parted slightly off-center",
    "shaggy layered cut with choppy ends and tousled texture, casual and modern",
    "hime cut with straight cheek-length side locks and long straight back hair",
    "soft wool-wave curls, voluminous and airy, framing the face",
    "high layered cut with textured ends, half-tucked behind one ear",
    "long hair with a wispy fringe, slightly messy texture, effortless styling",
    "shoulder-length blunt bob with a soft inward curve, tucked behind one ear",
    "long hair in a low loose braid with face-framing strands pulled out",
    "mid-length hair with a deep side part and soft blowout volume",
    "layered lob with curtain bangs and soft inward ends",
    "long hair in a high half-up ponytail with a soft face-framing fringe",
    "twin high ponytails with a wispy fringe, playful and clean",
    "sleek low bun with a center part and face-framing strands",
    "short ear-length blunt bob with a soft side part",
    "long hair in a loose braid over one shoulder, soft and natural",
] + list(HAIR_STYLE_TEXT.values()))

HAIR_COLORS = ["跟随发型", "现代", "古风"]
HAIR_COLOR_TEXT = {
    "自然黑": "natural black hair color",
    "冷茶棕": "cool tea-brown hair color, ashy undertone",
    "雾霾灰棕": "hazy ash-brown hair color, muted grey undertone",
    "奶茶灰": "milk-tea grey-brown hair color, soft and creamy",
    "黑茶": "dark tea-brown hair color, deep and glossy",
    "亚麻棕": "linen brown hair color, light and airy",
    "亚麻金": "light ash-blonde hair color, cool platinum undertone, soft natural root shadow",
    "浅蜜金": "light honey-beige blonde hair color, warm soft sheen, natural depth at the roots",
    "浅香槟金": "pale champagne blonde hair color, cool golden sheen, natural depth, no orange cast",
    "黑糖栗棕": "dark brown-sugar chestnut hair color, rich warm undertone, glossy finish",
    "冷灰黑": "cool grey-black hair color, subtle ink-black sheen, natural depth",
    "银灰": "ash-silver hair color, clean cool grey sheen, soft blended roots, no lavender cast",
    "焦糖茶棕": "caramel tea-brown hair color, warm honey undertone, soft sheen",
    "挂耳染": "two-tone hair color, soft ash-blonde inner layer peeking out near the ear, blended roots",
}

HAIR_STYLE_GUFENG = [
    "long straight black hair in a low bun with a jade hairpin",
    "long hair half-up with a gold buyao hairpin and dangling beads",
    "long black hair with a center part, a silver hairpin, loose strands framing the face",
    "twin loop buns with silk ribbons and small floral ornaments",
    "long hair in a high topknot with a jade crown and hanging tassels",
    "long wavy black hair with a pearl hairpin and a single flower ornament",
    "long hair in a loose side braid woven with silk ribbon and jade beads",
    "long hair with an elaborate phoenix hair crown and dangling ornaments",
    "long hair in a high ponytail tied with a long silk ribbon and a jade ornament",
    "long hair worn loose with a forehead ornament and jade earrings",
    "half-up style with a small jade crown and the rest flowing down the back",
]
HAIR_TINT_GUFENG = [
    "jet black hair color, deep and glossy",
    "cool ink-black hair color with a soft sheen",
    "dark chestnut hair color, warm and rich",
    "deep brown-black hair color, natural depth",
]


def _resolve_hair_style(hair_style, outfit_style):
    """当发型选「跟随服装」或「经典」遇上古风服装时，自动对齐古风发髻池，杜绝汉服配波波头。"""
    if hair_style in ("现代", "古风"):
        return hair_style
    if outfit_style == "古风":
        return "古风"
    if hair_style == "跟随服装":
        return "现代"
    return "经典"


def _hair_style_text(style, rng=None, outfit_style="现代"):
    eff = _resolve_hair_style(style, outfit_style)
    if eff in (None, "", "经典"):
        return None
    r = rng or random
    if eff == "古风":
        return r.choice(HAIR_STYLE_GUFENG)
    return r.choice(HAIR_STYLE_POOL)


def _hair_tint_text(color, rng=None):
    if color in (None, "", "跟随发型", "关闭"):
        return None
    r = rng or random
    if color == "古风":
        return r.choice(HAIR_TINT_GUFENG)
    return r.choice(list(HAIR_COLOR_TEXT.values()))


SKINS = [
    "fair skin",
    "warm beige skin",
    "porcelain skin",
    "sun-kissed skin",
    "dewy skin",
    "pale cool-toned skin",
]

BODIES = [
    "slim waist, soft hips",
    "curvy figure, wide hips",
    "slender figure, small waist",
    "athletic slim figure",
    "soft natural figure, balanced proportions",
]

# 默认/丰满池与「关闭」中性池解耦，修复选「罩杯=关闭」反而变巨乳的 Bug
BREASTS = [
    "full natural bust, round breasts",
    "natural feminine bust, soft round contours",
    "shapely natural bust, balanced proportions",
]
BUST_NEUTRAL_CLOTHED = "natural feminine figure, balanced upper body proportions"
BUST_NEUTRAL_NUDE = "natural medium bust"

CUPS = {
    "B": "a full B-cup bust, natural round shape",
    "C": "a full C-cup bust, natural round shape",
    "D": "a full D-cup bust, voluptuous round shape",
}
CUPS_NUDE = {
    "B": "a full B-cup bust, natural round shape",
    "C": "a full C-cup bust, natural round shape",
    "D": "a full D-cup bust, voluptuous round breasts",
}
CUP_CHOICES = ["B~C随机", "B", "C", "D", "关闭"]

HEIGHTS = [
    "petite frame, around 160 cm",
    "average height, around 165 cm",
    "tall slender frame, around 170 cm, long legs",
]

NECKLINES = ["跟随服装", "高领", "圆领", "低领", "深V", "一字肩"]
NECKLINE_TEXT = {
    "高领": "high neckline, chest fully covered",
    "圆领": "round neckline, chest fully covered",
    "低领": "low scoop neckline, subtle natural cleavage",
    "深V": "deep V neckline, subtle natural cleavage",
    "一字肩": "off-shoulder neckline, bare collarbones",
}
LOWCUT_HINTS = ("bikini", "camisole", "slip", "tank", "swimsuit", "cover-up", "lingerie")
LURE_LOWCUT_HINTS = ("halter", "sheer", "bodycon", "nightdress", "lace", "satin")

OUTFIT_STYLES = ["现代", "古风"]
GUFENG_STYLES = ("古风",)

OUTFITS_LURE = {
    "纯欲御姐": [
        "a sheer chiffon blouse over a lace bralette and a high-waisted bodycon skirt",
        "a black halter-neck backless bodycon dress",
        "a satin slip nightdress with thin straps and lace trim",
        "a deep-V ribbed knit bodycon dress with a high side slit",
        "a sheer mesh top over a fitted pencil skirt",
        "a champagne lace-trim camisole set",
        "a backless satin gown with a draped cowl neckline",
        "a fitted off-shoulder knit dress hugging the waist and hips",
    ],
    "通勤OL": [
        "a white silk blouse with the collar open and a black high-waisted pencil skirt",
        "a charcoal blazer over a lace camisole and a fitted midi skirt",
        "a crisp white shirt, a gray pencil skirt and sheer stockings",
        "a black sleeveless bodycon office dress",
        "a fitted turtleneck knit top and a leather skirt with a front slit",
        "a belted shirt dress with the top buttons left open",
        "a fitted gray suit with a silk camisole underneath",
    ],
    "私密居家": [
        "a black satin slip nightdress with lace trim",
        "a champagne silk camisole and shorts set",
        "a sheer lace nightdress over bare skin",
        "a fitted ribbed loungewear set with a deep scoop neck",
        "a thin sheer robe over a satin slip",
        "an oversized white shirt worn open over a lace bralette",
        "a soft knit robe tied loosely at the waist, one shoulder slipping",
    ],
    "运动休闲": [
        "a seamless sports bra and high-waisted leggings set",
        "a cropped hoodie over a sports top and bike shorts",
        "a fitted tank top and running shorts with a light windbreaker",
        "a sage green yoga set with a cropped long-sleeve top",
        "a fitted cycling jersey with padded shorts",
        "an oversized gym tee and short shorts",
        "a white tennis dress with a pleated skirt",
    ],
    "甜酷街头": [
        "an oversized graphic hoodie with a pleated mini skirt and chunky boots",
        "a cropped leather jacket over a crop top and cargo pants",
        "a slip dress layered with a chunky knit cardigan and platform boots",
        "a varsity jacket with a mini skirt and thigh-high socks",
        "a denim corset top with wide-leg jeans and a chain belt",
        "a sheer long-sleeve top over a bralette and low-rise jeans",
    ],
    "泳装度假": [
        "a white string bikini with a sheer sarong wrapped at the hips",
        "a black one-piece swimsuit with a deep V neckline and cut-out sides",
        "a high-waisted bikini with a crochet cover-up shirt",
        "a strapless bandeau bikini with a wide sun hat",
        "a ribbed bikini set with a long open beach shirt",
        "a sleek one-shoulder swimsuit with gold hardware",
    ],
    "晚礼服": [
        "a floor-length satin gown with a draped cowl neckline and a thigh slit",
        "a black fishtail gown with a deep V back and delicate straps",
        "a champagne sequin dress with a halter neckline and an open back",
        "a silk slip gown with thin straps and a low draped back",
        "a fitted velvet gown with off-shoulder sleeves and a side slit",
        "a sheer layered tulle gown with an embroidered bodice",
    ],
}

NIGHT_SCENES = [
    ("dimly lit bedroom at night, warm bedside lamp, rumpled white sheets", "indoor", "bed"),
    ("quiet living room late at night, a single floor lamp, a glass of wine on the table", "indoor", "indoor_generic"),
    ("hotel room with floor-to-ceiling windows and city lights at midnight", "indoor", "bed"),
    ("apartment at midnight, rain streaking down the window, soft lamp glow", "indoor", "indoor_generic"),
    ("warm-lit bathroom at night, steam on the mirror, soft shadows", "indoor", "bath"),
    ("balcony at night with distant city lights and cool night air", "outdoor", "outdoor"),
]

MODERN_SCENES = [
    ("bright minimalist loft apartment with floor-to-ceiling windows, soft daylight", "indoor", "indoor_generic"),
    ("specialty coffee shop with warm wood, hanging plants and afternoon light", "indoor", "kitchen"),
    ("city street after rain with neon reflections at night", "outdoor", "outdoor"),
    ("modern co-working space with glass partitions in late afternoon", "indoor", "indoor_generic"),
    ("rooftop terrace with a city skyline at golden hour", "outdoor", "outdoor"),
    ("art gallery with white walls and soft spotlights", "indoor", "indoor_generic"),
    ("convenience store aisle at night under cool fluorescent light", "indoor", "indoor_generic"),
    ("bright gym studio with mirrors and soft window light", "indoor", "indoor_generic"),
    ("subway platform in the evening with motion blur", "indoor", "indoor_generic"),
    ("hotel lobby with marble floors and warm ambient light", "indoor", "indoor_generic"),
    ("seaside highway at sunset with the ocean on one side", "outdoor", "outdoor"),
    ("rooftop pool at dusk with city lights below", "outdoor", "outdoor"),
    ("desert campsite at blue hour with string lights", "outdoor", "outdoor"),
    ("industrial loft studio with concrete walls and tall windows", "indoor", "indoor_generic"),
    ("rocky seaside cove at golden hour with waves breaking below", "outdoor", "outdoor"),
    ("desert highway at dusk with heat haze and distant mesas", "outdoor", "outdoor"),
    ("snow field at blue hour with bare trees and soft falling snow", "outdoor", "outdoor"),
    ("greenhouse conservatory with glass panes and hanging vines", "indoor", "indoor_generic"),
]

OUTFITS_MODERN = [
    "an oversized cream knit sweater with wide-leg trousers",
    "a cropped ribbed cardigan over a satin slip skirt",
    "a relaxed linen shirt and tailored shorts",
    "a fitted tank top with high-waisted wide-leg jeans",
    "a slip dress with a leather jacket over it",
    "a cropped bomber jacket and cargo pants",
    "a seamless athleisure set with a cropped hoodie",
    "a long trench coat over a knit top and straight jeans",
    "a knitted polo shirt and a pleated midi skirt",
    "a denim jacket over a white tee and mom jeans",
    "a sheer mesh top layered over a bandeau and wide trousers",
    "a fitted bodysuit with tailored trousers",
    "an oversized shirt dress with a belt and sneakers",
    "a cropped puffer vest over a long-sleeve tee",
]

GUFENG_SCENES = [
    ("moonlit courtyard with stone lanterns and plum branches", "outdoor", "outdoor"),
    ("traditional wooden corridor with carved lattice windows and soft lantern light", "indoor", "indoor_generic"),
    ("bamboo grove with dappled light and drifting mist", "outdoor", "outdoor"),
    ("ancient-style bedroom with silk curtains and a carved wooden screen", "indoor", "bed"),
    ("palace hall with red pillars and hanging silk drapery", "indoor", "indoor_generic"),
    ("lotus pond with a stone bridge at dusk", "outdoor", "outdoor"),
    ("snowy night outside a pavilion, warm lantern glow", "outdoor", "outdoor"),
    ("study room with scrolls, an incense burner and warm candlelight", "indoor", "indoor_generic"),
    ("horse ranch at dawn with mist over the grassland", "outdoor", "outdoor"),
    ("vast grassland under a wide sky with distant mountains", "outdoor", "outdoor"),
    ("snowy mountain pass with pine trees and cold light", "outdoor", "outdoor"),
    ("jianghu inn with wooden beams, red lanterns and wine jars", "indoor", "indoor_generic"),
    ("immortal mountain peak above a sea of clouds at dawn", "outdoor", "outdoor"),
    ("lotus pond at night with a small boat and lantern reflections", "outdoor", "outdoor"),
    ("snow-covered plum grove with a stone lantern and falling petals", "outdoor", "outdoor"),
    ("bamboo pavilion with hanging gauze curtains and incense smoke", "indoor", "indoor_generic"),
]

NUDE_SCENES = [
    ("sunlit grassland with tall grass and soft wind", "outdoor", "outdoor", "自然野外"),
    ("quiet lakeside at dawn with mist over the water", "outdoor", "outdoor", "自然野外"),
    ("secluded beach cove with rocks and clear water", "outdoor", "outdoor", "自然野外"),
    ("forest clearing with dappled sunlight and moss", "outdoor", "outdoor", "自然野外"),
    ("desert dunes at golden hour with soft shadows", "outdoor", "outdoor", "自然野外"),
    ("horse ranch stable with warm afternoon light and straw", "indoor", "indoor_generic", "自然野外"),
    ("minimal bedroom with white sheets and soft window light", "indoor", "bed", "室内私密"),
    ("warm-lit bathroom with steam on the mirror", "indoor", "bath", "室内私密"),
    ("quiet studio with a linen backdrop and soft key light", "indoor", "indoor_generic", "室内私密"),
]

OUTFITS_GUFENG = {
    "古风·华丽": [
        "an embroidered gold-thread hanfu with layered wide sleeves, a jade belt and hanging tassels",
        "a Tang-style chest-high ruqun in vermilion silk with a flowing silk shawl and gold hairpins",
        "a Ming-style standing-collar robe with a gold-woven horse-face skirt and pearl hair ornaments",
        "a deep crimson brocade gown with phoenix embroidery, a jadeite pendant and an elaborate hair crown",
        "a Wei-Jin style wide-sleeved robe in ink blue with a silver hairpin and a long silk sash",
        "a silk qipao gown with a high collar, gold embroidery and pearl earrings",
        "a sheer gauze outer robe over a satin inner dress, moon-white and silver, with jade ornaments",
        "an imperial-style robe in royal purple with dragon embroidery, a gold crown and a jade belt",
        "a red wedding hanfu with a gold phoenix crown and layered silk veils",
        "a light blue hanfu with embroidered plum blossoms, a silver hairpin and a round silk fan",
        "a dark green brocade coat over a cream dress with a jade bangle and a jade hairpin",
        "a layered Song-style beizi and pleated baidie skirt in celadon and ivory, jade bracelet, silk ribbon",
    ],
    "古风·清雅": [
        "a plain white hanfu with subtle embroidery, a wooden hairpin and a bamboo flute",
        "a pale grey-blue beizi over a long skirt with minimal jade jewelry",
        "a light green ruqun with a soft shawl and a simple bun pinned with jade",
        "a moon-white scholar robe with a dark sash and a folding fan in hand",
        "a pale pink hanfu with delicate floral embroidery and a silk ribbon",
        "a simple black robe with silver trim and a silver hairpin",
        "a cream cross-collar robe with a light silk scarf and hair half-up",
        "a soft lavender hanfu with layered skirts and a single jade pendant",
    ],
    "古风·飒爽": [
        "a fitted dark green riding outfit with a short cape, leather boots and a sword at her hip",
        "a Tang-style hufu riding suit with narrow sleeves, a leather belt and riding boots",
        "a white martial-arts robe with a wide sash, arm guards and a long high ponytail",
        "a dark blue cavalry coat with fur trim, leather bracers and a bow across her back",
        "a red battle robe with light armor plates, a jade-handled sword and leather boots",
        "a flowing white swordswoman robe with silver embroidery and a bamboo hat",
        "a black fitted riding dress with a high slit, leather gloves and knee-high boots",
        "a gold-trimmed warrior hanfu with shoulder guards and a crimson cape",
    ],
    "古风·媚": [
        "a Tang-style chest-high ruqun in rose silk with a sheer shawl and gold hairpins",
        "a translucent gauze robe over a silk inner dress, jade ornaments and a flower hairpin",
        "a deep V cross-collar hanfu in crimson with gold embroidery and dangling earrings",
        "a soft pink hanfu with a wide open collar, silk ribbon and pearl hairpins",
        "a black and gold hanfu with a plunging neckline and an ornate hair crown",
        "a sheer layered hanfu in moon-white with silver embroidery and bare shoulders",
        "a purple Tang-style dress with a draped shawl, gold bangles and a flower crown",
    ],
    "古风·宽袖": [
        "a flowing wide-sleeved hanfu with layered gauze skirts, a long silk sash and jade ornaments",
        "a Tang-style wide-sleeve robe in ivory with a painted shawl and a low jade belt",
        "a Wei-Jin wide-sleeved gauze robe in moon white with long trailing sleeves and a silk ribbon",
        "a layered hanfu with oversized flowing sleeves, gold-thread cloud embroidery and a jade pendant",
        "a pale blue wide-sleeved gown with a long gauze shawl and pearl hair ornaments",
        "a black and silver wide-sleeved robe with flowing sleeves and a tasseled jade belt",
    ],
    "古风·仙侠": [
        "a layered sheer immortal robe in silver white with floating gauze sleeves and a jade crown",
        "a pale cyan celestial gown with a long trailing shawl and silver hair ornaments",
        "a misty lavender immortal dress with wide gauze sleeves and a lotus jade pendant",
        "a silver-embroidered white immortal robe with a high collar and floating ribbons",
        "a flowing pale gold immortal gown with cloud embroidery and crystal hairpins",
        "a translucent blue immortal robe layered over a satin slip with a jade forehead ornament",
    ],
}

# --- v66 新增现代主题池（独立子库，仅显式选中「主题细分」时进入，避免污染随机池）---
OUTFITS_MODERN_EXTRA = {
    "现代·新中式旗袍": [
        "a modern fitted qipao in ivory silk with a mandarin collar and side slits",
        "a black velvet cheongsam with gold frog buttons and a high slit",
        "a pale blue brocade qipao with cap sleeves and a jade button",
        "a sleeveless ink-black qipao with silver embroidery at the hem",
        "a rose silk qipao with a low mandarin collar and a slit skirt",
        "a short champagne satin qipao dress with a diagonal hem",
    ],
    "现代·校园清纯": [
        "a white short-sleeve shirt with a pleated navy skirt and a knotted ribbon tie",
        "a sailor-collar blouse with a red neckerchief and a pleated skirt",
        "a cream knit vest over a white shirt and a dark pleated skirt",
        "a light blue shirt dress with white sneakers and ankle socks",
        "a navy blazer over a white shirt and a pleated skirt",
        "a white cotton blouse with a pinafore dress and a canvas tote",
    ],
    "现代·法式优雅": [
        "a cream silk blouse with a bow collar and high-waisted wide trousers",
        "a navy polka-dot wrap dress with a fitted waist",
        "a beige trench dress with a belt and pointed heels",
        "a black off-shoulder knit top with a silk midi skirt",
        "a white lace blouse with a pleated camel skirt",
        "a fine-knit boat-neck top with cropped tailored trousers and a silk scarf",
    ],
    "现代·街头机能": [
        "a black technical shell jacket with utility straps over a fitted tank and cargo pants",
        "an oversized utility vest with pockets over a long-sleeve top and wide cargo trousers",
        "a cropped windbreaker with a buckle harness and high-waisted cargo pants",
        "a grey techwear jumpsuit with zip detailing and chunky sneakers",
        "a hooded shell coat with reflective piping over a fitted bodysuit",
        "a cropped nylon jacket with webbing straps and tapered cargo pants",
    ],
    "现代·婚纱白纱": [
        "a strapless white wedding gown with a fitted bodice and a full tulle skirt",
        "a mermaid wedding dress in ivory lace with a sheer back and a chapel train",
        "a sleeveless satin bridal gown with a draped cowl neckline and a long tulle veil",
        "an off-shoulder white gown with lace sleeves and a pearl belt",
        "a sheer-layered tulle bridal dress with a beaded bodice",
        "a simple white slip wedding dress with thin straps and a cathedral veil",
    ],
    "现代·度假亚麻": [
        "a white linen shirt dress with the sleeves rolled up and a straw hat",
        "a beige linen co-ord set with a cropped top and wide trousers",
        "a pale blue linen sundress with thin straps and a woven bag",
        "an oversized linen shirt worn open over a bikini top and shorts",
        "a cotton eyelet dress with a square neckline and a straw tote",
        "a light linen jumpsuit with a tie waist and leather sandals",
    ],
    "现代·暗夜酷感": [
        "a black leather corset top with high-waisted wide trousers",
        "a fitted black slip dress with a leather biker jacket over it",
        "a dark mesh long-sleeve top over a bandeau and a leather mini skirt",
        "a black halter bodysuit with a chain belt and slim trousers",
        "a sheer black shirt worn open over a lace bralette and leather pants",
        "a black satin corset dress with a lace-up back and thigh-high boots",
    ],
}

# --- v66 新增古风主题池 ---
OUTFITS_GUFENG_EXTRA = {
    "古风·婚嫁红妆": [
        "a red wedding hanfu with gold phoenix embroidery, a phoenix crown and a red silk shawl",
        "a crimson bridal robe with gold thread patterns and a beaded tassel headpiece",
        "a Tang-style red wedding ruqun with a gold-embroidered shawl and flower ornaments",
        "a deep red brocade wedding gown with a gold crown and layered silk drapes",
        "a scarlet xi-fu set with embroidered cuffs, a jade belt and hanging tassels",
        "a red silk bridal dress with gold cloud embroidery and a pearl forehead ornament",
    ],
    "古风·异域胡旋": [
        "a silk hufu dance costume with a fitted bodice, wide trousers and a beaded belt",
        "a turquoise and gold ethnic robe with embroidered trim and coin ornaments",
        "a layered gauze dance dress in saffron with silver bangles and a beaded headdress",
        "a fitted brocade vest over a sheer silk blouse with wide patterned trousers",
        "a purple desert robe with gold embroidery and coin tassels",
        "a red silk dance outfit with a bare midriff and a layered coin belt",
    ],
    "古风·禅意道袍": [
        "a plain grey Taoist robe with wide sleeves and a cloth belt",
        "a linen monk-style robe in pale oat with a wooden prayer bead necklace",
        "a cream zen robe with a crossed collar and a simple hemp sash",
        "a dark indigo loose robe with a layered collar and cloth shoes",
        "a pale tea-colored meditation robe with wide sleeves and a bamboo fan",
    ],
    "古风·女扮男装": [
        "a white scholar robe with a dark sash and a folding fan",
        "a black brocade men's robe with silver trim and a jade pendant",
        "a light blue scholar's changpao with a scholar's cap and a book in hand",
        "a dark blue riding robe with a leather belt and a short sword",
        "a grey linen men's robe with a wide sash and a bamboo flute",
    ],
}

SCENES = [
    ("sunlit bedroom with white sheets and sheer curtains, soft morning light", "indoor", "bed",
     ["a fitted white cotton t-shirt and gray lounge shorts",
      "a white shirt tied at the waist and black cotton shorts",
      "a white lace camisole and soft cotton shorts",
      "a pale pink pajama set"]),
    ("modern bedroom at night with warm bedside lamp and dark wood headboard", "indoor", "bed",
     ["a fitted thin white camisole and gray shorts",
      "a fitted gray t-shirt",
      "a black satin slip"]),
    ("small apartment living room with a fabric sofa and afternoon light", "indoor", "indoor_generic",
     ["a beige knit sweater and jeans",
      "a white tank top and gray sweatpants",
      "a fitted cardigan over a camisole"]),
    ("minimalist apartment with white walls and a large window, soft daylight", "indoor", "indoor_generic",
     ["a white ribbed tank top and beige trousers",
      "a fitted light gray knit dress",
      "a white shirt and straight jeans"]),
    ("cozy kitchen with morning light and a cup of coffee on the counter", "indoor", "kitchen",
     ["a white t-shirt and denim shorts, a fitted linen apron",
      "a fitted white shirt and shorts",
      "a soft gray tank top and shorts"]),
    ("modern bathroom with marble wall, soft diffused light and steam", "indoor", "bath",
     ["a white towel wrapped around her body",
      "a white bathrobe tied at the waist",
      "a white towel around the waist"]),
    ("balcony at dusk with city view and warm string lights", "outdoor", "outdoor",
     ["a fitted knit cardigan and shorts",
      "a white camisole and wide-leg trousers",
      "a fitted summer dress"]),
    ("rooftop terrace at sunset with plants and string lights", "outdoor", "outdoor",
     ["a white tank top and denim shorts",
      "a fitted summer dress",
      "a fitted cropped knit top and tailored trousers"]),
    ("cozy cafe by the window with a coffee cup, warm afternoon light", "indoor", "kitchen",
     ["a beige knit sweater and jeans",
      "a white blouse and dark trousers",
      "a light cardigan over a white top"]),
    ("bookstore aisle with warm lamps and tall shelves", "indoor", "indoor_generic",
     ["a white shirt and beige trousers",
      "a gray knit sweater and jeans",
      "a fitted long cardigan over a camisole"]),
    ("supermarket aisle with fluorescent light and colorful shelves", "indoor", "indoor_generic",
     ["a white t-shirt and jeans",
      "a gray hoodie and shorts",
      "a fitted jacket over a top"]),
    ("subway car in the evening with window reflections", "indoor", "indoor_generic",
     ["a white t-shirt and black trousers",
      "a gray knit sweater and jeans",
      "a fitted trench coat over a top"]),
    ("city street at dusk with blurred shop lights", "outdoor", "outdoor",
     ["a denim jacket over a white top and jeans",
      "a black slip dress",
      "a light coat over a knit top"]),
    ("park bench in the afternoon with autumn leaves", "outdoor", "outdoor",
     ["a beige knit sweater and jeans",
      "a fitted white t-shirt and tailored trousers",
      "a light jacket over a hoodie"]),
    ("riverside walkway at golden hour", "outdoor", "outdoor",
     ["a white t-shirt and shorts",
      "a fitted summer dress",
      "a tank top and jeans"]),
    ("quiet beach at sunset with gentle waves", "outdoor", "outdoor",
     ["a white bikini",
      "a black one-piece swimsuit",
      "a fitted sheer cover-up over a bikini"]),
    ("poolside at golden hour with water reflections", "outdoor", "outdoor",
     ["a white bikini",
      "a black one-piece swimsuit",
      "a light cover-up over a bikini"]),
    ("hotel room with floor-to-ceiling window and city lights at night", "indoor", "bed",
     ["a white bathrobe",
      "a black satin slip",
      "a thin white camisole and shorts"]),
    ("small gym studio with soft window light", "indoor", "indoor_generic",
     ["a gray sports bra and leggings",
      "a white tank top and shorts",
      "a black athletic set"]),
    ("art studio with north window light and canvases", "indoor", "indoor_generic",
     ["a fitted paint-stained white shirt and shorts",
      "a gray tank top and jeans",
      "a fitted white shirt"]),
    ("garden patio in the morning with plants and soft light", "outdoor", "outdoor",
     ["a fitted summer dress",
      "a white blouse and shorts",
      "a knit cardigan over a camisole"]),
    ("forest path with dappled sunlight", "outdoor", "outdoor",
     ["a white t-shirt and shorts",
      "a light dress",
      "a tank top and jeans"]),
    ("lake dock in the misty morning", "outdoor", "outdoor",
     ["a white knit sweater and shorts",
      "a fitted jacket over a top",
      "a fitted long cardigan over a camisole"]),
    ("home office with a desk lamp and books", "indoor", "indoor_generic",
     ["a white shirt and trousers",
      "a gray knit sweater",
      "a camisole and cardigan"]),
    ("attic room with a skylight and soft daylight", "indoor", "bed",
     ["a white t-shirt and shorts",
      "a light dress",
      "a fitted white shirt"]),
    ("vintage apartment with tall windows and wooden floor", "indoor", "bed",
     ["a white blouse and long skirt",
      "a knit sweater and jeans",
      "a slip dress"]),
    ("quiet tea room with warm light and a low table", "indoor", "kitchen",
     ["a fitted knit top and tailored trousers",
      "a light cardigan over a camisole",
      "a fitted simple dress"]),
    ("courtyard with potted plants and soft afternoon light", "outdoor", "outdoor",
     ["a white t-shirt and shorts",
      "a fitted summer dress",
      "a tank top and jeans"]),
    ("night market with warm lanterns and food stalls", "outdoor", "outdoor",
     ["a white t-shirt and jeans",
      "a fitted jacket over a top",
      "a casual dress"]),
    ("train compartment with a large window and passing countryside", "indoor", "indoor_generic",
     ["a white t-shirt and trousers",
      "a knit sweater and jeans",
      "a fitted coat over a top"]),
    ("greenhouse with plants and diffuse light", "indoor", "indoor_generic",
     ["a white dress",
      "a tank top and shorts",
      "a fitted light shirt"]),
    ("library with tall shelves and warm reading lamps", "indoor", "indoor_generic",
     ["a white blouse and long skirt",
      "a knit sweater and trousers",
      "a cardigan over a camisole"]),
    ("sunlit classroom with wooden desks and tall windows, warm afternoon light", "indoor", "indoor_generic",
     ["a white shirt and a pleated skirt",
      "a cream knit vest over a white blouse",
      "a navy blazer over a light shirt"]),
    ("bright photo studio with a white seamless backdrop and softbox light", "indoor", "indoor_generic",
     ["a fitted ribbed tank top and tailored trousers",
      "a plain white shirt and denim shorts",
      "a simple slip dress"]),
    ("european stone street with cafe terraces and warm afternoon light", "outdoor", "outdoor",
     ["a light trench coat over a white blouse and jeans",
      "a floral summer dress and a straw bag",
      "a fitted knit top and wide-leg trousers"]),
    ("small chapel with stained glass and pale wooden pews, soft window light", "indoor", "indoor_generic",
     ["a white satin slip dress",
      "a pale blue midi dress with a cardigan",
      "a fitted ivory dress"]),
    ("resort villa poolside with palm shadows and white loungers", "outdoor", "outdoor",
     ["a white bikini with a sheer sarong",
      "a linen shirt dress and a straw hat",
      "a light cover-up over a bikini"]),
    ("campus courtyard with old trees and stone steps, late afternoon light", "outdoor", "outdoor",
     ["a white shirt and a pleated skirt",
      "a cream knit vest and shorts",
      "a light cardigan over a white top"]),
    ("industrial alley with concrete walls and faded graffiti, dusk light", "outdoor", "outdoor",
     ["a black leather jacket over a tank and cargo pants",
      "a fitted grey hoodie and wide trousers",
      "a cropped bomber jacket and shorts"]),
]

OUTFITS_MODERN_DAILY = _uniq(
    OUTFITS_MODERN + [o for (_t, _k, _g, _outfits) in SCENES for o in _outfits]
)
OUTFITS_MODERN_ALL = _uniq(
    OUTFITS_MODERN_DAILY
    + OUTFITS_LURE["纯欲御姐"]
    + OUTFITS_LURE["通勤OL"]
    + OUTFITS_LURE["私密居家"]
    + OUTFITS_LURE["运动休闲"]
    + OUTFITS_LURE["甜酷街头"]
    + OUTFITS_LURE["泳装度假"]
    + OUTFITS_LURE["晚礼服"]
    + _flat_map(OUTFITS_MODERN_EXTRA)
)
OUTFITS_GUFENG_ALL = _uniq(
    OUTFITS_GUFENG["古风·华丽"]
    + OUTFITS_GUFENG["古风·清雅"]
    + OUTFITS_GUFENG["古风·飒爽"]
    + OUTFITS_GUFENG["古风·媚"]
    + OUTFITS_GUFENG["古风·宽袖"]
    + OUTFITS_GUFENG["古风·仙侠"]
    + _flat_map(OUTFITS_GUFENG_EXTRA)
)
MODERN_SCENES_ALL = _uniq(
    MODERN_SCENES
    + [(t, k, g) for (t, k, g, _c) in NUDE_SCENES]
    + NIGHT_SCENES
    + [(t, k, g) for (t, k, g, _o) in SCENES]
)
GUFENG_SCENES_ALL = GUFENG_SCENES

# --- 26 档主题细分池（v66 扩表：现代 15 档 + 古风 10 档 + 自动随机）---
SUB_THEMES = [
    "自动随机",
    "现代·日常穿搭",
    "现代·纯欲御姐",
    "现代·通勤OL",
    "现代·私密居家",
    "现代·运动休闲",
    "现代·甜酷街头",
    "现代·泳装度假",
    "现代·晚礼服",
    "现代·新中式旗袍",
    "现代·校园清纯",
    "现代·法式优雅",
    "现代·街头机能",
    "现代·婚纱白纱",
    "现代·度假亚麻",
    "现代·暗夜酷感",
    "古风·华丽宫廷",
    "古风·清雅书卷",
    "古风·飒爽侠女",
    "古风·妩媚风情",
    "古风·魏晋宽袖",
    "古风·飘逸仙侠",
    "古风·婚嫁红妆",
    "古风·异域胡旋",
    "古风·禅意道袍",
    "古风·女扮男装",
]

SUB_THEME_POOL_MAP = {
    "现代·日常穿搭": OUTFITS_MODERN_DAILY,
    "现代·纯欲御姐": OUTFITS_LURE["纯欲御姐"],
    "现代·通勤OL": OUTFITS_LURE["通勤OL"],
    "现代·私密居家": OUTFITS_LURE["私密居家"],
    "现代·运动休闲": OUTFITS_LURE["运动休闲"],
    "现代·甜酷街头": OUTFITS_LURE["甜酷街头"],
    "现代·泳装度假": OUTFITS_LURE["泳装度假"],
    "现代·晚礼服": OUTFITS_LURE["晚礼服"],
    "古风·华丽宫廷": OUTFITS_GUFENG["古风·华丽"],
    "古风·清雅书卷": OUTFITS_GUFENG["古风·清雅"],
    "古风·飒爽侠女": OUTFITS_GUFENG["古风·飒爽"],
    "古风·妩媚风情": OUTFITS_GUFENG["古风·媚"],
    "古风·魏晋宽袖": OUTFITS_GUFENG["古风·宽袖"],
    "古风·飘逸仙侠": OUTFITS_GUFENG["古风·仙侠"],
}

for _k, _v in OUTFITS_MODERN_EXTRA.items():
    SUB_THEME_POOL_MAP[_k] = _v
for _k, _v in OUTFITS_GUFENG_EXTRA.items():
    SUB_THEME_POOL_MAP[_k] = _v

# 主题 → 场景关键词软过滤（命中不足 3 条时自动放弃过滤，保证不会无场景可用）
SUB_THEME_SCENE_HINTS = {
    "现代·日常穿搭": ("bedroom", "apartment", "living room", "balcony", "cafe", "park", "street", "kitchen"),
    "现代·纯欲御姐": ("loft", "apartment", "bedroom", "hotel room", "gallery", "living room", "studio", "terrace"),
    "现代·通勤OL": ("office", "co-working", "loft", "lobby", "cafe", "street", "gallery", "train", "studio"),
    "现代·私密居家": ("bedroom", "living room", "bathroom", "apartment", "attic", "hotel room", "vintage apartment"),
    "现代·运动休闲": ("gym", "studio", "rooftop", "park", "riverside", "forest", "balcony", "seaside", "pool"),
    "现代·甜酷街头": ("street", "subway", "convenience", "industrial", "night market", "rooftop", "neon", "alley"),
    "现代·泳装度假": ("pool", "beach", "cove", "seaside", "lakeside", "rooftop", "spa", "dock"),
    "现代·晚礼服": ("lobby", "gallery", "terrace", "rooftop", "loft", "chapel", "garden"),
    "现代·新中式旗袍": ("tea room", "gallery", "courtyard", "garden", "vintage apartment", "hotel lobby", "loft"),
    "现代·校园清纯": ("classroom", "library", "bookstore", "cafe", "campus", "courtyard", "art studio"),
    "现代·法式优雅": ("cafe", "street", "garden", "patio", "balcony", "gallery", "vintage apartment", "tea room", "terrace"),
    "现代·街头机能": ("street", "industrial", "alley", "subway", "night market", "rooftop", "neon", "convenience"),
    "现代·婚纱白纱": ("chapel", "gallery", "lobby", "terrace", "rooftop", "garden", "studio", "loft"),
    "现代·度假亚麻": ("beach", "seaside", "cove", "lakeside", "desert", "garden", "terrace", "dock", "pool", "patio"),
    "现代·暗夜酷感": ("industrial", "night", "neon", "night market", "street", "subway", "gallery", "alley", "loft"),
}


# --- 摄影大师级光影与情绪眼神池 ---
LIGHTING_CHOICES = ["跟随场景", "自然柔光", "落日逆光", "暗调情绪", "闪光直打", "霓虹夜景"]
LIGHTING_TEXT = {
    "自然柔光": "soft diffused window daylight, clean airy atmosphere, even exposure",
    "落日逆光": "warm golden hour backlight, glowing rim light on hair, sun flare, warm atmospheric tones",
    "暗调情绪": "chiaroscuro low-key lighting, directional side light, deep cinematic shadows, moody atmosphere",
    "闪光直打": "direct on-camera flash photography, crisp high-contrast highlights, candid editorial vibe",
    "霓虹夜景": "ambient neon city glow, cyan and magenta rim reflections, cinematic night atmosphere",
}

MOOD_CHOICES = ["自然随机", "直视互动", "松弛抓拍", "清冷高级", "温婉甜美", "微醺慵懒"]
MOOD_TEXT = {
    "直视互动": "looking directly into the lens, engaging eye contact, subtle intimate expression",
    "松弛抓拍": "candid unposed moment, gaze averted softly away from camera, relaxed natural poise",
    "清冷高级": "aloof editorial expression, cool composed gaze, lips slightly parted, high-fashion vibe",
    "温婉甜美": "warm gentle smile, soft curved eyes, approachable and tender expression",
    "微醺慵懒": "languid half-lidded gaze, relaxed sensual mood, soft dreamy expression",
}

# --- v66 相机滤镜：常见人像机身的色彩科学 + 特殊滤镜质感 ---
CAMERA_FILTERS = [
    "关闭",
    "佳能 R5·奶油肤色",
    "佳能 5D4·胶片暖调",
    "尼康 Z8·通透中性",
    "尼康 D850·高解析",
    "索尼 A7RV·锐利清冷",
    "索尼 A7M4·电影青橙",
    "富士 XT5·Classic Chrome",
    "富士 X100VI·Classic Neg",
    "富士 GFX100·Pro Neg 柔肤",
    "徕卡 M11·德味浓郁",
    "徕卡 SL2·微反差",
    "哈苏 X2D·中画幅自然",
    "飞思 IQ4·商业肤色",
    "柯达 Portra400·柔肤",
    "柯达 Gold200·暖黄怀旧",
    "富士 Pro400H·青调柔肤",
    "CineStill800T·夜景钨丝",
    "柯达 Ektar100·高饱和",
    "依尔福 HP5·黑白颗粒",
    "黑柔 1/4·Black Mist",
    "白柔·Glimmerglass",
    "柔焦·Softar 朦胧",
    "星光镜·十字星芒",
]
CAMERA_FILTER_STRENGTHS = ["弱", "中", "强"]

# 每组 = (核心色彩科学 / 质感, [特征子句...], 强度密度表 or None)
# 「强度」调的是**描述浓度**：弱 = 只留核心一句并加 subtle；中 = 核心 + 前 2 个特征；强 = 全部特征。
# 物理滤镜类额外带真实密度档（Black Mist 1/8→1/4、Softar I→III、星芒 4→8 线）。
CAMERA_FILTER_PARTS = {
    "佳能 R5·奶油肤色": (
        "Canon EOS R5 color science, creamy warm skin tones",
        ["soft highlight roll-off", "gentle contrast", "silky bokeh"],
    ),
    "佳能 5D4·胶片暖调": (
        "Canon EOS 5D Mark IV look, warm filmic tone curve",
        ["soft skin with rosy warmth", "gentle shadow lift", "classic editorial warmth"],
    ),
    "尼康 Z8·通透中性": (
        "Nikon Z8 color science, neutral true-to-life color",
        ["high micro-contrast", "clean skin texture", "crisp detail"],
    ),
    "尼康 D850·高解析": (
        "Nikon D850 rendering, high-resolution crisp detail",
        ["slightly cool neutral balance", "deep tonal gradation"],
    ),
    "索尼 A7RV·锐利清冷": (
        "Sony A7R V color science, razor-sharp detail",
        ["slightly cool teal shadows", "clean highlights"],
    ),
    "索尼 A7M4·电影青橙": (
        "Sony A7 IV video look, teal and orange cinematic grade",
        ["lifted blacks", "soft highlight bloom", "filmic contrast"],
    ),
    "富士 XT5·Classic Chrome": (
        "Fujifilm X-T5 Classic Chrome film simulation, muted tones",
        ["cyan-leaning shadows", "documentary color", "fine film grain"],
    ),
    "富士 X100VI·Classic Neg": (
        "Fujifilm X100VI Classic Neg film simulation, nostalgic contrast",
        ["amber highlights", "deep greens", "subtle grain"],
    ),
    "富士 GFX100·Pro Neg 柔肤": (
        "Fujifilm GFX100 II Pro Neg Std film simulation, soft pastel skin",
        ["medium-format tonal smoothness", "gentle highlight roll-off"],
    ),
    "徕卡 M11·德味浓郁": (
        "Leica M11 rendering, rich saturated midtones",
        ["deep three-dimensional micro-contrast", "gentle highlight falloff",
         "classic Leica glow"],
    ),
    "徕卡 SL2·微反差": (
        "Leica SL2 rendering, strong micro-contrast",
        ["crisp detail with smooth skin", "neutral-warm balance", "subtle vignetting"],
    ),
    "哈苏 X2D·中画幅自然": (
        "Hasselblad X2D medium-format color, natural skin tones",
        ["extremely smooth tonal transitions", "gentle highlight roll-off", "quiet contrast"],
    ),
    "飞思 IQ4·商业肤色": (
        "Phase One IQ4 commercial rendering, flawless skin gradation",
        ["precise color accuracy", "high dynamic range", "editorial polish"],
    ),
    "柯达 Portra400·柔肤": (
        "Kodak Portra 400 film look, soft warm skin tones",
        ["creamy highlights", "fine natural grain", "gentle pastel shadows"],
    ),
    "柯达 Gold200·暖黄怀旧": (
        "Kodak Gold 200 film look, warm golden cast",
        ["nostalgic yellow highlights", "visible grain", "sunny amateur-photo warmth"],
    ),
    "富士 Pro400H·青调柔肤": (
        "Fujifilm Pro 400H film look, airy cyan-green cast",
        ["soft pastel skin", "bright low-contrast highlights", "delicate grain"],
    ),
    "CineStill800T·夜景钨丝": (
        "CineStill 800T tungsten film look, halation glow around highlights",
        ["cool blue tungsten ambience", "warm skin under practical lights", "visible grain"],
    ),
    "柯达 Ektar100·高饱和": (
        "Kodak Ektar 100 film look, high saturation",
        ["vivid reds and blues", "ultra-fine grain", "crisp clean contrast"],
    ),
    "依尔福 HP5·黑白颗粒": (
        "Ilford HP5 Plus black and white film look, monochrome",
        ["rich tonal range", "visible grain", "deep blacks", "classic documentary contrast"],
    ),
    "黑柔 1/4·Black Mist": (
        "{d} diffusion filter, glowing halated highlights",
        ["softened contrast", "milky blacks", "dreamy cinematic bloom around light sources"],
        {"弱": "Black Mist 1/8", "中": "Black Mist 1/4", "强": "Black Mist 1/4"},
    ),
    "白柔·Glimmerglass": (
        "{d} diffusion filter, subtle highlight glow",
        ["gentle skin softening", "slight sparkle around specular light", "romantic haze"],
        {"弱": "Glimmerglass 2", "中": "Glimmerglass 3", "强": "Glimmerglass 4"},
    ),
    "柔焦·Softar 朦胧": (
        "{d} soft-focus filter, dreamy veiled highlights",
        ["delicate skin glow", "painterly softness with retained core sharpness"],
        {"弱": "Softar I", "中": "Softar II", "强": "Softar III"},
    ),
    "星光镜·十字星芒": (
        "{d}, sparkling specular glints",
        ["glamour portrait sparkle", "star flares on light sources"],
        {"弱": "4-point star filter", "中": "6-point star filter", "强": "8-point star filter"},
    ),
}


def _full_filter_text(parts):
    core = parts[0]
    if len(parts) > 2:
        core = core.format(d=parts[2].get("强", ""))
    return ", ".join([core] + list(parts[1]))


CAMERA_FILTER_TEXT = {k: _full_filter_text(v) for k, v in CAMERA_FILTER_PARTS.items()}


def _camera_filter_text(choice, strength="强"):
    """强度只改变描述浓度，不改变所选滤镜本身。"""
    if not choice or choice in ("关闭", "无", "不启用"):
        return ""
    parts = CAMERA_FILTER_PARTS.get(choice)
    if not parts:
        return ""
    level = strength if strength in ("弱", "中", "强") else "强"
    core = parts[0]
    extras = list(parts[1]) if len(parts) > 1 else []
    if len(parts) > 2:
        core = core.format(d=parts[2].get(level, parts[2].get("中", "")))
    if level == "弱":
        return f"subtle {core}"
    if level == "中":
        return ", ".join([core] + extras[:2])
    return ", ".join([core] + extras)



def _outfit_pool_for(style, sub_theme="自动随机"):
    if sub_theme and sub_theme != "自动随机":
        if style == "古风" and sub_theme.startswith("古风·"):
            return SUB_THEME_POOL_MAP.get(sub_theme, OUTFITS_GUFENG_ALL)
        if style != "古风" and sub_theme.startswith("现代·"):
            return SUB_THEME_POOL_MAP.get(sub_theme, OUTFITS_MODERN_ALL)
    return OUTFITS_GUFENG_ALL if style in GUFENG_STYLES else OUTFITS_MODERN_ALL


def _filter_by_pref(pool, pref):
    if pref in ("室内", "室内日常"):
        sub = [s for s in pool if s[1] == "indoor"]
    elif pref in ("户外", "户外日常"):
        sub = [s for s in pool if s[1] == "outdoor"]
    else:
        sub = pool
    return sub or pool


def _outfit_for(style, idx, sub_theme="自动随机"):
    """使用伪随机哈希替代线性取模，避免相邻批次单品固定死循环。"""
    pool = _outfit_pool_for(style, sub_theme)
    r = random.Random((int(idx) * 2654435761 + 19937) % (2 ** 31))
    return r.choice(pool)


def _scene_for_style(style, pref, idx, sub_theme="自动随机"):
    pool = GUFENG_SCENES_ALL if style in GUFENG_STYLES else MODERN_SCENES_ALL
    pool = _filter_by_pref(pool, pref)
    if style not in GUFENG_STYLES and sub_theme in SUB_THEME_SCENE_HINTS:
        hints = SUB_THEME_SCENE_HINTS[sub_theme]
        soft = [s for s in pool if any(h in s[0].lower() for h in hints)]
        if len(soft) >= 3:
            pool = soft
    r = random.Random((int(idx) * 2246822519 + 857) % (2 ** 31))
    return r.choice(pool)


NUDE_GUARD = (
    "uncluttered natural surroundings, nothing but the landscape around her"
)
SWIM_HINTS = ("bikini", "swimsuit", "sarong", "cover-up", "beach shirt", "sun hat", "one-piece")
GOWN_HINTS = ("gown", "sequin", "fishtail", "tulle", "velvet")
PLAYFUL_HAIR_HINTS = ("twin high ponytails", "twin loop buns", "playful")


def _elegant_hair_fix(hair_text, outfit, idx, hair_style=None, outfit_style="现代"):
    if not hair_text:
        return hair_text
    o = (outfit or "").lower()
    if not any(h in o for h in GOWN_HINTS):
        return hair_text
    if not any(h in hair_text for h in PLAYFUL_HAIR_HINTS):
        return hair_text
    eff = _resolve_hair_style(hair_style, outfit_style)
    src = HAIR_STYLE_GUFENG if eff in GUFENG_STYLES else HAIR_STYLE_POOL
    pool = [h for h in src if not any(p in h for p in PLAYFUL_HAIR_HINTS)]
    if not pool:
        return hair_text
    r = random.Random((int(idx) * 2654435761 + 7919) % (2 ** 31))
    return r.choice(pool)


WATER_SCENES_OUTDOOR = [
    ("rocky seaside cove at golden hour with waves breaking below", "outdoor", "outdoor"),
    ("golden sand beach with gentle surf and warm afternoon light", "outdoor", "outdoor"),
    ("infinity pool deck overlooking the ocean at sunset", "outdoor", "outdoor"),
    ("lakeside wooden deck at dawn with still water and drifting mist", "outdoor", "outdoor"),
]
WATER_SCENES_INDOOR = [
    ("warm-lit spa pool room with steam and soft water reflections", "indoor", "bath"),
    ("indoor swimming pool at night with underwater lights", "indoor", "indoor_generic"),
]
GOWN_SCENES_INDOOR = [
    ("grand hotel lobby with marble floors and warm chandeliers", "indoor", "indoor_generic"),
    ("art gallery with white walls and soft spotlights", "indoor", "indoor_generic"),
    ("industrial loft studio with concrete walls and tall windows", "indoor", "indoor_generic"),
    ("small chapel with stained glass and pale wooden pews, soft window light", "indoor", "indoor_generic"),
]
GOWN_SCENES_OUTDOOR = [
    ("rooftop terrace with a city skyline at golden hour", "outdoor", "outdoor"),
    ("garden with white flowers and an arched trellis at golden hour", "outdoor", "outdoor"),
    ("european stone street with cafe terraces and warm afternoon light", "outdoor", "outdoor"),
]
# v66 新增：居家 / 雅致 / 校园 / 街头四组场景，专治「睡裙逛地铁」「旗袍进便利店」
HOME_SCENES_INDOOR = [
    ("sunlit bedroom with white sheets and sheer curtains, soft morning light", "indoor", "bed"),
    ("modern bedroom at night with warm bedside lamp and dark wood headboard", "indoor", "bed"),
    ("small apartment living room with a fabric sofa and afternoon light", "indoor", "indoor_generic"),
    ("warm-lit bathroom with steam on the mirror, soft shadows", "indoor", "bath"),
    ("bright photo studio with a white seamless backdrop and softbox light", "indoor", "indoor_generic"),
]
# 居家服装若被强制要求「户外」，只允许落在私密性说得通的半户外场景
HOME_SCENES_OUTDOOR = [
    ("balcony at dusk with city view and warm string lights", "outdoor", "outdoor"),
    ("courtyard with potted plants and soft afternoon light", "outdoor", "outdoor"),
    ("garden patio in the morning with plants and soft light", "outdoor", "outdoor"),
    ("riverside walkway at golden hour", "outdoor", "outdoor"),
]
ELEGANT_SCENES_INDOOR = [
    ("quiet tea room with warm light and a low table", "indoor", "kitchen"),
    ("grand hotel lobby with marble floors and warm chandeliers", "indoor", "indoor_generic"),
    ("art gallery with white walls and soft spotlights", "indoor", "indoor_generic"),
    ("vintage apartment with tall windows and wooden floor", "indoor", "bed"),
]
ELEGANT_SCENES_OUTDOOR = [
    ("courtyard with potted plants and soft afternoon light", "outdoor", "outdoor"),
    ("garden with white flowers and an arched trellis at golden hour", "outdoor", "outdoor"),
    ("european stone street with cafe terraces and warm afternoon light", "outdoor", "outdoor"),
]
SCHOOL_SCENES_INDOOR = [
    ("sunlit classroom with wooden desks and tall windows, warm afternoon light", "indoor", "indoor_generic"),
    ("library with tall shelves and warm reading lamps", "indoor", "indoor_generic"),
    ("bookstore aisle with warm lamps and tall shelves", "indoor", "indoor_generic"),
    ("cozy cafe by the window with a coffee cup, warm afternoon light", "indoor", "kitchen"),
]
SCHOOL_SCENES_OUTDOOR = [
    ("campus courtyard with old trees and stone steps, late afternoon light", "outdoor", "outdoor"),
    ("park bench in the afternoon with autumn leaves", "outdoor", "outdoor"),
]
URBAN_SCENES_INDOOR = [
    ("subway platform in the evening with motion blur", "indoor", "indoor_generic"),
    ("convenience store aisle at night under cool fluorescent light", "indoor", "indoor_generic"),
    ("industrial loft studio with concrete walls and tall windows", "indoor", "indoor_generic"),
]
URBAN_SCENES_OUTDOOR = [
    ("city street after rain with neon reflections at night", "outdoor", "outdoor"),
    ("industrial alley with concrete walls and faded graffiti, dusk light", "outdoor", "outdoor"),
    ("night market with warm lanterns and food stalls", "outdoor", "outdoor"),
]

WEDDING_HINTS = ("wedding", "bridal", "veil", "mermaid wedding", "pearl belt", "tulle gown")
HOME_HINTS = (
    "nightdress", "pajama", "sleepwear", "loungewear", "knit robe", "silk robe",
    "bathrobe", "robe tied loosely", "thin sheer robe", "camisole and shorts set",
)
QIPAO_HINTS = ("qipao", "cheongsam")
SCHOOL_HINTS = ("pleated skirt", "sailor-collar", "pinafore", "school",
                "knit vest over a white shirt")
TECHWEAR_HINTS = ("techwear", "shell jacket", "utility vest", "cargo pants",
                  "cargo trousers", "harness", "nylon jacket", "reflective piping",
                  "jumpsuit with zip")


def _scene_for_outfit(outfit, pref, idx, style=None):
    """服装 → 场景强关联：让每套衣服只落在说得通的场景里。"""
    if style in GUFENG_STYLES:
        return None
    o = (outfit or "").lower()
    indoor_pref = pref in ("室内", "室内日常")
    outdoor_pref = pref in ("户外", "户外日常")
    pool = None
    if any(h in o for h in SWIM_HINTS):
        pool = WATER_SCENES_INDOOR if indoor_pref else WATER_SCENES_OUTDOOR
    elif any(h in o for h in QIPAO_HINTS):
        pool = ELEGANT_SCENES_OUTDOOR if outdoor_pref else ELEGANT_SCENES_INDOOR
    elif any(h in o for h in WEDDING_HINTS) or any(h in o for h in GOWN_HINTS):
        pool = GOWN_SCENES_OUTDOOR if outdoor_pref else GOWN_SCENES_INDOOR
    elif any(h in o for h in HOME_HINTS):
        pool = HOME_SCENES_OUTDOOR if outdoor_pref else HOME_SCENES_INDOOR
    elif any(h in o for h in SCHOOL_HINTS):
        pool = SCHOOL_SCENES_OUTDOOR if outdoor_pref else SCHOOL_SCENES_INDOOR
    elif any(h in o for h in TECHWEAR_HINTS):
        pool = URBAN_SCENES_INDOOR if indoor_pref else URBAN_SCENES_OUTDOOR
    if not pool:
        return None
    r = random.Random((int(idx) * 2654435761 + 4493) % (2 ** 31))
    return r.choice(pool)


_SCENE_KIND_CACHE = {}
_SCENE_TAG_CACHE = {}

# --- v66 场景能力标签：场景里到底「有什么可用道具」 ---
# 姿势若引用场景中不存在的道具（床 / 浴缸 / 灶台 / 吧台 / 书架 ...），一律判为穿帮。
SCENE_TAG_RULES = (
    ("bed", ("bed", "bedroom", "headboard", "mattress", "sheets", "attic room", "daybed")),
    ("sofa", ("sofa", "couch", "living room")),
    ("bath", ("bathroom", "shower", "bathtub", "tub", "spa", "steam", "sauna", "washroom")),
    ("kitchen", ("kitchen", "stove", "oven", "refrigerator")),
    ("counter", ("kitchen", "counter", "cafe", "coffee", "bar", "tea room", "bakery", "diner")),
    ("sink", ("kitchen", "bathroom", "sink", "spa", "washroom")),
    ("stove", ("kitchen", "stove", "oven")),
    ("shelf", ("bookstore", "library", "shelf", "shelves", "supermarket",
               "convenience", "shop", "store", "pharmacy")),
    ("table", ("table", "desk", "office", "study", "classroom", "cafe",
               "coffee", "tea room", "dining", "conference")),
    ("chair", ("table", "desk", "office", "study", "classroom", "cafe",
               "coffee", "tea room", "kitchen", "dining")),
    ("bench", ("park", "garden", "patio", "courtyard", "plaza", "station",
               "lobby", "gallery", "terrace", "deck", "chapel", "steps")),
    ("window", ("window", "balcony", "loft", "apartment", "room", "studio", "skylight")),
    ("mirror", ("mirror", "gym", "studio", "bathroom", "dressing")),
    ("railing", ("balcony", "rooftop", "terrace", "deck", "dock", "pier",
                 "stair", "bridge", "railing")),
    ("water", ("beach", "lake", "pond", "sea", "pool", "cove", "river", "surf",
               "water", "dock", "shore", "spa", "waterfall")),
    ("nature_seat", ("rock", "boulder", "log", "stump", "driftwood", "outcrop", "desert",
                     "dune", "beach", "grassland", "meadow", "forest", "grove",
                     "clearing", "cove")),
    ("tree", ("forest", "grove", "park", "tree", "garden", "path", "clearing",
              "bamboo", "orchard", "plum")),
    ("lantern", ("lantern",)),
    ("outdoor_seat", ("low wall", "steps", "stair", "plaza", "bridge", "pier", "courtyard")),
)

# 姿势 → 它必须依赖的道具标签（多个时任一成立即可视为合理）
POSE_TAG_RULES = (
    (("on the bed", "edge of the bed", "onto the bed", "on the bed's", "headboard",
      "mattress", "sheet across", "in bed", "bed with"), "bed"),
    (("sofa", "couch"), "sofa"),
    (("bathtub", "shower", "tiles", "tiled", "tub", "steam", "sauna"), "bath"),
    (("sink",), "sink"),
    (("stove", "oven"), "stove"),
    (("countertop", "counter"), "counter"),
    (("shelf", "shelves", "book"), "shelf"),
    (("table", "desk"), "table"),
    (("chair", "stool"), "chair"),
    (("bench",), "bench"),
    (("windowsill",), "window"),
    (("mirror",), "mirror"),
    (("railing", "lamppost"), "railing"),
    (("low wall", "steps"), "outdoor_seat"),
    (("water's edge", "in the water", "surf", "shore", "waves"), "water"),
    (("tree", "branch"), "tree"),
    (("stone lantern",), "lantern"),
    (("rock", "boulder", "outcrop", "stump", "driftwood", "log"), "nature_seat"),
)


def _scene_tags(scene):
    """返回场景具备的道具能力集合（带缓存）。"""
    key = scene or ""
    cached = _SCENE_TAG_CACHE.get(key)
    if cached is not None:
        return cached
    s = key.lower()
    tags = set()
    for tag, hints in SCENE_TAG_RULES:
        if any(h in s for h in hints):
            tags.add(tag)
    kind = _scene_kind(key)
    if kind == "outdoor":
        tags.add("outdoor")
    else:
        tags.add("indoor")
        tags.add("window")
        # 古风室内场景默认具备木榻 / 案几 / 坐凳等古典陈设
        if _is_gufeng_scene(key):
            tags.update(("chair", "table", "bed", "shelf"))
    _SCENE_TAG_CACHE[key] = tags
    return tags


def _pose_tag_ok(pose, scene):
    """姿势引用的道具是否在场景中存在（防止书店里出现床、咖啡馆里出现浴缸）。"""
    p = (pose or "").lower()
    need = [tag for hints, tag in POSE_TAG_RULES if any(h in p for h in hints)]
    if not need:
        return True
    tags = _scene_tags(scene)
    return any(tag in tags for tag in need)


def _scene_kind(text):
    key = text or ""
    if key in _SCENE_KIND_CACHE:
        return _SCENE_KIND_CACHE[key]
    kind = "outdoor"
    for pool in (
        MODERN_SCENES_ALL, GUFENG_SCENES_ALL, SCENES, NUDE_SCENES,
        NIGHT_SCENES, WATER_SCENES_INDOOR, WATER_SCENES_OUTDOOR,
        GOWN_SCENES_INDOOR, GOWN_SCENES_OUTDOOR, HOME_SCENES_INDOOR,
        HOME_SCENES_OUTDOOR, ELEGANT_SCENES_INDOOR, ELEGANT_SCENES_OUTDOOR,
        SCHOOL_SCENES_INDOOR, SCHOOL_SCENES_OUTDOOR, URBAN_SCENES_INDOOR,
        URBAN_SCENES_OUTDOOR
    ):
        for s in pool:
            if s[0] == text:
                kind = s[1]
                _SCENE_KIND_CACHE[key] = kind
                return kind
    _SCENE_KIND_CACHE[key] = kind
    return kind


ARTIFICIAL_OUTDOOR_HINTS = (
    "balcony", "rooftop", "street after rain", "campsite",
    "seaside highway", "desert highway", "city lights", "string lights",
    "street", "market", "alley", "plaza", "sidewalk", "station",
    "crossing", "bridge", "terrace"
)


def _nude_scene_fix(scene, clothed, idx, style=None):
    if clothed:
        return scene
    if _scene_kind(scene) != "outdoor":
        return scene
    if not any(h in scene for h in ARTIFICIAL_OUTDOOR_HINTS):
        return scene
    src = GUFENG_SCENES_ALL if style in GUFENG_STYLES else MODERN_SCENES_ALL
    pool = [s[0] for s in src if s[1] == "outdoor" and _is_natural_outdoor(s[0])]
    if not pool:
        pool = [
            s[0] for s in src
            if s[1] == "outdoor" and not any(h in s[0] for h in ARTIFICIAL_OUTDOOR_HINTS)
        ]
    if not pool:
        return scene
    r = random.Random((int(idx) * 2654435761 + 6151) % (2 ** 31))
    return r.choice(pool)


REVEAL_CHOICES = ["关闭", "微露", "适中"]
REVEAL_TEXT = {
    "微露": "collarbones visible, relaxed open collar, a hint of upper chest",
    "适中": "collarbones and upper chest softly revealed, relaxed open collar, a subtle glimpse of cleavage",
}


def _reveal_text(choice, neckline_choice=None, clothed=True):
    if not clothed or choice in (None, "", "关闭"):
        return ""
    if neckline_choice in ("高领", "圆领"):
        return ""
    return REVEAL_TEXT.get(choice, "")


OCCLUDING_OUTFIT_HINTS = (
    "apron", "towel", "bathrobe", "knit robe", "hoodie", "pajama",
    "sweatshirt", "trench coat", "puffer"
)
OPEN_GARMENT_HINTS = (
    "off-shoulder", "off shoulder", "strapless", "halter", "backless",
    "bandeau", "tube top", "one-shoulder", "deep v", "deep-v", "plunge",
    "cowl", "sweetheart", "cut-out", "open back", "sheer", "bralette",
    "camisole", "slip dress", "slip gown", "slip skirt", "bikini",
    "swimsuit", "nightdress", "scoop neck", "sports bra", "corset", "crop top"
)
HIGH_NECK_HINTS = (
    "turtleneck", "high collar", "standing-collar", "standing collar",
    "mock neck", "crew neck", "high-neck", "high neck"
)
OCCLUDING_ANGLE_HINTS = (
    "from behind", "back view", "side view", "profile silhouette",
    "over-the-shoulder view", "over-the-shoulder glance"
)
TURN_AWAY_HINTS = (
    "turning from the stove", "looking back over her shoulder",
    "from behind", "over her shoulder", "reach a shelf", "reaching up",
    "bending forward", "leaning over", "arms above her head", "arms crossed"
)


def _effective_neckline(neckline, reveal):
    if reveal in (None, "", "关闭"):
        return neckline
    if neckline in ("高领", "圆领"):
        return "跟随服装"
    return neckline


def _chest_visible(bust_text, neckline_text, neckline_choice, occluded=False, reveal_on=False):
    if occluded:
        return False
    if neckline_choice in ("高领", "圆领"):
        return False
    if reveal_on:
        return True
    if bust_text and bust_text != BUST_NEUTRAL_CLOTHED:
        return True
    if neckline_choice in ("低领", "深V"):
        return True
    return bool(neckline_text) and "cleavage" in neckline_text


def _visible_angles(pool):
    keep = [a for a in pool if not any(h in a for h in OCCLUDING_ANGLE_HINTS)]
    return keep or pool


def _visible_pose(pool, idx):
    fronts = [p for p in pool if p[1] and not any(h in p[0] for h in TURN_AWAY_HINTS)]
    if not fronts:
        fronts = [p for p in pool if p[1]]
    if not fronts:
        return None
    return fronts[int(idx) % len(fronts)]


def _outfit_occludes(outfit):
    o = (outfit or "").lower()
    return any(h in o for h in OCCLUDING_OUTFIT_HINTS)


def _chest_blocked(outfit):
    """高领 / 立领 / 圆领毛衣等遮住胸口的单品，不允许再写「胸口敞开、胸型透出」。"""
    o = (outfit or "").lower()
    return _outfit_occludes(o) or any(h in o for h in HIGH_NECK_HINTS)


def _fit_outfit(outfit, style, neckline, cup_on, idx, sub_theme="自动随机", open_chest=False):
    pool = _outfit_pool_for(style, sub_theme)
    need_closed = neckline in ("高领", "圆领")
    need_open = neckline in ("低领", "深V") or bool(open_chest)
    avoid_occl = bool(cup_on) or need_open

    def _ok(x):
        xl = x.lower()
        if need_closed and any(h in xl for h in OPEN_GARMENT_HINTS):
            return False
        if need_open and any(h in xl for h in HIGH_NECK_HINTS):
            return False
        if avoid_occl and any(h in xl for h in OCCLUDING_OUTFIT_HINTS):
            return False
        return True

    if _ok(outfit):
        return outfit
    cands = [o for o in pool if _ok(o)]
    if not cands:
        def _ok2(x):
            xl = x.lower()
            if need_closed and any(h in xl for h in OPEN_GARMENT_HINTS):
                return False
            if need_open and any(h in xl for h in HIGH_NECK_HINTS):
                return False
            return True
        cands = [o for o in pool if _ok2(o)]
    if not cands:
        return outfit
    return cands[int(idx) % len(cands)]


def _neckline_text(choice, outfit, style="现代"):
    if choice in (None, ""):
        return ""
    if choice == "跟随服装":
        low = any(h in (outfit or "").lower() for h in LOWCUT_HINTS + LURE_LOWCUT_HINTS)
        return "low neckline, subtle natural cleavage" if low else ""
    # 古风下自动转换领型描述，避免现代一字肩/圆领毛衣词汇污染汉服
    if style in GUFENG_STYLES:
        gufeng_map = {
            "高领": "standing collar, high buttoned collar, chest fully covered",
            "圆领": "traditional round collar robe, chest fully covered",
            "低领": "low cross-collar hanfu, subtle natural cleavage",
            "深V": "deep plunging cross-collar, subtle natural cleavage, the collar frames her chest",
            "一字肩": "chest-high ruqun style, bare shoulders and collarbones visible",
        }
        return gufeng_map.get(choice, NECKLINE_TEXT.get(choice, ""))
    return NECKLINE_TEXT.get(choice, "")


PUBIC = [
    "natural dark pubic hair, softly trimmed",
    "natural untrimmed pubic hair",
    "neatly trimmed pubic hair, natural dark hair",
]

POSES = [
    ("standing by the window, looking outside", True),
    ("sitting on the sofa with her legs crossed", True),
    ("sitting on the edge of the bed, leaning back on her hands", True),
    ("lying on her stomach on the bed, propped on her elbows", False),
    ("lying on her back on the bed, arms above her head", True),
    ("kneeling on the bed, sitting back on her heels", True),
    ("standing in front of the mirror, brushing her hair", True),
    ("sitting at the kitchen counter, holding a cup", True),
    ("leaning against the wall with one knee bent", True),
    ("sitting on the floor with her back against the sofa", True),
    ("stretching her arms above her head after waking up", True),
    ("standing in the shower, water running over her skin", True),
    ("sitting on a chair with one knee pulled up", True),
    ("standing on tiptoe to reach a shelf", True),
    ("lying on the sofa with one leg bent", True),
    ("standing with her hands behind her back", True),
    ("sitting cross-legged on the bed", True),
    ("leaning on the balcony railing, looking at the city", False),
    ("walking toward the camera", True),
    ("kneeling by the window, looking out", True),
    ("sitting on the windowsill", True),
    ("lying on her side on the bed, head on her hand", False),
    ("standing with her arms crossed under her chest", True),
    ("sitting on a stool with her elbows on her knees", True),
    ("bending forward to pick something up", False),
    ("standing under a tree, looking up", True),
    ("sitting on a park bench", True),
    ("standing at the kitchen sink", False),
    ("lying on the floor with her knees up", True),
    ("standing with one hand in her hair", True),
]

_POSE_BED_EXTRA = [
    ("lying on the bed with one knee raised, sheet across her thigh", True),
    ("sitting on the bed with her back against the headboard, legs stretched out", True),
    ("kneeling on the bed and arching her back, looking over her shoulder", False),
    ("lying on her back at the edge of the bed with her legs hanging off", True),
]

_POSE_BATH_EXTRA = [
    ("standing in the bathtub, water up to her thighs", True),
    ("sitting on the edge of the bathtub with one leg inside", True),
    ("wrapping a towel around her hair, standing at the sink", True),
    ("stepping out of the shower with wet skin", True),
    ("leaning over the sink, looking into the mirror", False),
    ("standing under the shower with her head tilted back", True),
    ("sitting on the bathroom floor with her back against the tiles", True),
    ("standing with one foot on the edge of the tub, drying her calf", True),
    ("leaning against the tiled wall with her head tilted back", True),
    ("sitting on a stool in the shower, water running down her back", False),
]

_POSE_KITCHEN_EXTRA = [
    ("leaning against the counter with a cup in both hands", True),
    ("sitting on the countertop with her legs dangling", True),
    ("standing by the window holding a warm mug", True),
    ("reaching up to a shelf with her back arched", False),
    ("sitting at the table with her chin on her hand", True),
    ("turning from the stove to look at the camera", True),
    ("kneeling on a chair to reach the top shelf", False),
    ("leaning on the door frame with a cup in her hand", True),
]

_POSE_OUTDOOR_EXTRA = [
    ("standing at the railing with the wind in her hair", False),
    ("sitting on a low wall with her legs crossed", True),
    ("leaning against a lamppost, one hand on the post", True),
    ("standing at the water's edge with her feet in the water", True),
    ("sitting on the sand with her knees drawn up", True),
    ("walking along the path, looking back over her shoulder", False),
    ("standing with her arms open, face tilted to the sun", True),
    ("sitting on the steps with her elbows on her knees", True),
    ("leaning on a railing with her back to the view", True),
]

_POSE_INDOOR_EXTRA = [
    ("sitting on the arm of the sofa, one leg swinging", True),
    ("standing between the shelves, pulling out a book", True),
    ("sitting on the floor with her back against the wall, knees up", True),
    ("leaning over a table with both hands on it", False),
]

POSE_GROUPS = {
    "bed": [POSES[2], POSES[3], POSES[4], POSES[5], POSES[10], POSES[16],
            POSES[19], POSES[21], POSES[28], POSES[29]] + _POSE_BED_EXTRA,
    "bath": [POSES[6], POSES[8], POSES[24]] + _POSE_BATH_EXTRA,
    "kitchen": [POSES[7], POSES[12], POSES[13], POSES[15], POSES[23], POSES[27]] + _POSE_KITCHEN_EXTRA,
    "outdoor": [POSES[17], POSES[18], POSES[24], POSES[25], POSES[26]] + _POSE_OUTDOOR_EXTRA,
    "indoor_generic": [POSES[1], POSES[6], POSES[8], POSES[9], POSES[12], POSES[14],
                       POSES[15], POSES[19], POSES[22], POSES[23], POSES[29]] + _POSE_INDOOR_EXTRA,
}

POSE_PROP_RULES = (
    (("on the bed", "edge of the bed", "onto the bed", "on the bed's", "headboard", "mattress", "sheet across"), {"bed"}),
    (("sofa", "couch"), {"bed", "indoor_generic"}),
    (("bathtub", "shower", "tiles", "tub"), {"bath"}),
    (("sink",), {"bath", "kitchen"}),
    (("countertop", "counter", "shelf", "shelves", "table", "desk", "windowsill", "chair", "stool", "door frame"),
     {"bed", "kitchen", "indoor_generic"}),
)

NATURAL_OUTDOOR_HINTS = (
    "snow", "plum", "bamboo", "grassland", "forest", "grove",
    "mountain", "peak", "desert", "dune", "beach", "cove",
    "lakeside", "lake", "pond", "campsite", "river", "sea",
    "cliff", "meadow", "clearing", "mist", "wilderness",
    "ranch", "field", "pavilion"
)
URBAN_OUTDOOR_HINTS = (
    "street", "city", "rooftop", "terrace", "plaza", "night market",
    "highway", "sidewalk", "neon", "balcony", "station", "crossing", "alley"
)
SEATED_POSE_HINTS = (
    "sitting", "seated", "lying", "reclining", "kneeling",
    "cross-legged", "knees drawn up", "knees up", "on her back",
    "on her stomach", "on her side", "leaning on", "leaning against",
    "against the wall", "against the tiles", "on the floor",
    "windowsill", "window", "mirror", "countertop", "counter",
    "bench", "steps", "low wall", "railing", "lamppost", "stool",
    "chair", "table", "shelf", "shelves", "headboard", "pillow",
    "blanket", "stove", "sink", "tub", "bathtub", "shower", "tiles"
)
NATURAL_GROUND_RULES = (
    (("snow", "plum", "frost"), "snow-covered ground underfoot, snow at the edge of the frame"),
    (("wooden deck", "deck", "dock", "pier"), "weathered deck boards underfoot"),
    (("bamboo", "forest", "grove", "clearing", "wilderness"), "forest floor underfoot, moss and fallen leaves"),
    (("grassland", "meadow", "ranch", "field", "prairie"), "open grassland underfoot, grass brushing her legs"),
    (("mountain", "peak", "cliff", "rocky"), "rocky mountain ground underfoot, loose stone"),
    (("desert", "dune", "sand"), "fine sand underfoot"),
    (("beach", "cove", "sea", "surf"), "wet sand underfoot at the water's edge"),
    (("lake", "pond", "lakeside", "river"), "firm ground underfoot at the shore"),
)
LONG_GARMENT_HINTS = (
    "hanfu", "robe", "ruqun", "qipao", "beizi", "gown", "skirt",
    "wide-sleeve", "wide-sleeved", "dress"
)
GOWN_SEATED_BAN = (
    "cross-legged", "kneeling", "on her heels", "knees drawn up",
    "knees up", "sitting on the floor", "on the floor with her knees",
    "sitting on the ground", "sitting on the sand", "crouching", "lying on the floor"
)
GOWN_SKIRT_GUARD = (
    "the long skirt gathered in her lap, the hem falling straight down"
)

_POSE_GOWN_FURNITURE = [
    ("sitting on the edge of the bed, leaning back on her hands", True),
    ("sitting on a chair with one knee pulled up", True),
    ("sitting on a stool with her elbows on her knees", True),
    ("sitting on the windowsill", True),
    ("sitting on a park bench", True),
    ("sitting on the sofa with her legs crossed", True),
    ("sitting on a low wall with her legs crossed", True),
    ("sitting at the table with her chin on her hand", True),
    ("lying on her side on the bed, head on her hand", True),
    ("lying on her back on the bed, arms above her head", True),
]


def _pose_rotate(pool, idx, salt=0):
    n = len(pool)
    if n <= 0:
        return None
    if n == 1:
        return pool[0]

    def _gcd(a, b):
        while b:
            a, b = b, a % b
        return a

    step = 1
    for cand in (7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47):
        if _gcd(cand, n) == 1:
            step = cand
            break
    h = (int(idx) * 2654435761 + int(salt) * 40503 + 104729) % (2 ** 31)
    return pool[(int(idx) * step + h) % n]


_POSE_NATURE_EXTRA = [
    ("standing in the tall grass with her sleeves moving in the wind", True),
    ("walking slowly through the snow, one hand gathering her sleeve", True),
    ("standing still with her chin lifted, snow falling around her", True),
    ("pausing on the path with one hand resting on a branch", True),
    ("standing with her arms folded inside her wide sleeves", True),
    ("turning to look back along the path", True),
    ("standing beside a stone lantern with one hand on the snow-dusted stone", True),
    ("standing at the edge of the clearing, gazing into the distance", True),
    ("walking away down the path, glancing back over her shoulder", False),
    ("standing with her hands clasped in front of her, eyes lowered", True),
]

_POSE_NATURE_SEAT = [
    ("sitting on a large flat rock, both feet on the rock in front of her, knees together", True),
    ("sitting on a fallen log, both feet on the ground in front of her, hands resting on her knees", True),
    ("sitting on a mossy boulder at the water's edge, legs hanging down the side, feet together", True),
    ("sitting on a smooth rock, both feet on the ground in front of her, hands on her knees", True),
    ("resting on a rock outcrop, sitting upright with both feet on the stone, knees together", True),
    ("sitting on a driftwood log on the sand, both feet resting on the sand in front of her", True),
    ("sitting on a tree stump at the edge of the clearing, both feet on the ground, knees together", True),
    ("sitting on a wide flat boulder half sunk in the grass, both feet on the stone, knees together", True),
    ("sitting on a low rock shelf above the water, both feet on the rock in front of her", True),
    ("sitting on a weathered stump at the treeline, both feet flat on the ground, hands folded in her lap", True),
]

NATURAL_SEAT_HINTS = ("rock", "boulder", "log", "stump", "driftwood", "outcrop")


def _pose_on_natural_seat(pose):
    p = (pose or "").lower()
    return any(h in p for h in NATURAL_SEAT_HINTS)


def _natural_seat_anchor(pose, outfit=None, scene=None):
    """只补「坐的是什么」，不重复姿势里已经写过的脚位与地面，避免同一句说三遍。"""
    p = (pose or "").lower()
    seat = None
    if "driftwood" in p or "log" in p:
        seat = "the weathered driftwood log beneath her"
    elif "stump" in p:
        seat = "the bare tree stump beneath her"
    elif any(h in p for h in ("rock", "boulder", "outcrop")):
        seat = "the bare rock beneath her"
    if seat is None:
        return None
    s = (scene or "").lower()
    if any(h in s for h in ("snow", "frost", "plum", "winter")):
        seat = f"{seat}, snow dusting the stone"
    o = (outfit or "").lower()
    if any(h in o for h in LONG_GARMENT_HINTS):
        return f"{seat}, the long skirt falling straight down over her legs"
    return seat


GUFENG_MODERN_PROP_HINTS = (
    "sofa", "couch", "windowsill", "window", "park bench",
    "countertop", "counter", "bathtub", "shower", "tiles", "desk", "mirror", "office"
)

GUFENG_SEAT_INDOOR = [
    ("sitting on a carved wooden daybed, legs folded to one side, both feet together on the daybed", True),
    ("sitting on a cushioned wooden platform, legs folded to one side, one hand on a small tea table", True),
    ("sitting on a wooden stool beside a tea table, back straight, both feet flat on the floor", True),
    ("sitting sideways on a wooden bench, both legs together and hanging down, feet on the floor", True),
    ("sitting on the edge of a wooden daybed in the study, both feet on the floor, scrolls nearby", True),
    ("leaning against a red lacquered pillar, one leg straight and the other slightly bent, both feet on the floor", True),
]


def _is_gufeng_scene(scene):
    s = scene or ""
    for item in GUFENG_SCENES_ALL:
        if item[0] == s:
            return True
    return False


_POSE_STAND_ANY = [
    ("standing still, facing the camera", True),
    ("standing with her hands clasped in front of her", True),
    ("turning slightly with one hand lifting her sleeve", True),
    ("standing with her sleeves hanging, calm upright posture", True),
    ("walking toward the camera", True),
    ("walking past the frame, glancing at the camera", True),
    ("standing with her back to the camera, glancing over her shoulder", True),
    ("standing with one hand resting at her waist, chin lifted", True),
    ("standing with her arms loose at her sides, weight on one leg", True),
    ("standing in profile, turning her head toward the camera", True),
    ("stepping forward with her sleeves trailing behind her", True),
    ("standing with both hands gathering her long sleeves", True),
    ("standing with one hand raised to her hairpin", True),
    ("standing with her hands behind her back, looking down", True),
    ("standing at an angle, one shoulder toward the camera", True),
    ("walking down a few steps with one hand on the rail", True),
    ("standing with her arms folded, sleeves overlapping", True),
    ("standing with one hand at her collar", True),
    ("standing with her hair and sleeves lifted by the wind", True),
    ("standing with her hands clasped behind her, chin raised", True),
]


def _is_natural_outdoor(scene):
    if _scene_kind(scene) != "outdoor":
        return False
    s = (scene or "").lower()
    if any(h in s for h in URBAN_OUTDOOR_HINTS):
        return False
    return any(h in s for h in NATURAL_OUTDOOR_HINTS)


def _natural_ground_text(scene):
    """只输出一条与场景匹配的地面描述，不再叠加泛泛的 bare ground。"""
    s = (scene or "").lower()
    for hints, text in NATURAL_GROUND_RULES:
        if any(h in s for h in hints):
            return text
    return "bare ground beneath her"


def _pose_needs_furniture(pose):
    p = (pose or "").lower()
    return any(h in p for h in SEATED_POSE_HINTS)


def _pose_garment_ok(pose, outfit):
    o = (outfit or "").lower()
    if not any(h in o for h in LONG_GARMENT_HINTS):
        return True
    p = (pose or "").lower()
    return not any(h in p for h in GOWN_SEATED_BAN)


def _gown_on_nature_ban(pose, scene, outfit):
    if scene is None:
        return False
    if not _is_natural_outdoor(scene):
        return False
    o = (outfit or "").lower()
    if not any(h in o for h in LONG_GARMENT_HINTS):
        return False
    return _pose_needs_furniture(pose)


def _pose_props_ok(pose, group, scene=None):
    p = (pose or "").lower()
    if scene is not None and not _pose_tag_ok(pose, scene):
        return False
    # 带雪的姿势只能出现在雪景里（否则「湖畔木台边一场雪」）
    if scene is not None and "snow" in p:
        s = scene.lower()
        if not any(h in s for h in ("snow", "frost", "plum", "winter", "glacier")):
            return False
    for hints, groups in POSE_PROP_RULES:
        if any(h in p for h in hints) and group not in groups:
            return False
    if scene is not None and _is_natural_outdoor(scene) and _pose_needs_furniture(pose):
        if not _pose_on_natural_seat(pose):
            return False
    if scene is not None and _is_gufeng_scene(scene):
        if any(h in p for h in GUFENG_MODERN_PROP_HINTS):
            return False
    return True


def _pose_pool_for(group, scene=None):
    pool = list(POSE_GROUPS.get(group, POSES))
    if scene is not None and _is_natural_outdoor(scene):
        pool = pool + _POSE_NATURE_EXTRA + _POSE_NATURE_SEAT
    elif scene is not None and _is_gufeng_scene(scene) and _scene_kind(scene) == "indoor":
        pool = pool + GUFENG_SEAT_INDOOR
    return [x for x in pool if _pose_props_ok(x[0], group, scene)]


def _compliant_pool(group, scene=None, outfit=None, front_only=False):
    pool = [
        x for x in _pose_pool_for(group, scene)
        if _pose_garment_ok(x[0], outfit) and not _gown_on_nature_ban(x[0], scene, outfit)
    ]
    if front_only:
        fronts = [x for x in pool if x[1]]
        if fronts:
            pool = fronts
    if len(pool) < 4:
        seen = set(x[0] for x in pool)
        for x in _POSE_STAND_ANY + _POSE_GOWN_FURNITURE:
            if x[0] in seen:
                continue
            if not _pose_props_ok(x[0], group, scene):
                continue
            if not _pose_garment_ok(x[0], outfit):
                continue
            if _gown_on_nature_ban(x[0], scene, outfit):
                continue
            pool.append(x)
            seen.add(x[0])
    return pool


def _pose_from_pool(group, scene=None, outfit=None, idx=0, exclude=None, front_only=False, salt=0):
    pool = _compliant_pool(group, scene, outfit, front_only)
    if exclude:
        fresh = [x for x in pool if x[0] not in exclude]
        if fresh:
            pool = fresh
    if not pool:
        return None
    return _pose_rotate(pool, idx, len(group) * 131 + len(scene or "") + int(salt) * 7919)


def _pose_scene_fix(pose, front, group, idx, scene=None, outfit=None, exclude=None, front_only=False):
    ok = (
        _pose_props_ok(pose, group, scene)
        and _pose_garment_ok(pose, outfit)
        and not _gown_on_nature_ban(pose, scene, outfit)
    )
    if ok and not (exclude and pose in exclude):
        return pose, front
    pool = _compliant_pool(group, scene, outfit, front_only)
    if exclude:
        fresh = [x for x in pool if x[0] not in exclude]
        if fresh:
            pool = fresh
    if not pool:
        return pose, front
    picked = _pose_rotate(pool, idx, len(group) * 131 + len(scene or ""))
    return picked if picked else (pose, front)


def _scene_group(text):
    for pool in (
        SCENES, MODERN_SCENES_ALL, GUFENG_SCENES_ALL, NUDE_SCENES,
        NIGHT_SCENES, WATER_SCENES_INDOOR, WATER_SCENES_OUTDOOR,
        GOWN_SCENES_INDOOR, GOWN_SCENES_OUTDOOR, HOME_SCENES_INDOOR,
        HOME_SCENES_OUTDOOR, ELEGANT_SCENES_INDOOR, ELEGANT_SCENES_OUTDOOR,
        SCHOOL_SCENES_INDOOR, SCHOOL_SCENES_OUTDOOR, URBAN_SCENES_INDOOR,
        URBAN_SCENES_OUTDOOR
    ):
        for s in pool:
            if s[0] == text:
                return s[2]
    return "indoor_generic"


# --- 方案 A：五档摄影师套系命名（向下兼容旧版 4 个模式名称）---
MODES = ["盲盒抽卡", "模特换装", "旅拍转场", "写真套图", "定点连拍"]
LEGACY_MODE_MAP = {
    "完全随机": "盲盒抽卡",
    "同人不同姿势": "模特换装",
    "同场景不同姿势": "写真套图",
    "锁场景锁人只变姿势": "定点连拍",
}


def _norm_mode(mode):
    return LEGACY_MODE_MAP.get(mode, mode if mode in MODES else "写真套图")


def _pick_scene(rng, pref):
    if pref in ("室内", "室内日常"):
        pool = [s for s in SCENES if s[1] == "indoor"]
    elif pref in ("户外", "户外日常"):
        pool = [s for s in SCENES if s[1] == "outdoor"]
    else:
        pool = SCENES
    return rng.choice(pool)


def _vulva_visible(pose_front, shot):
    return pose_front and ("medium shot" not in shot)


def _normalize_shot(shot, beauty_angles):
    if beauty_angles and "camera slightly below eye level" in shot:
        return "medium full shot, from mid-thigh up"
    return shot


# --- 摄影大师智能镜头与光线匹配引擎 ---
NIGHT_LIGHT_HINTS = (
    "night", "midnight", "dusk", "blue hour", "neon", "candlelight",
    "lantern", "bedside lamp", "floor lamp", "fluorescent", "evening", "underwater lights"
)


def _smart_camera_and_light(shot, scene, lighting="跟随场景"):
    s_low = (shot or "").lower()
    sc_low = (scene or "").lower()

    # 1. 根据景别智能匹配焦段（彻底解决 85mm 拍大远景/狭窄室内全身的物理畸变冲突）
    if "wide shot" in s_low:
        lens = "35mm lens, environmental portrait, deep spatial perspective"
    elif "medium shot" in s_low:
        lens = "85mm f/1.4 portrait lens, shallow depth of field, creamy bokeh"
    elif "cowboy" in s_low or "mid-thigh" in s_low:
        lens = "50mm f/1.4 lens, natural human-eye perspective"
    else:
        lens = "50mm lens, full-length proportion accuracy"

    # 2. 匹配光线：夜景不再硬塞「soft natural light」，用户强制光效时也不与场景时段打架
    is_night = any(h in sc_low for h in NIGHT_LIGHT_HINTS)
    is_golden = any(h in sc_low for h in ("sunset", "golden hour", "dawn", "sunrise"))
    if lighting and lighting != "跟随场景" and lighting in LIGHTING_TEXT:
        light = LIGHTING_TEXT[lighting]
        if lighting == "自然柔光" and is_night:
            # 夜景 + 自然柔光 = 自相矛盾，降级为可控的柔光夜景
            light = "soft diffused practical light, clean tonal gradation, gentle shadow falloff"
        elif lighting == "落日逆光" and is_night:
            light = "warm practical backlight, glowing rim light on hair, soft ambient glow"
        elif lighting == "霓虹夜景" and not is_night and not any(h in sc_low for h in URBAN_OUTDOOR_HINTS):
            # 白天/室内场景选霓虹：改用彩色灯光语汇，避免「白天出现霓虹夜景」
            light = "colorful gel lighting, cyan and magenta rim reflections, moody saturated atmosphere"
    elif is_night:
        light = "cinematic ambient lighting, delicate shadow play, rich atmospheric contrast"
    elif is_golden:
        light = "warm golden hour sunlight, soft directional glow"
    else:
        light = "soft natural light, clean tonal gradation"

    return f"{lens}, {light}"


def _render(
    scene, person, pose, front, shot, angle, outfit, clothed, extra="",
    bust_text=None, neckline_text=None, reveal_text=None, hair_text=None,
    hair_color_text=None, nude_guard=False, ground_text=None,
    chest_frame=True, lighting="跟随场景", mood="自然随机", cam_filter="关闭",
    cam_filter_strength="强"
):
    face, hair, skin, body, bust, pubic = person
    if mood and mood != "自然随机" and mood in MOOD_TEXT:
        mtxt = MOOD_TEXT[mood]
        # 背身/侧背机位写「直视镜头」自相矛盾，改写为回头视线
        if (not front) and mood == "直视互动":
            mtxt = "glancing back toward the lens over her shoulder, subtle intimate expression"
        face = f"{face}, {mtxt}"
    if hair_text:
        hair = hair_text
    if hair_color_text:
        hair = f"{hair}, {hair_color_text}"
    if bust_text:
        bust = bust_text
    # 领口与露肤度同时写 cleavage 属于重复语义，保留信息更具体的领口描述
    if reveal_text and neckline_text and "cleavage" in reveal_text and "cleavage" in neckline_text:
        reveal_text = ""

    cam_light = _smart_camera_and_light(shot, scene, lighting)
    tail = f"realistic skin texture, natural body proportions, correct anatomy, {cam_light}"
    filter_text = _camera_filter_text(cam_filter, cam_filter_strength)
    if filter_text:
        tail = f"{tail}, {filter_text}"
    if extra:
        tail = f"{tail}, {extra}"

    # 主体与服装前置：权重靠前，避免「衣服/场景」被后置长尾稀释
    head = (
        f"photorealistic, {shot}, {angle}, beautiful young Asian woman, "
        f"{face}, {hair}, {skin}"
    )

    if clothed:
        look = f"wearing {outfit}, the clothing follows her body shape"
        if bust_text and bust_text != BUST_NEUTRAL_CLOTHED and chest_frame:
            look = (
                f"{look}, bust contour readable through the fabric, "
                "chest framed toward the camera"
            )
        if neckline_text:
            look = f"{look}, {neckline_text}"
        if reveal_text:
            look = f"{look}, {reveal_text}"
        if _pose_needs_furniture(pose) and any(h in (outfit or "").lower() for h in LONG_GARMENT_HINTS):
            look = f"{look}, {GOWN_SKIRT_GUARD}"
        core = f"{head}, {look}, {body}"
        if bust:
            core = f"{core}, {bust}"
        core = f"{core}, {scene}, {pose}"
        if ground_text:
            core = f"{core}, {ground_text}"
        return f"{core}, {tail}"

    nude_bits = "nude, fully nude, bare skin"
    if front:
        # 正面机位显式写出乳头与乳晕：词库原本完全没提，模型会自行「打码」或抹平
        nude_bits += ", visible nipples, natural areola tone"
    if _vulva_visible(front, shot):
        nude_bits += f", visible vulva, {pubic}"
    if nude_guard:
        nude_bits += f", {NUDE_GUARD}"
    core = f"{head}, {nude_bits}, {body}"
    if bust:
        core = f"{core}, {bust}"
    core = f"{core}, {scene}, {pose}"
    if ground_text:
        core = f"{core}, {ground_text}"
    return f"{core}, {tail}"


def _line_rng(seed, i):
    return random.Random((int(seed) * 2654435761 + int(i) * 7919 + 104729) % (2 ** 31))


def build_pair(
    idx, seed=0, scene_pref="不限", person_override=None,
    height_override=None, bust_text=None, bust_nude_text=None,
    neckline_choice=None, beauty_angles=False,
    reveal_text=None, hair_text=None, outfit_style=None,
    hair_color_text=None, pose_exclude=None, shot_override=None,
    hair_style=None, sub_theme="自动随机", lighting="跟随场景", mood="自然随机",
    cam_filter="关闭", cam_filter_strength="强", want="clothed"
):
    rng = random.Random((int(idx) * 2654435761) % (2 ** 31))
    scene, kind, group, outfits = _pick_scene(rng, scene_pref)
    shot = rng.choice(SHOTS)
    if shot_override:
        shot = shot_override
    pose, front = rng.choice(POSES)
    shot = _normalize_shot(shot, beauty_angles)
    if beauty_angles:
        angles = FRONT_ANGLES_BEAUTY if front else BACK_ANGLES_BEAUTY
    else:
        angles = FRONT_ANGLES if front else BACK_ANGLES
    angle = rng.choice(angles)
    face = rng.choice(FACES)
    hair = rng.choice(HAIRS)
    skin = rng.choice(SKINS)
    body = rng.choice(BODIES)
    bust = rng.choice(BREASTS)
    outfit = rng.choice(outfits)
    pubic = rng.choice(PUBIC)

    if outfit_style:
        lure = _outfit_for(outfit_style, idx, sub_theme)
        if lure:
            outfit = lure
            outfit = _fit_outfit(
                outfit, outfit_style, neckline_choice,
                bool(bust_text and bust_text != BUST_NEUTRAL_CLOTHED), idx, sub_theme,
                open_chest=bool(reveal_text)
            )
            _sc, _kd, _gp = _scene_for_style(outfit_style, scene_pref, idx, sub_theme)
            scene, group = _sc, _gp
            _so = _scene_for_outfit(outfit, scene_pref, idx, outfit_style)
            if _so:
                scene, group = _so[0], _so[2]

    neck = _neckline_text(neckline_choice, outfit, outfit_style or "现代")
    chest_on = _chest_visible(
        bust_text, neck, neckline_choice,
        _chest_blocked(outfit), reveal_on=bool(reveal_text)
    )

    # 无衣版可能被换到另一处自然场景，姿势必须针对「真正会被渲染的那个场景」校验，
    # 否则会出现「草原上坐在公园长椅上」这类穿帮。
    _nude_sc = _nude_scene_fix(scene, False, idx, outfit_style) if outfit_style else scene
    pose_scene, pose_group = scene, group
    if want == "nude" and _nude_sc != scene:
        pose_scene, pose_group = _nude_sc, _scene_group(_nude_sc)

    if chest_on:
        if (not front) or any(h in pose for h in TURN_AWAY_HINTS):
            vp = _visible_pose(POSE_GROUPS.get(pose_group, POSES), idx)
            if vp:
                pose, front = vp
        pool_a = FRONT_ANGLES_BEAUTY if (beauty_angles and front) else (
            BACK_ANGLES_BEAUTY if beauty_angles else (FRONT_ANGLES if front else BACK_ANGLES)
        )
        pool_a = _visible_angles(pool_a)
        if angle not in pool_a:
            angle = pool_a[int(idx) % len(pool_a)]

    if pose_exclude is not None:
        picked = _pose_from_pool(
            pose_group, pose_scene, outfit, idx, pose_exclude,
            front_only=chest_on, salt=seed
        )
        if picked:
            pose, front = picked
    pose, front = _pose_scene_fix(
        pose, front, pose_group, idx, pose_scene, outfit, pose_exclude
    )

    # 姿势最终可能翻转朝向，机位必须跟着改，避免「背面机位 + 正面姿势」
    pool_final = FRONT_ANGLES_BEAUTY if (beauty_angles and front) else (
        BACK_ANGLES_BEAUTY if beauty_angles else (FRONT_ANGLES if front else BACK_ANGLES)
    )
    if chest_on:
        pool_final = _visible_angles(pool_final)
    if angle not in pool_final:
        angle = pool_final[int(idx) % len(pool_final)]

    if person_override:
        face, hair, skin, body, bust, pubic = person_override
    elif height_override:
        # 盲盒抽卡下开启「锁定身材」：只锁定身高与骨架比例，绝不偷锁脸型/发型/肤色！
        body = f"{height_override}, {body}"

    person = (face, hair, skin, body, bust, pubic)

    ground_clothed = None
    if _is_natural_outdoor(scene):
        ground_clothed = _natural_ground_text(scene)
        _anchor = _natural_seat_anchor(pose, outfit, scene)
        if _anchor:
            ground_clothed = f"{ground_clothed}, {_anchor}"

    clothed = _render(
        scene, person, pose, front, shot, angle, outfit, True,
        bust_text=bust_text, neckline_text=neck, reveal_text=reveal_text,
        hair_text=_elegant_hair_fix(hair_text, outfit, idx, hair_style, outfit_style or "现代"),
        hair_color_text=hair_color_text,
        ground_text=ground_clothed, chest_frame=chest_on,
        lighting=lighting, mood=mood, cam_filter=cam_filter,
                cam_filter_strength=cam_filter_strength
    )

    _nude_sc_final = _nude_sc
    ground_nude = None
    if _is_natural_outdoor(_nude_sc_final):
        ground_nude = _natural_ground_text(_nude_sc_final)
        _anchor_n = _natural_seat_anchor(pose, None, _nude_sc_final)
        if _anchor_n:
            ground_nude = f"{ground_nude}, {_anchor_n}"

    nude = _render(
        _nude_sc_final, person, pose, front, shot, angle, outfit, False,
        bust_text=bust_nude_text,
        hair_text=hair_text, hair_color_text=hair_color_text,
        nude_guard=bool(outfit_style) and _scene_kind(_nude_sc_final) == "outdoor" and not _pose_on_natural_seat(pose),
        ground_text=ground_nude,
        lighting=lighting, mood=mood, cam_filter=cam_filter,
                cam_filter_strength=cam_filter_strength
    )
    return clothed, nude, scene, pose, shot, angle, outfit, _nude_sc_final


def build_batch(
    base_idx, count, seed, scene_pref="不限", clothed=True,
    mode="写真套图", dedup_pose=True, rotate_shot=True, extra="",
    cup=None, neckline=None, lock_body=False, beauty_angles=False,
    reveal=None, hair_style=None, hair_color=None, outfit_style="现代",
    sub_theme="自动随机", lighting="跟随场景", mood="自然随机", cam_filter="关闭",
    cam_filter_strength="强"
):
    """返回 list[dict]：idx / prompt / scene / pose / shot / angle / outfit。"""
    mode = _norm_mode(mode)
    n = max(1, min(int(count), 200))
    items = []

    extra = (extra or "").strip()
    cup_rng = random.Random((int(seed) * 2246822519 + 3266489917) % (2 ** 31))
    if cup == "关闭":
        bust_text = BUST_NEUTRAL_CLOTHED
        bust_nude = BUST_NEUTRAL_NUDE
        cup_active = False
    elif cup in ("B", "C", "D"):
        bust_text = CUPS[cup] if clothed else None
        bust_nude = CUPS_NUDE[cup]
        cup_active = True
    else:
        # B~C随机
        cup_pick = cup_rng.choice(["B", "C"])
        bust_text = CUPS[cup_pick] if clothed else None
        bust_nude = CUPS_NUDE[cup_pick]
        cup_active = True

    neckline = _effective_neckline(neckline, reveal)
    neck_eff = neckline if clothed else None
    reveal_text = _reveal_text(reveal, neckline, clothed)

    def _hair_for(i):
        hr = random.Random((int(seed) * 2654435761 + int(i) * 7919 + 31337) % (2 ** 31))
        return (
            _hair_style_text(hair_style, hr, outfit_style),
            _hair_tint_text(hair_color, hr)
        )

    # ------------------------------------------------------------ 模式 1：盲盒抽卡（全随机）
    if mode == "盲盒抽卡":
        height_ov = None
        if lock_body:
            prng = random.Random((int(seed) * 1103515245 + 12345) % (2 ** 31))
            height_ov = prng.choice(HEIGHTS)

        used_poses = set()
        shot_start = None
        if rotate_shot:
            s_rng = random.Random((int(seed) * 22695477 + 11) % (2 ** 31))
            shot_start = s_rng.randrange(len(SHOTS))

        for i in range(n):
            if dedup_pose:
                idx = 1 + ((base_idx - 1 + i * 7919) % TOTAL_SEGMENTS)
            else:
                idx = 1 + ((base_idx - 1 + i) % TOTAL_SEGMENTS)
            _hs, _ht = _hair_for(i)
            _shot_ov = None
            if shot_start is not None:
                _shot_ov = _normalize_shot(SHOTS[(shot_start + i) % len(SHOTS)], beauty_angles)
            clothed_p, nude_p, scene, pose, shot, angle, outfit, nude_scene = build_pair(
                idx, seed + i, scene_pref,
                height_override=height_ov,
                bust_text=bust_text, bust_nude_text=bust_nude,
                neckline_choice=neck_eff, beauty_angles=beauty_angles,
                reveal_text=reveal_text, hair_text=_hs, hair_color_text=_ht,
                outfit_style=outfit_style, hair_style=hair_style,
                pose_exclude=used_poses if dedup_pose else None,
                shot_override=_shot_ov, sub_theme=sub_theme,
                lighting=lighting, mood=mood, cam_filter=cam_filter,
                cam_filter_strength=cam_filter_strength,
                want="clothed" if clothed else "nude"
            )
            if dedup_pose:
                used_poses.add(pose)
            prompt = clothed_p if clothed else nude_p
            if extra:
                prompt = f"{prompt}, {extra}"
            items.append({
                "idx": idx, "prompt": prompt,
                "scene": scene if clothed else nude_scene,
                "pose": pose, "shot": shot, "angle": angle, "outfit": outfit
            })
        return items

    # ------------------------------------------------------------ 模式 2~5：固定模特的套系模式
    # 2. 模特换装：锁 [人]          | 变 [衣 + 景 + 姿 + 镜]
    # 3. 旅拍转场：锁 [人 + 衣]     | 变 [景 + 姿 + 镜]
    # 4. 写真套图：锁 [人 + 衣 + 景] | 变 [姿 + 镜]
    # 5. 定点连拍：锁 [人+衣+景+机位]| 变 [姿]（景别由 rotate_shot 决定）
    lock_outfit = mode in ("旅拍转场", "写真套图", "定点连拍")
    lock_scene = mode in ("写真套图", "定点连拍")
    fixed_pose_only = (mode == "定点连拍")

    rng = random.Random((int(base_idx) * 2654435761) % (2 ** 31))
    scene, kind, group, outfits = _pick_scene(rng, scene_pref)
    outfit = rng.choice(outfits)
    face = rng.choice(FACES)
    hair = rng.choice(HAIRS)
    skin = rng.choice(SKINS)
    body = rng.choice(BODIES)
    bust = rng.choice(BREASTS)
    pubic = rng.choice(PUBIC)

    if lock_body:
        h_rng = random.Random((int(seed) * 2246822519 + 7) % (2 ** 31))
        height = h_rng.choice(HEIGHTS)
        person = (face, hair, skin, f"{height}, {body}", bust, pubic)
    else:
        person = (face, hair, skin, body, bust, pubic)

    # 先计算基准服装与基准场景
    base_style_outfit = _outfit_for(outfit_style, base_idx, sub_theme) or outfit
    base_style_outfit = _fit_outfit(
        base_style_outfit, outfit_style, neck_eff, cup_active, base_idx, sub_theme,
        open_chest=bool(reveal_text)
    )
    _sc0, _kd0, _gp0 = _scene_for_style(outfit_style, scene_pref, base_idx, sub_theme)
    base_style_scene, base_style_group = _sc0, _gp0
    _so0 = _scene_for_outfit(base_style_outfit, scene_pref, base_idx, outfit_style)
    if _so0:
        base_style_scene, base_style_group = _so0[0], _so0[2]
    base_nude_scene = _nude_scene_fix(base_style_scene, False, base_idx, outfit_style)

    chest_on = False
    if clothed:
        chest_on = _chest_visible(
            bust_text, _neckline_text(neck_eff, base_style_outfit, outfit_style),
            neck_eff, _chest_blocked(base_style_outfit), reveal_on=bool(reveal_text)
        )

    pool = POSE_GROUPS.get(base_style_group, POSES)
    if fixed_pose_only:
        fronts = [p for p in pool if p[1]]
        if fronts:
            pool = fronts
    k = min(n, len(pool))
    if dedup_pose:
        picked = rng.sample(pool, k)
        poses = [picked[i % k] for i in range(n)]
    else:
        poses = [rng.choice(pool) for _ in range(n)]

    if rotate_shot:
        start = rng.randrange(len(SHOTS))
        shots = [SHOTS[(start + i) % len(SHOTS)] for i in range(n)]
    else:
        shots = [rng.choice(SHOTS)] * n
    shots = [_normalize_shot(s, beauty_angles) for s in shots]

    lock_angle = None
    if fixed_pose_only:
        pool_a = FRONT_ANGLES_BEAUTY if beauty_angles else FRONT_ANGLES
        if chest_on:
            pool_a = _visible_angles(pool_a)
        lock_angle = pool_a[int(base_idx) % len(pool_a)]

    used_poses = set()
    # 套系模式下人物发型与发色整批固定，确保是同一个模特
    locked_hs, locked_ht = _hair_for(0)

    for i in range(n):
        r = _line_rng(seed, i)
        step_idx = 1 + ((base_idx - 1 + i) % TOTAL_SEGMENTS)
        shot = shots[i]

        # 1) 决定服装
        if lock_outfit:
            of = base_style_outfit
        else:
            lure = _outfit_for(outfit_style, step_idx, sub_theme)
            of = _fit_outfit(lure, outfit_style, neck_eff, cup_active, step_idx, sub_theme,
                             open_chest=bool(reveal_text))

        # 2) 决定场景
        if lock_scene:
            sc, cur_group = base_style_scene, base_style_group
            pose, front = poses[i]
        else:
            _sc, _kd, _gp = _scene_for_style(outfit_style, scene_pref, step_idx, sub_theme)
            sc, cur_group = _sc, _gp
            _so = _scene_for_outfit(of, scene_pref, step_idx, outfit_style)
            if _so:
                sc, cur_group = _so[0], _so[2]
            lp = POSE_GROUPS.get(cur_group, POSES)
            pose, front = r.choice(lp)

        line_chest_on = False
        if clothed:
            line_chest_on = _chest_visible(
                bust_text, _neckline_text(neck_eff, of, outfit_style),
                neck_eff, _chest_blocked(of), reveal_on=bool(reveal_text)
            )

        if line_chest_on and ((not front) or any(h in pose for h in TURN_AWAY_HINTS)):
            vp = _visible_pose(POSE_GROUPS.get(cur_group, POSES), step_idx)
            if vp:
                pose, front = vp

        use_sc = sc
        if not clothed:
            use_sc = base_nude_scene if lock_scene else _nude_scene_fix(sc, False, step_idx, outfit_style)

        if dedup_pose:
            picked = _pose_from_pool(
                cur_group, use_sc, of, step_idx, used_poses,
                front_only=line_chest_on or fixed_pose_only, salt=seed
            )
            if picked:
                pose, front = picked
        pose, front = _pose_scene_fix(
            pose, front, cur_group, step_idx, use_sc, of,
            used_poses if dedup_pose else None, front_only=fixed_pose_only
        )
        if dedup_pose:
            used_poses.add(pose)

        if fixed_pose_only:
            angle = lock_angle
        else:
            angles = FRONT_ANGLES_BEAUTY if (beauty_angles and front) else (
                BACK_ANGLES_BEAUTY if beauty_angles else (FRONT_ANGLES if front else BACK_ANGLES)
            )
            if line_chest_on:
                angles = _visible_angles(angles)
            angle = r.choice(angles)

        neck = _neckline_text(neck_eff, of, outfit_style)
        ground = None
        if _is_natural_outdoor(use_sc):
            ground = _natural_ground_text(use_sc)
            _anchor = _natural_seat_anchor(pose, of if clothed else None, use_sc)
            if _anchor:
                ground = f"{ground}, {_anchor}"

        prompt = _render(
            use_sc, person, pose, front, shot, angle, of, clothed, extra,
            bust_text=(bust_text if clothed else bust_nude),
            neckline_text=neck, reveal_text=reveal_text,
            hair_text=_elegant_hair_fix(locked_hs, of, base_idx if lock_outfit else step_idx, hair_style, outfit_style),
            hair_color_text=locked_ht,
            nude_guard=(not clothed) and _scene_kind(use_sc) == "outdoor" and not _pose_on_natural_seat(pose),
            ground_text=ground, chest_frame=line_chest_on,
            lighting=lighting, mood=mood, cam_filter=cam_filter,
                cam_filter_strength=cam_filter_strength
        )
        # 锁场景时段号固定显示 base_idx，变场景时显示当前 step_idx，确保段信息与实际抽取完全一致
        rec_idx = base_idx if lock_scene else step_idx
        items.append({
            "idx": rec_idx, "prompt": prompt, "scene": use_sc,
            "pose": pose, "shot": shot, "angle": angle, "outfit": of
        })
    return items


def _save_txt(seed, items, lines, clothed):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        tag = "clothed" if clothed else "nude"
        name = f"crazy3ds_pair_{int(seed) % 100000:05d}_{len(items):02d}_{tag}.txt"
        path = os.path.join(OUTPUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return path
    except Exception:
        return ""


class Crazy3DSPairPromptPlusNode:
    """Crazy3DS 美女提示词大师：商业级人像提示词批量生成节点。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "随机种子": ("INT", {
                    "default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "control_after_generate": True,
                    "tooltip": "同一颗种子 = 同一批结果。段号由种子换算（1~50000 段）。"
                }),
                "穿衣服": ("BOOLEAN", {
                    "default": True, "label_on": "有衣服", "label_off": "没衣服",
                    "tooltip": "开 = 有衣服，关 = 没衣服。同一种子下场景/姿势/机位完全对齐，只换服装。\n"
                               "关掉后「领口 / 露肤度」自动置灰；「罩杯」在两个版本下均生效。"
                }),
                "场景偏好": (["不限", "室内", "户外"], {
                    "default": "不限",
                    "tooltip": "筛选最终场景。泳装触发的泳池、礼服触发的酒店大堂也遵守此偏好。"
                }),
                "数量": ("INT", {
                    "default": 4, "min": 1, "max": 200, "step": 1,
                    "tooltip": "一次输出几条提示词（1-200）。"
                }),
                "生成模式": (MODES, {
                    "default": "写真套图",
                    "tooltip": "盲盒抽卡：人/衣/景/姿/镜全变，适合找灵感。\n"
                               "模特换装：锁同一模特，去不同场景换穿不同衣服。\n"
                               "旅拍转场：锁同一模特+同一套衣服，穿梭在不同场景摆拍。\n"
                               "写真套图：锁模特+衣服+场景，围绕人物换不同机位与姿势拍写真。\n"
                               "定点连拍：三脚架固定机位（人/衣/景/机位全锁），只连续变换动作。"
                }),
                "姿势去重": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "开 = 同一批内姿势绝不重复（五档模式全部生效）。"
                }),
                "景别轮转": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "开 = 景别按 全身 / 七分身 / 半身 / 远景 / 中全景 依次轮转（含定点连拍模式）。\n"
                               "关 = 整批保持同一景别。"
                }),
                "罩杯": (CUP_CHOICES, {
                    "default": "B~C随机",
                    "tooltip": "穿衣版写「隔着布料的胸型轮廓」，无衣版写「自然胸型」，两版均生效。\n"
                               "选「关闭」时输出自然匀称体态，不强调胸围。"
                }),
                "领口": (NECKLINES, {
                    "default": "跟随服装",
                    "tooltip": "跟随服装 = 按单品自动判断；古风下自动映射为交领/坦领/抹胸诃子。\n"
                               "「露肤度」开启时，高领 / 圆领会自动退回跟随服装。"
                }),
                "锁定身材": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "开 = 整批锚定同一身高骨架（160/165/170cm），避免批次内忽高忽低。"
                }),
                "美姿机位": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "开 = 启用显腿长显比例的商业人像机位池，过滤掉死亡俯拍/仰拍。"
                }),
                "露肤度": (REVEAL_CHOICES, {
                    "default": "关闭",
                    "tooltip": "关闭 / 微露 / 适中。优先于高领/圆领；无衣模式下自动置灰。"
                }),
                "服装风格": (OUTFIT_STYLES, {
                    "default": "现代",
                    "tooltip": "现代 / 古风。服装池与场景池物理隔离，绝不跨池串味。"
                }),
                "主题细分": (SUB_THEMES, {
                    "default": "自动随机",
                    "tooltip": "26 档主题：现代 15 档（日常/纯欲/通勤OL/私密居家/运动/甜酷/泳装/晚礼服/"
                               "新中式旗袍/校园清纯/法式优雅/街头机能/婚纱白纱/度假亚麻/暗夜酷感）"
                               "＋古风 10 档（华丽宫廷/清雅书卷/飒爽侠女/妩媚风情/魏晋宽袖/飘逸仙侠/"
                               "婚嫁红妆/异域胡旋/禅意道袍/女扮男装）。"
                }),
                "发型": (HAIR_STYLES, {
                    "default": "跟随服装",
                    "tooltip": "跟随服装 = 现代装抽现代发型、古风装自动配古风发髻（防穿帮）。\n"
                               "也可强制指定 经典 / 现代 / 古风。"
                }),
                "发色": (HAIR_COLORS, {
                    "default": "跟随发型",
                    "tooltip": "跟随发型 = 不额外加染发词；现代 / 古风 = 从对应色板抽样。"
                }),
                "光影氛围": (LIGHTING_CHOICES, {
                    "default": "跟随场景",
                    "tooltip": "跟随场景 = 自动识别白天/夜景/日落匹配光线；也可强制指定落日逆光、暗调情绪、闪光直打等。"
                }),
                "情绪眼神": (MOOD_CHOICES, {
                    "default": "自然随机",
                    "tooltip": "控制人物面部微表情与眼神互动感（直视镜头、松弛抓拍、清冷高级、温婉甜美、微醺慵懒）。"
                }),
                "相机滤镜": (CAMERA_FILTERS, {
                    "default": "关闭",
                    "tooltip": "叠加真实人像机身的色彩科学与特殊滤镜质感：\n"
                               "佳能奶油肤色 / 尼康通透中性 / 索尼清冷或青橙 / 富士 Classic Chrome·Classic Neg·Pro Neg /\n"
                               "徕卡德味 / 哈苏与飞思中画幅肤色 / 柯达 Portra·Gold·Ektar / 富士 Pro400H / CineStill 800T /\n"
                               "依尔福 HP5 黑白 / 黑柔·白柔·柔焦·星光镜。\n"
                               "「关闭」= 只输出焦段与光影描述，不附加任何滤镜。"
                }),
                "滤镜强度": (CAMERA_FILTER_STRENGTHS, {
                    "default": "强",
                    "tooltip": "调节滤镜的「描述浓度」（不是模型强度）：\n"
                               "弱 = 只保留一句核心色彩科学 + subtle，不加颗粒/光晕等特征；\n"
                               "中 = 核心 + 前 2 个特征（多为对比 / 肤色 / 高光）；\n"
                               "强 = 全部特征（等同旧版默认效果）。\n"
                               "黑柔 / 白柔 / 柔焦 / 星光会随强度切换真实密度档：\n"
                               "黑柔 1/8→1/4、Glimmerglass 2→4、Softar I→III、星芒 4→8 线。"
                }),
                "编号": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "开 = 「段信息」与保存的 txt 每行带 #01 前缀。\n"
                               "注：「提示词」列表输出口永远保持纯净无编号，可直接连 CLIP。"
                }),
                "追加词": ("STRING", {
                    "default": "", "multiline": False,
                    "tooltip": "非空时拼在每条提示词最末尾。例：film grain, Fujifilm XT4"
                }),
                "保存txt": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "开 = 自动落盘一份到 output/crazy3ds_pair_XXXXX_NN_clothed.txt。"
                }),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("提示词", "负面提示词", "段信息")
    OUTPUT_IS_LIST = (True, False, False)
    FUNCTION = "run"
    CATEGORY = "Crazy3DS/提示词大师"

    def run(
        self, 随机种子, 穿衣服, 场景偏好, 数量, 生成模式,
        姿势去重, 景别轮转, 编号, 追加词, 保存txt,
        罩杯="B~C随机", 领口="跟随服装", 锁定身材=True, 美姿机位=True,
        露肤度="关闭", 服装风格="现代", 主题细分="自动随机",
        发型="跟随服装", 发色="跟随发型", 光影氛围="跟随场景", 情绪眼神="自然随机",
        相机滤镜="关闭", 滤镜强度="强",
        自定义数量=0  # 兼容旧 API 脚本传参
    ):
        seed = int(随机种子)
        n = int(自定义数量) if int(自定义数量) > 0 else int(数量)
        n = max(1, min(n, 200))
        base_idx = 1 + (seed % TOTAL_SEGMENTS)

        items = build_batch(
            base_idx, n, seed, 场景偏好, bool(穿衣服), 生成模式,
            dedup_pose=bool(姿势去重), rotate_shot=bool(景别轮转),
            extra=(追加词 or "").strip(),
            cup=罩杯, neckline=领口, reveal=露肤度,
            outfit_style=服装风格, sub_theme=主题细分,
            hair_style=发型, hair_color=发色,
            lighting=光影氛围, mood=情绪眼神, cam_filter=相机滤镜,
            cam_filter_strength=滤镜强度,
            lock_body=bool(锁定身材), beauty_angles=bool(美姿机位)
        )

        prompts = [it["prompt"] for it in items]
        mode_norm = _norm_mode(生成模式)

        multi_lines = []
        info_lines = []
        for i, it in enumerate(items):
            prefix = f"#{i + 1:02d} " if 编号 else ""
            multi_lines.append(f"{prefix}{it['prompt']}")
            info_lines.append(
                f"{prefix}[{mode_norm}] 段 {it['idx']:05d} · 场景：{it['scene'][:26]}…"
                f" · 姿势：{it['pose'][:34]}… · 景别：{it['shot'].split(',')[0]}"
                f" · 机位：{it['angle']}"
            )

        if 保存txt:
            _save_txt(seed, items, multi_lines, bool(穿衣服))

        negative = build_negative(
            clothed=bool(穿衣服), outfit_style=服装风格, sub_theme=主题细分,
            lighting=光影氛围, cam_filter=相机滤镜, scene_pref=场景偏好
        )
        return (prompts, negative, "\n".join(info_lines))


# 保持向后别名引用，方便旧测试脚本导入
PairPromptPlusNode = Crazy3DSPairPromptPlusNode

NODE_CLASS_MAPPINGS = {
    "Crazy3DS_PairPromptPlus": Crazy3DSPairPromptPlusNode,
    # 兼容旧工作流直接打开不报错
    "美女提示词PLUS": Crazy3DSPairPromptPlusNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Crazy3DS_PairPromptPlus": f"Crazy3DS 美女提示词大师 {__version__}",
    "美女提示词PLUS": f"Crazy3DS 美女提示词大师 {__version__} (兼容旧版)",
}