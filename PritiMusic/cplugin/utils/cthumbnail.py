# -----------------------------------------------
# 🔸 RONAK MUSIC Project Thumbnail Module
# 🔹 Developed & Maintained by: Simple Boy (https://github.com/Ronakgupta322)
# 🔹 Optimized for Clone Bots (Non-blocking Threading + Crash Proof)
# 📅 Copyright © 2026 – All Rights Reserved
# -----------------------------------------------

import os
import re
import asyncio
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch

# Try importing from config, fallback to default image if it fails
try:
    from config import YOUTUBE_IMG_URL
except ImportError:
    YOUTUBE_IMG_URL = "https://telegra.ph/file/c82db7a30ddb94b0d061c.png"

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

PANEL_W, PANEL_H = 763, 545
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 88
TRANSPARENCY = 170
INNER_OFFSET = 36

THUMB_W, THUMB_H = 542, 273
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET

TITLE_X, META_X = 377, 377
TITLE_Y = THUMB_Y + THUMB_H + 10
META_Y = TITLE_Y + 45

BAR_X, BAR_Y = 388, META_Y + 45
BAR_RED_LEN, BAR_TOTAL_LEN = 280, 480

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

# ✅ Threaded Synchronous Function (Lag Preventer)
def generate_image_sync(thumb_path, cache_path, title, views, duration_text, is_live):
    try:
        base = Image.open(thumb_path).resize((1280, 720)).convert("RGBA")
        bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

        # Frosted glass panel
        panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
        overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
        frosted = Image.alpha_composite(panel_area, overlay)
        mask = Image.new("L", (PANEL_W, PANEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
        bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

        draw = ImageDraw.Draw(bg)
        
        # ✅ Font fetching safely
        try:
            title_font = ImageFont.truetype("SIMPLE_MUSIC/assets/assets/font2.ttf", 32)
            regular_font = ImageFont.truetype("SIMPLE_MUSIC/assets/assets/font.ttf", 18)
        except OSError:
            try:
                # Fallback to local assets if SIMPLE_MUSIC path fails
                title_font = ImageFont.truetype("assets/font2.ttf", 32)
                regular_font = ImageFont.truetype("assets/font.ttf", 18)
            except OSError:
                title_font = regular_font = ImageFont.load_default()

        thumb = base.resize((THUMB_W, THUMB_H))
        tmask = Image.new("L", thumb.size, 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
        bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

        draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
        draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

        # Progress bar
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
        draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
        draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

        draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
        end_text = "Live" if is_live else duration_text
        draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

        # Icons
        icons_path = "SIMPLE_MUSIC/assets/assets/play_icons.png"
        if not os.path.isfile(icons_path):
            icons_path = "assets/play_icons.png" # Fallback path
            
        if os.path.isfile(icons_path):
            ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
            r, g, b, a = ic.split()
            black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
            bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

        bg.convert("RGB").save(cache_path)
    except Exception as e:
        print(f"Thumbnail Error: {e}")
    finally:
        # Save storage by removing original unedited thumbnail
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass

# ✅ Added bot_username, *args and **kwargs to ignore extra arguments passed by the clone bots
async def get_thumb(videoid: str, bot_username: str = "main", *args, **kwargs) -> str:
    # ✅ Unique path for each bot to prevent Image Overwrite Errors
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{bot_username}_v4.png")
    if os.path.exists(cache_path):
        return cache_path

    try:
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        results_data = await results.next()
        result_items = results_data.get("result", [])
        
        if not result_items:
            raise ValueError("No results found.")
            
        data = result_items[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL).split("?")[0]
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
    except Exception:
        title, thumbnail, duration, views = "Unsupported Title", YOUTUBE_IMG_URL, None, "Unknown Views"

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "Unknown Mins"

    # ✅ Unique raw path for each clone bot
    thumb_path = os.path.join(CACHE_DIR, f"thumb_{videoid}_{bot_username}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
                else:
                    return YOUTUBE_IMG_URL
    except Exception:
        return YOUTUBE_IMG_URL

    # ✅ Threading used to prevent clone bot from hanging during heavy image processing
    await asyncio.to_thread(generate_image_sync, thumb_path, cache_path, title, views, duration_text, is_live)

    return cache_path if os.path.exists(cache_path) else YOUTUBE_IMG_URL
