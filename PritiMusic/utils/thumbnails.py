# -----------------------------------------------
# 🔸 Clone Music Bot Thumbnail Generator (BULLETPROOF)
# 🔹 Dark Glassmorphism Premium UI
# -----------------------------------------------
import os
import re
import random
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

# --- PATHS & CONSTANTS ---
CACHE_DIR = "cache"
ASSETS_DIR = "PritiMusic/assets" 
os.makedirs(CACHE_DIR, exist_ok=True)

PANEL_W, PANEL_H = 780, 560
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 80
TRANSPARENCY = 200 
INNER_OFFSET = 36

THUMB_W, THUMB_H = 560, 290
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET

TITLE_X, TITLE_Y = THUMB_X, THUMB_Y + THUMB_H + 20
META_X, META_Y = THUMB_X, TITLE_Y + 45
BAR_X, BAR_Y = THUMB_X, META_Y + 55
BAR_RED_LEN, BAR_TOTAL_LEN = 320, THUMB_W
ICONS_W, ICONS_H = 415, 45
ICONS_X, ICONS_Y = PANEL_X + (PANEL_W - ICONS_W) // 2, BAR_Y + 45

MAX_TITLE_WIDTH = THUMB_W

NEON_RED = "#FF0055"
TEXT_WHITE = "#FFFFFF"
TEXT_GRAY = "#B3B3B3"


# --- HELPER FUNCTIONS (ERROR-FREE) ---
def get_random_fallback_img():
    """Crash hone se bachane ke liye default image"""
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

def get_font_width(font, text):
    """Pillow ke naye aur purane dono versions ke liye safe"""
    try:
        return font.getlength(text)
    except AttributeError:
        try:
            return font.getsize(text)[0]
        except Exception:
            return len(text) * 10 # Absolute fallback

def trim_to_width(text: str, font, max_w: int) -> str:
    ellipsis = "…"
    if get_font_width(font, text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if get_font_width(font, text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


# --- MAIN THUMBNAIL FUNCTION ---
async def get_thumb(videoid: str, player_username: str = None) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_premium.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        # 1. Fetch Data via py_yt
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        try:
            results_data = await results.next()
            result_items = results_data.get("result", [])
            if not result_items:
                raise ValueError("No results")
            data = result_items[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            thumbnail = data.get("thumbnails", [{}])[0].get("url") or get_random_fallback_img()
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            title, thumbnail, duration, views = "Audio Track", get_random_fallback_img(), None, ""

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown"

        # 2. Download Base Image
        thumb_path = os.path.join(CACHE_DIR, f"thumb_{videoid}.png")
        downloaded = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
                            downloaded = True
        except Exception:
            pass
            
        if not downloaded:
            return get_random_fallback_img()

        # 3. Create UI
        base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
        bg = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(15))).enhance(0.3)

        # Panel
        panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
        overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (15, 15, 15, TRANSPARENCY))
        frosted = Image.alpha_composite(panel_area, overlay)
        mask = Image.new("L", (PANEL_W, PANEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 40, fill=255)
        bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

        # Draw details
        draw = ImageDraw.Draw(bg)
        
        # SAFE FONT LOADING
        try:
            title_font = ImageFont.truetype(os.path.join(ASSETS_DIR, "font2.ttf"), 34)
            regular_font = ImageFont.truetype(os.path.join(ASSETS_DIR, "font.ttf"), 18)
            small_font = ImageFont.truetype(os.path.join(ASSETS_DIR, "font.ttf"), 16)
        except Exception:
            title_font = regular_font = small_font = ImageFont.load_default()

        # Inner Thumbnail
        thumb = base.resize((THUMB_W, THUMB_H))
        tmask = Image.new("L", thumb.size, 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 25, fill=255)
        bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

        # Typography
        draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill=TEXT_WHITE, font=title_font)
        draw.text((META_X, META_Y), f"YouTube  •  {views}", fill=TEXT_GRAY, font=regular_font)

        # Progress Bar
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="#333333", width=6) 
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill=NEON_RED, width=6) 
        draw.ellipse([(BAR_X + BAR_RED_LEN - 8, BAR_Y - 8), (BAR_X + BAR_RED_LEN + 8, BAR_Y + 8)], fill=TEXT_WHITE)

        # Timers
        draw.text((BAR_X, BAR_Y + 12), "00:00", fill=TEXT_GRAY, font=small_font)
        end_w = get_font_width(small_font, end_text)
        draw.text((BAR_X + BAR_TOTAL_LEN - end_w, BAR_Y + 12), end_text, fill=NEON_RED if is_live else TEXT_GRAY, font=small_font)

        # SAFE ICON LOADING
        icons_path = os.path.join(ASSETS_DIR, "play_icons.png")
        if os.path.isfile(icons_path):
            try:
                ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
                r, g, b, a = ic.split()
                white_ic = Image.merge("RGBA", (r.point(lambda *_: 255), g.point(lambda *_: 255), b.point(lambda *_: 255), a))
                bg.paste(white_ic, (ICONS_X, ICONS_Y), white_ic)
            except Exception:
                pass # Agar icon file corrupt hui toh skip kar dega, crash nahi hoga

        # Cleanup & Save
        try:
            os.remove(thumb_path)
        except OSError:
            pass

        final_img = bg.convert("RGB")
        final_img.save(cache_path)
        return cache_path

    except Exception as e:
        print(f"Critial Thumbnail Error (Safely Bypassed): {e}")
        return get_random_fallback_img()
