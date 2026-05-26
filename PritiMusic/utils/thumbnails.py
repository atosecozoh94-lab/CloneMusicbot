import os
import re
import random
import time
import aiofiles
import aiohttp

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
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

def get_font(size: int, bold: bool = False):
    font_candidates = [
        os.path.join(ASSETS_DIR, "font2.ttf" if bold else "font.ttf"),
        os.path.join(ASSETS_DIR, "Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf"),
        "arial.ttf",
    ]
    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def text_width(font, text: str) -> int:
    try:
        return int(font.getlength(text))
    except Exception:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

def wrap_text_lines(text: str, font, max_width: int, max_lines: int = 2):
    words = str(text or "").split()
    if not words:
        return ["Unknown Title"]
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if text_width(font, test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if not lines:
        lines = ["Unknown Title"]
    
    # Truncate last line with ellipsis if it exceeds max_lines
    if len(lines) == max_lines:
        last_line = lines[-1]
        ellipsis = "..."
        if text_width(font, last_line) > max_width:
            for i in range(len(last_line), 0, -1):
                if text_width(font, last_line[:i] + ellipsis) <= max_width:
                    lines[-1] = last_line[:i] + ellipsis
                    break
    return lines[:max_lines]

async def download_image(url: str, dest: str) -> bool:
    try:
        if not url or not url.startswith("http"):
            return False
        timeout = aiohttp.ClientTimeout(total=15)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                data = await resp.read()
                async with aiofiles.open(dest, "wb") as f:
                    await f.write(data)
        return True
    except Exception:
        return False


# ==========================================
# 💎 PRO LEVEL TECHNICAL THUMBNAIL LOGIC
# ==========================================
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    # 1. Identity Check - Clone bot overlap fix
    main_bot_username = getattr(app, "username", "MusicBot")
    player_username = None
    
    if len(args) > 0:
        player_username = str(args[0])
    elif "bot_username" in kwargs:
        player_username = str(kwargs["bot_username"])
    elif "player_username" in kwargs:
        player_username = str(kwargs["player_username"])
        
    current_username = player_username if (player_username and player_username != "None") else main_bot_username

    # Priority to custom clone bot thumbnails if passed via kwargs
    custom_thumb = kwargs.get("thumb_url") or kwargs.get("image_url") or kwargs.get("thumbnail")

    # Tech Premium cache identifier so old buggy images don't load
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{current_username}_tech_premium.png")
    if os.path.exists(cache_path):
        return cache_path

    unique_id = f"{videoid}_{current_username}_{int(time.time())}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_premium_{unique_id}.png")

    try:
        # Fetch Data safely
        try:
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            results_data = await results.next()
            data = results_data.get("result", [])[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            artist = data.get("channel", {}).get("name", "Unknown Artist")
            thumbnail = custom_thumb if custom_thumb else (data.get("thumbnails", [{}])[0].get("url") or get_random_fallback_img())
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            title, artist, duration, views = "Unsupported Title", "Unknown Artist", None, "Unknown Views"
            thumbnail = custom_thumb if custom_thumb else get_random_fallback_img()

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown Mins"

        # 2. CRASH FIX - Safe Image Open Handling
        success = await download_image(thumbnail, thumb_path)
        
        W, H = 1280, 720
        
        if success:
            try:
                raw_img = Image.open(thumb_path).convert("RGBA")
            except Exception:
                raw_img = Image.new("RGBA", (W, H), (22, 27, 34, 255))
        else:
            raw_img = Image.new("RGBA", (W, H), (22, 27, 34, 255))

        # --------------------------------------------------
        # 🎨 PIL DRAWING - TECHNICAL REPOSITORY DASHBOARD 
        # --------------------------------------------------
        bg = Image.new("RGBA", (W, H), (13, 17, 23, 255)) # Dark GitHub-style background

        draw = ImageDraw.Draw(bg)
        # Tech Grid styling
        for i in range(0, W, 40):
            draw.line((i, 0, i, H), fill=(255, 255, 255, 6), width=1)
        for i in range(0, H, 40):
            draw.line((0, i, W, i), fill=(255, 255, 255, 6), width=1)

        # Left side: Square Tech Album Art (Fixed 'ulta fulta' squash issue using ImageOps.fit)
        album_size = 460
        album_x, album_y = 80, 130
        
        album = ImageOps.fit(raw_img, (album_size, album_size), Image.LANCZOS)
        
        # Tech borders for album art
        draw.rectangle((album_x - 3, album_y - 3, album_x + album_size + 3, album_y + album_size + 3), outline=(88, 166, 255, 255), width=3)
        bracket_len = 30
        draw.line((album_x - 15, album_y - 15, album_x + bracket_len, album_y - 15), fill=(88, 166, 255, 255), width=5)
        draw.line((album_x - 15, album_y - 15, album_x - 15, album_y + bracket_len), fill=(88, 166, 255, 255), width=5)
        draw.line((album_x + album_size + 15, album_y + album_size + 15, album_x + album_size - bracket_len, album_y + album_size + 15), fill=(88, 166, 255, 255), width=5)
        draw.line((album_x + album_size + 15, album_y + album_size + 15, album_x + album_size + 15, album_y + album_size - bracket_len), fill=(88, 166, 255, 255), width=5)
        
        bg.paste(album, (album_x, album_y))

        # Right Side: Tech Dashboard Panel
        card_x, card_y = 600, 130
        card_w, card_h = 600, 460
        
        # Terminal Background
        draw.rectangle((card_x, card_y, card_x + card_w, card_y + card_h), fill=(22, 27, 34, 240), outline=(48, 54, 61, 255), width=2)
        # Terminal Header
        draw.rectangle((card_x, card_y, card_x + card_w, card_y + 40), fill=(48, 54, 61, 255))
        draw.ellipse((card_x + 15, card_y + 12, card_x + 30, card_y + 27), fill=(255, 95, 86, 255))
        draw.ellipse((card_x + 40, card_y + 12, card_x + 55, card_y + 27), fill=(255, 189, 46, 255))
        draw.ellipse((card_x + 65, card_y + 12, card_x + 80, card_y + 27), fill=(39, 201, 63, 255))
        
        tag_font = get_font(18, bold=True)
        title_font = get_font(42, bold=True)
        sub_font = get_font(24, bold=False)
        
        # Terminal Tab Title / Dev Credit Header
        draw.text((card_x + 100, card_y + 10), f"root@Ronakgupta321:~/{current_username}# play.sh", fill=(139, 148, 158, 255), font=tag_font)

        text_y = card_y + 70
        draw.text((card_x + 30, text_y), f"> STATUS: ACTIVE", fill=(39, 201, 63, 255), font=sub_font)
        
        text_y += 40
        title_lines = wrap_text_lines(title, title_font, card_w - 60, 2)
        for line in title_lines:
            draw.text((card_x + 30, text_y), f"{line}", fill=(201, 209, 217, 255), font=title_font)
            text_y += 55
            
        text_y += 20
        draw.text((card_x + 30, text_y), f"├── [Author] : {artist}", fill=(139, 148, 158, 255), font=sub_font)
        draw.text((card_x + 30, text_y + 40), f"└── [Views]  : {views}", fill=(139, 148, 158, 255), font=sub_font)

        # Progress bar section
        bar_y = card_y + 370
        draw.text((card_x + 30, bar_y - 35), f"[Duration] {duration_text}", fill=(88, 166, 255, 255), font=sub_font)
        
        # Tech / ASCII Progress line
        draw.rectangle((card_x + 30, bar_y, card_x + card_w - 30, bar_y + 12), outline=(139, 148, 158, 255), width=2)
        draw.rectangle((card_x + 34, bar_y + 4, card_x + 34 + int((card_w-68)*0.35), bar_y + 8), fill=(88, 166, 255, 255))

        # Save the final image
        final_img = bg.convert("RGB")
        final_img.save(cache_path, quality=95)
        return cache_path

    except Exception as e:
        return get_random_fallback_img()
    finally:
        # Cleanup Raw Image safely
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass
