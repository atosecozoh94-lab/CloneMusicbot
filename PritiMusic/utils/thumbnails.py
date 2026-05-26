import os
import re
import time
import random
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Helper: Text ko wrap/trim karne ke liye aur uska width nikalne ke liye
def get_text_width(font, text):
    try:
        return int(font.getlength(text))
    except Exception:
        return font.getbbox(text)[2] - font.getbbox(text)[0]

def trim_to_width(text: str, font, max_w: int) -> str:
    ellipsis = "…"
    if get_text_width(font, text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if get_text_width(font, text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

# Helper: Fonts safe loading
def load_font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size) # Fallback
        except Exception:
            return ImageFont.load_default()

# 🟢 SPOTIFY EDITION THUMBNAIL LOGIC
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    cache_prefix = str(args[0]) if args else kwargs.get("bot_username", "main_bot")
    
    # Custom Thumbnail File Check
    custom_thumb = kwargs.get("thumb_url") or kwargs.get("thumbnail")
    
    is_local_file = False
    if custom_thumb and os.path.isfile(custom_thumb):
        is_local_file = True
        raw_image_path = custom_thumb 
    else:
        unique_id = f"{int(time.time())}_{random.randint(100, 999)}"
        thumb_path = os.path.join(CACHE_DIR, f"raw_{cache_prefix}_{videoid}_{unique_id}.png")
        raw_image_path = thumb_path 
    
    # Final cache output path (v6_spotify)
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{cache_prefix}_v6_spotify.png")
    if os.path.exists(cache_path):
        return cache_path

    # Fetch Data from YouTube
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        data = results_data.get("result", [])[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
        channel_name = data.get("channel", {}).get("name", "Unknown Artist")
        youtube_thumb_url = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
    except Exception:
        title, duration, views, channel_name, youtube_thumb_url = "Unsupported Title", None, "Unknown Views", "Unknown Artist", YOUTUBE_IMG_URL

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "LIVE" if is_live else duration or "0:00"

    # Download ONLY if it's NOT a local file
    if not is_local_file:
        download_url = custom_thumb if custom_thumb else youtube_thumb_url
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(raw_image_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            pass

    # ---------------------------------------------------------
    # 🎨 SPOTIFY UI DRAWING
    # ---------------------------------------------------------
    try:
        W, H = 1280, 720
        try:
            raw_img = Image.open(raw_image_path).convert("RGBA")
        except Exception:
            raw_img = Image.new("RGBA", (500, 500), (40, 40, 40, 255))

        # 1. Background: Heavy Blur & Darken (Spotify Fullscreen Theme)
        base = ImageOps.fit(raw_img, (W, H), Image.LANCZOS)
        bg = base.filter(ImageFilter.GaussianBlur(60)) # Heavy blur
        bg = ImageEnhance.Brightness(bg).enhance(0.25) # Dark tint

        draw = ImageDraw.Draw(bg)

        # 2. Main Album Art (Big, Square, Center)
        ALBUM_SIZE = 460
        AX = (W - ALBUM_SIZE) // 2
        AY = 50

        album_img = ImageOps.fit(raw_img, (ALBUM_SIZE, ALBUM_SIZE), Image.LANCZOS)
        
        # Spotify uses very slight rounded corners for album art
        mask = Image.new("L", (ALBUM_SIZE, ALBUM_SIZE), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, ALBUM_SIZE, ALBUM_SIZE), radius=15, fill=255)
        bg.paste(album_img, (AX, AY), mask)

        # 3. Load Fonts
        title_font = load_font("SHUKLAMUSIC/assets/assets/font2.ttf", 42) # Bold
        artist_font = load_font("SHUKLAMUSIC/assets/assets/font.ttf", 26) # Regular
        time_font = load_font("SHUKLAMUSIC/assets/assets/font.ttf", 18)   # Small

        # 4. Text: Left-aligned to the Album Art
        TITLE_Y = AY + ALBUM_SIZE + 35
        safe_title = trim_to_width(title, title_font, ALBUM_SIZE - 20)
        
        # Title (Pure White)
        draw.text((AX, TITLE_Y), safe_title, fill=(255, 255, 255, 255), font=title_font)

        # Artist (Spotify Gray: #B3B3B3)
        ARTIST_Y = TITLE_Y + 55
        draw.text((AX, ARTIST_Y), channel_name, fill=(179, 179, 179, 255), font=artist_font)

        # 5. Progress Bar (Spotify Style)
        BAR_Y = ARTIST_Y + 50
        filled_ratio = 0.35 # Fixed at 35% visually
        filled_len = int(ALBUM_SIZE * filled_ratio)
        
        # Empty Track (Dark Gray: #4D4D4D)
        draw.line([(AX, BAR_Y), (AX + ALBUM_SIZE, BAR_Y)], fill=(77, 77, 77, 255), width=5)
        
        # Filled Track (Pure White)
        draw.line([(AX, BAR_Y), (AX + filled_len, BAR_Y)], fill=(255, 255, 255, 255), width=5)
        
        # Playhead Dot (Pure White)
        draw.ellipse([(AX + filled_len - 7, BAR_Y - 7), (AX + filled_len + 7, BAR_Y + 7)], fill=(255, 255, 255, 255))

        # 6. Timers (Below the bar, small font)
        TIME_Y = BAR_Y + 15
        
        # Current Time (0:00)
        draw.text((AX, TIME_Y), "0:00", fill=(179, 179, 179, 255), font=time_font)
        
        # Total Duration / Live Tag
        dur_w = get_text_width(time_font, duration_text)
        # Agar LIVE hai to Spotify Green color dena (#1DB954)
        dur_color = (29, 185, 84, 255) if is_live else (179, 179, 179, 255)
        draw.text((AX + ALBUM_SIZE - dur_w, TIME_Y), duration_text, fill=dur_color, font=time_font)

        # Save and return
        bg.convert("RGB").save(cache_path, quality=95)
        return cache_path

    finally:
        # File Cleanup (Local clone files are safe)
        if not is_local_file and os.path.exists(raw_image_path):
            try:
                os.remove(raw_image_path)
            except OSError:
                pass
