# ---------------------------------------------------------------
# 🔸 CLONE MUSIC BOT Project
# 🔹 Modified for: ronakgupta322 (https://github.com/ronakgupta322/clonemusicbot)
# 📅 Copyright © 2026 – All Rights Reserved
# ---------------------------------------------------------------
import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ✅ MATCHING PANEL DIMENSIONS (Bada aur chaurha panel)
PANEL_W, PANEL_H = 860, 600
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = (720 - PANEL_H) // 2
TRANSPARENCY = 210  # Photo jaisa solid frosted look

# ✅ MATCHING INNER THUMBNAIL (Badi screen)
THUMB_W, THUMB_H = 780, 360
THUMB_X = PANEL_X + 40
THUMB_Y = PANEL_Y + 40

# ✅ LEFT-ALIGNED TEXT COORDINATES (Photo ke hisaab se)
TITLE_X = THUMB_X
TITLE_Y = THUMB_Y + THUMB_H + 20

META_X = THUMB_X
META_Y = TITLE_Y + 45

# ✅ FULL WIDTH PROGRESS BAR
BAR_X = THUMB_X
BAR_Y = META_Y + 45
BAR_TOTAL_LEN = THUMB_W
BAR_RED_LEN = int(BAR_TOTAL_LEN * 0.45) # Red line ka size

# ✅ ICONS AT BOTTOM CENTER
ICONS_W, ICONS_H = 415, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 45

MAX_TITLE_WIDTH = THUMB_W - 20

def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = " …"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

async def get_thumb(videoid: str, *args, **kwargs) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v4.png")
    if os.path.exists(cache_path):
        return cache_path

    # YouTube video data fetch
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        result_items = results_data.get("result", [])
        if not result_items:
            raise ValueError("No results found.")
        data = result_items[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
    except Exception:
        title, thumbnail, duration, views = "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown Views"

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "Unknown Mins"

    # Download thumbnail
    thumb_path = os.path.join(CACHE_DIR, f"thumb{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except Exception:
        return YOUTUBE_IMG_URL

    # Create base image & background blur
    base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
    bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(12))).enhance(0.55)

    # Frosted glass panel
    panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
    overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (220, 220, 220, TRANSPARENCY))
    frosted = Image.alpha_composite(panel_area, overlay)
    mask = Image.new("L", (PANEL_W, PANEL_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 45, fill=255)
    bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

    draw = ImageDraw.Draw(bg)
    try:
        # ✅ PERFECT FONT SIZES
        title_font = ImageFont.truetype("clonemusicbot/assets/assets/font2.ttf", 36)
        regular_font = ImageFont.truetype("clonemusicbot/assets/assets/font.ttf", 20)
    except OSError:
        title_font = regular_font = ImageFont.load_default()

    # Rounded Video Thumbnail inside Panel
    thumb = base.resize((THUMB_W, THUMB_H))
    tmask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 25, fill=255)
    bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

    # ✅ LEFT ALIGNED TEXT
    trimmed_title = trim_to_width(title, title_font, MAX_TITLE_WIDTH)
    meta_text = f"YouTube | {views}"

    draw.text((TITLE_X, TITLE_Y), trimmed_title, fill="black", font=title_font)
    draw.text((META_X, META_Y), meta_text, fill="#333333", font=regular_font)

    # ✅ FULL WIDTH PROGRESS BAR
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="#8E8E93", width=5)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 8, BAR_Y - 8), (BAR_X + BAR_RED_LEN + 8, BAR_Y + 8)], fill="red")

    # Time indicators (Left and Right aligned to the bar)
    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
    end_text = "Live" if is_live else duration_text
    end_text_w = draw.textlength(end_text, font=regular_font)
    draw.text((BAR_X + BAR_TOTAL_LEN - end_text_w, BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

    # Icons Layer Overlay
    icons_path = "clonemusicbot/assets/assets/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
        bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

    # Cleanup temporary image file
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.save(cache_path)
    return cache_path
