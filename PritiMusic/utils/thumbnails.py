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
# 💎 PREMIUM THUMBNAIL LOGIC
# ==========================================
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    # Handle Arguments Flexibly
    main_bot_username = getattr(app, "username", "MusicBot")
    player_username = None
    if len(args) > 0:
        player_username = str(args[0])
    elif "player_username" in kwargs:
        player_username = str(kwargs["player_username"])
        
    current_username = player_username if (player_username and player_username != "None") else main_bot_username

    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{current_username}_premium.png")
    if os.path.exists(cache_path):
        return cache_path

    unique_id = f"{videoid}_{int(time.time())}_{random.randint(100, 999)}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_premium_{unique_id}.png")

    try:
        # Fetch Data
        results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        try:
            results_data = await results.next()
            data = results_data.get("result", [])[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            artist = data.get("channel", {}).get("name", "Unknown Artist")
            thumbnail = data.get("thumbnails", [{}])[0].get("url") or get_random_fallback_img()
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            title, artist, thumbnail, duration, views = "Unsupported Title", "Unknown Artist", get_random_fallback_img(), None, "Unknown Views"

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown Mins"

        # Download raw thumbnail
        await download_image(thumbnail, thumb_path)

        # --------------------------------------------------
        # 🎨 PIL DRAWING - LUXURY DESIGN
        # --------------------------------------------------
        W, H = 1280, 720
        
        try:
            base = Image.open(thumb_path).resize((W, H)).convert("RGBA")
        except Exception:
            base = Image.new("RGBA", (W, H), (20, 20, 30, 255))

        # 1. Background Blur & Dark Gradient Overlay
        bg = base.filter(ImageFilter.GaussianBlur(40))
        bg = ImageEnhance.Brightness(bg).enhance(0.4) # Darken base
        
        dark_overlay = Image.new("RGBA", (W, H), (10, 12, 22, 190)) # Deep navy/black tint
        bg = Image.alpha_composite(bg, dark_overlay)

        # 2. Subtle Neon Accents (Glow)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        # Top-Left Cyan Glow
        gdraw.ellipse((-150, -150, 450, 450), fill=(0, 220, 255, 60))
        # Bottom-Right Purple Glow
        gdraw.ellipse((850, 350, 1450, 950), fill=(160, 40, 255, 50))
        glow = glow.filter(ImageFilter.GaussianBlur(90))
        bg = Image.alpha_composite(bg, glow)

        # 3. Left Album Image with Shadow & Gold Border
        album_size = 480
        album_x, album_y = 60, 110
        
        # Shadow
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        sdraw.rounded_rectangle((album_x + 12, album_y + 18, album_x + album_size + 12, album_y + album_size + 18), radius=40, fill=(0, 0, 0, 160))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        bg = Image.alpha_composite(bg, shadow)
        
        # Image Masking & Border
        album = base.resize((album_size, album_size), Image.LANCZOS)
        mask = Image.new("L", (album_size, album_size), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, album_size, album_size), radius=35, fill=255)
        
        album_border = Image.new("RGBA", (album_size, album_size), (0, 0, 0, 0))
        ImageDraw.Draw(album_border).rounded_rectangle((0, 0, album_size, album_size), radius=35, outline=(220, 180, 110, 255), width=3) # Luxury Gold/Cream
        album.paste(album_border, (0, 0), album_border)
        bg.paste(album, (album_x, album_y), mask)

        # 4. Right Side "Glassmorphism" Card
        card_x, card_y = 580, 110
        card_w, card_h = 640, 480
        
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(card)
        # Frosted Glass Base
        cdraw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=35, fill=(255, 255, 255, 18))
        # Glass Border
        cdraw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=35, outline=(255, 255, 255, 45), width=2)
        bg = Image.alpha_composite(bg, card)

        # 5. Typography & Text Drawing
        draw = ImageDraw.Draw(bg)
        tag_font = get_font(22, bold=True)
        title_font = get_font(48, bold=True)
        sub_font = get_font(26, bold=False)
        time_font = get_font(22, bold=False)
        tagline_font = get_font(20, bold=False)

        # Badge: Now Playing
        draw.text((card_x + 45, card_y + 45), f"NOW PLAYING  •  @{current_username}", fill=(0, 230, 255, 255), font=tag_font)

        # Title (Wrapped)
        title_lines = wrap_text_lines(title, title_font, card_w - 90, 2)
        text_y = card_y + 100
        for line in title_lines:
            draw.text((card_x + 45, text_y), line, fill=(255, 255, 255, 255), font=title_font)
            text_y += 65

        # Meta: Artist & Views
        meta_y = card_y + 260
        draw.text((card_x + 45, meta_y), f"👤 By: {artist}", fill=(200, 210, 225, 240), font=sub_font)
        draw.text((card_x + 45, meta_y + 40), f"👁 Views: {views}", fill=(160, 175, 195, 220), font=sub_font)

        # 6. Premium Progress Bar
        bar_x = card_x + 45
        bar_y = card_y + 380
        bar_w = card_w - 90
        fill_ratio = 0.35 # 35% filled visually
        progress_px = int(bar_w * fill_ratio)
        
        # Empty Track (Gray)
        draw.line((bar_x, bar_y, bar_x + bar_w, bar_y), fill=(255, 255, 255, 50), width=6)
        # Filled Track (Cyan)
        draw.line((bar_x, bar_y, bar_x + progress_px, bar_y), fill=(0, 230, 255, 255), width=6)
        
        # Glowing Knob
        knob_cx, knob_cy = bar_x + progress_px, bar_y
        # Knob outer glow
        draw.ellipse((knob_cx - 12, knob_cy - 12, knob_cx + 12, knob_cy + 12), fill=(0, 230, 255, 100))
        # Knob inner circle
        draw.ellipse((knob_cx - 6, knob_cy - 6, knob_cx + 6, knob_cy + 6), fill=(255, 255, 255, 255))

        # Time Labels
        draw.text((bar_x, bar_y + 15), "00:00", fill=(180, 190, 200, 255), font=time_font)
        duration_w = text_width(time_font, duration_text)
        draw.text((bar_x + bar_w - duration_w, bar_y + 15), duration_text, fill=(0, 230, 255, 255) if is_live else (180, 190, 200, 255), font=time_font)

        # 7. Bottom Luxury Tagline
        tagline = "✨ High Quality Streaming Experience"
        tagline_w = text_width(tagline_font, tagline)
        draw.text(((W - tagline_w) // 2, 670), tagline, fill=(150, 160, 180, 200), font=tagline_font)

        # Save the final masterpiece
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
