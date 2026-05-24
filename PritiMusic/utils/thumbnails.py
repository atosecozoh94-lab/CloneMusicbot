import os
import re
import random
import time
import aiofiles
import aiohttp

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch

# ✅ Bot imports
from PritiMusic import app
from config import YOUTUBE_IMG_URL

CACHE_DIR = "cache"
ASSETS_DIR = "PritiMusic/assets"
os.makedirs(CACHE_DIR, exist_ok=True)


# ==========================================
# COMMON HELPERS
# ==========================================
def get_random_fallback_img():
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"


# ==========================================
# 🔴 NEW THUMBNAIL LOGIC (FOR MAIN BOT)
# ==========================================
PANEL_W, PANEL_H = 763, 545
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 88
TRANSPARENCY = 170
INNER_OFFSET = 36
THUMB_W, THUMB_H = 542, 273
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET
TITLE_X = 377
META_X = 377
TITLE_Y = THUMB_Y + THUMB_H + 10
META_Y = TITLE_Y + 45
BAR_X, BAR_Y = 388, META_Y + 45
BAR_RED_LEN = 280
BAR_TOTAL_LEN = 480
ICONS_W, ICONS_H = 415, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 48
MAX_TITLE_WIDTH = 580

def trim_to_width(text: str, font, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

async def get_thumb(videoid: str, player_username: str = None) -> str:
    # Final thumbnail path
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_main_new.png")
    
    # Agar thumbnail pehle se bana hua hai, toh seedha yahi se return karo
    if os.path.exists(cache_path):
        return cache_path

    # 🔥 FIX: Unique temp file naam taaki file overwrite ki wajah se do alag thumbnail mix na ho
    unique_id = f"{videoid}_{int(time.time())}_{random.randint(100, 999)}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_main_{unique_id}.png")

    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        try:
            results_data = await results.next()
            data = results_data.get("result", [])[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            thumbnail = data.get("thumbnails", [{}])[0].get("url") or get_random_fallback_img()
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            title, thumbnail, duration, views = "Unsupported Title", get_random_fallback_img(), None, "Unknown Views"

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown Mins"

        # Image download karna (safe tarike se)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            return get_random_fallback_img()

        # Image Processing (Blur, Brightness, Panel)
        base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
        bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

        panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
        overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
        frosted = Image.alpha_composite(panel_area, overlay)
        mask = Image.new("L", (PANEL_W, PANEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
        bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

        draw = ImageDraw.Draw(bg)
        try:
            title_font = ImageFont.truetype(os.path.join(ASSETS_DIR, "font2.ttf"), 32)
            regular_font = ImageFont.truetype(os.path.join(ASSETS_DIR, "font.ttf"), 18)
        except OSError:
            title_font = regular_font = ImageFont.load_default()

        thumb = base.resize((THUMB_W, THUMB_H))
        tmask = Image.new("L", thumb.size, 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
        bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

        # Title aur Views likhna
        draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
        draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

        # Progress bar draw karna
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
        draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
        draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

        draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
        end_text = "Live" if is_live else duration_text
        draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

        # Play icons lagana
        icons_path = os.path.join(ASSETS_DIR, "play_icons.png")
        if os.path.isfile(icons_path):
            ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
            r, g, b, a = ic.split()
            black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
            bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

        final_img = bg.convert("RGB")
        final_img.save(cache_path)
        return cache_path

    except Exception as e:
        return get_random_fallback_img()
    finally:
        # 🔥 FIX: Yeh ensure karega ki temp file hamesha delete ho jaye
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass
