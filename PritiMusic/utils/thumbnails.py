import os
import re
import random
import time
import aiofiles
import aiohttp

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch

# ✅ Bot imports (Make sure these exist in your repo)
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
        return bbox[2] - bbox[0] if bbox else 10

def wrap_text_lines(text: str, font, max_width: int, max_lines: int = 2):
    words = str(text or "Unknown Title").split()
    lines, current = [], ""
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
    
    # Truncate with ellipsis if it's too long
    if len(lines) == max_lines and text_width(font, lines[-1]) > max_width:
        last_line = lines[-1]
        while text_width(font, last_line + "...") > max_width and len(last_line) > 0:
            last_line = last_line[:-1]
        lines[-1] = last_line.strip() + "..."
        
    return lines[:max_lines]

async def download_image(url: str, dest: str) -> bool:
    try:
        if not url or not url.startswith("http"):
            return False
        timeout = aiohttp.ClientTimeout(total=10)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    async with aiofiles.open(dest, "wb") as f:
                        await f.write(data)
                    return True
        return False
    except Exception:
        return False

# Helper for rounded rectangles (if standard PIL lacks it)
def add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im


# ==========================================
# 💎 PRO LEVEL TECHNICAL THUMBNAIL LOGIC
# ==========================================
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    # 1. Identity Check
    main_bot_username = getattr(app, "username", "MusicBot")
    player_username = args[0] if len(args) > 0 else kwargs.get("bot_username") or kwargs.get("player_username")
    current_username = player_username if player_username and str(player_username) != "None" else main_bot_username

    custom_thumb = kwargs.get("thumb_url") or kwargs.get("image_url") or kwargs.get("thumbnail")
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{current_username}_tech_premium.png")
    
    if os.path.exists(cache_path):
        return cache_path

    unique_id = f"{videoid}_{current_username}_{int(time.time())}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_premium_{unique_id}.png")

    try:
        # Fetch Data
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
        duration_text = "Live Stream" if is_live else f"{duration} Mins"

        # 2. Download Image and open safely
        success = await download_image(thumbnail, thumb_path)
        W, H = 1280, 720
        
        try:
            raw_img = Image.open(thumb_path).convert("RGBA") if success else Image.new("RGBA", (W, H), (22, 27, 34, 255))
        except Exception:
            raw_img = Image.new("RGBA", (W, H), (22, 27, 34, 255))

        # --------------------------------------------------
        # 🎨 PIL DRAWING - PRO DEV DASHBOARD
        # --------------------------------------------------
        # Create Blurred Background for Premium Look
        bg = raw_img.resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
        
        # Add dark overlay over the blurred background
        overlay = Image.new("RGBA", (W, H), (13, 17, 23, 180)) # Dark translucent GitHub theme
        bg = Image.alpha_composite(bg.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(bg)

        # Draw Tech Grid
        for i in range(0, W, 50):
            draw.line((i, 0, i, H), fill=(255, 255, 255, 12), width=1)
        for i in range(0, H, 50):
            draw.line((0, i, W, i), fill=(255, 255, 255, 12), width=1)

        # ---- LEFT: SQUARE ALBUM ART ----
        album_size = 460
        album_x, album_y = 80, 130
        
        # Resize, crop to center, and round corners
        album = ImageOps.fit(raw_img, (album_size, album_size), Image.LANCZOS)
        album = add_corners(album, rad=25)
        
        # Tech Box brackets around Album Art
        bracket_len, b_w = 40, 5
        b_color = (88, 166, 255, 255) # GitHub Blue
        
        draw.line((album_x - 15, album_y - 15, album_x + bracket_len, album_y - 15), fill=b_color, width=b_w)
        draw.line((album_x - 15, album_y - 15, album_x - 15, album_y + bracket_len), fill=b_color, width=b_w)
        draw.line((album_x + album_size + 15, album_y + album_size + 15, album_x + album_size - bracket_len, album_y + album_size + 15), fill=b_color, width=b_w)
        draw.line((album_x + album_size + 15, album_y + album_size + 15, album_x + album_size + 15, album_y + album_size - bracket_len), fill=b_color, width=b_w)
        
        bg.paste(album, (album_x, album_y), album)

        # ---- RIGHT: TERMINAL DASHBOARD PANEL ----
        card_x, card_y = 600, 130
        card_w, card_h = 600, 460
        
        # Terminal Background with border
        draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=15, fill=(22, 27, 34, 240), outline=(48, 54, 61, 255), width=3)
        # Terminal Header
        draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + 45), radius=15, fill=(48, 54, 61, 255))
        # Mask bottom corners of header to keep it flush with box
        draw.rectangle((card_x, card_y + 25, card_x + card_w, card_y + 45), fill=(48, 54, 61, 255))
        
        # MacOS style window buttons
        draw.ellipse((card_x + 20, card_y + 15, card_x + 35, card_y + 30), fill=(255, 95, 86, 255))
        draw.ellipse((card_x + 45, card_y + 15, card_x + 60, card_y + 30), fill=(255, 189, 46, 255))
        draw.ellipse((card_x + 70, card_y + 15, card_x + 85, card_y + 30), fill=(39, 201, 63, 255))
        
        # Fonts
        tag_font = get_font(20, bold=True)
        title_font = get_font(44, bold=True)
        sub_font = get_font(26, bold=False)
        
        # Top Terminal Text
        draw.text((card_x + 110, card_y + 10), f"root@{current_username}:~# ./play_music.sh", fill=(139, 148, 158, 255), font=tag_font)

        text_y = card_y + 80
        draw.text((card_x + 35, text_y), f"> STATUS: STREAMING SECURELY...", fill=(39, 201, 63, 255), font=sub_font)
        
        # Title Wrap
        text_y += 50
        title_lines = wrap_text_lines(title, title_font, card_w - 70, 2)
        for line in title_lines:
            draw.text((card_x + 35, text_y), f"{line}", fill=(201, 209, 217, 255), font=title_font)
            text_y += 55
            
        # Metadata
        text_y += 30
        draw.text((card_x + 35, text_y), f"├── [Author] : {artist}", fill=(139, 148, 158, 255), font=sub_font)
        draw.text((card_x + 35, text_y + 40), f"└── [Views]  : {views}", fill=(139, 148, 158, 255), font=sub_font)

        # Progress Bar Area
        bar_y = card_y + 380
        draw.text((card_x + 35, bar_y - 40), f"[Processing Timeline] : {duration_text}", fill=(88, 166, 255, 255), font=sub_font)
        
        # Modern Progress Bar Background & Fill
        draw.rounded_rectangle((card_x + 35, bar_y, card_x + card_w - 35, bar_y + 15), radius=7, fill=(13, 17, 23, 255), outline=(139, 148, 158, 255), width=2)
        
        # Logic to simulate random progress or set to 35%
        fill_width = int((card_w - 70) * 0.35) 
        if is_live:
            fill_width = int((card_w - 70) * 0.98) # Full for live
        
        draw.rounded_rectangle((card_x + 38, bar_y + 3, card_x + 35 + fill_width, bar_y + 12), radius=5, fill=(88, 166, 255, 255))

        # Save Final Image
        final_img = bg.convert("RGB")
        final_img.save(cache_path, quality=95)
        return cache_path

    except Exception as e:
        print(f"Thumbnail Error: {e}")
        return get_random_fallback_img()
    finally:
        # Cleanup
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass

