import os
import re
import random
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from py_yt import VideosSearch

from PritiMusic import app
from config import YOUTUBE_IMG_URL
from PritiMusic.utils.database import clonebotdb 

CACHE_DIR = "cache"
ASSETS_DIR = "PritiMusic/assets"

os.makedirs(CACHE_DIR, exist_ok=True)

# ✅ Helper for Random Fallback Image
def get_random_fallback_img():
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

# --- HELPER FUNCTIONS FOR UI ---
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

def trim_to_width(text: str, font, max_width: int) -> str:
    text = str(text or "").strip()
    if not text:
        return "Unknown Title"
    if text_width(font, text) <= max_width:
        return text
    ellipsis = "..."
    for i in range(len(text), 0, -1):
        candidate = text[:i].rstrip() + ellipsis
        if text_width(font, candidate) <= max_width:
            return candidate
    return ellipsis

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
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if len(lines) == max_lines:
        lines[-1] = trim_to_width(lines[-1], font, max_width)
    return lines[:max_lines]

def make_progress_time(duration: str):
    if not duration or ":" not in str(duration):
        return "00:00", "03:00"
    return "00:00", str(duration)

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

def create_fallback_cover(size=(640, 640)):
    img = Image.new("RGBA", size, (25, 30, 45, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((40, 40, size[0] - 40, size[1] - 40), radius=35, fill=(40, 48, 72, 255))
    draw.ellipse((210, 170, 430, 390), fill=(110, 120, 160, 255))
    draw.rounded_rectangle((180, 380, 460, 560), radius=35, fill=(110, 120, 160, 255))
    return img

async def fetch_video_details(videoid: str):
    title, artist, duration, views = "Unknown Title", "Unknown Artist", "03:00", "0 views"
    try:
        results = VideosSearch(videoid, limit=10)
        search_result = await results.next()
        items = search_result.get("result") or []
        best_match = None
        for item in items:
            link = str(item.get("link", ""))
            item_id = str(item.get("id", ""))
            if f"watch?v={videoid}" in link or item_id == videoid:
                best_match = item
                break
        if not best_match and items:
            best_match = items[0]
        if best_match:
            title = best_match.get("title") or title
            artist = (best_match.get("channel") or {}).get("name") or artist
            duration = best_match.get("duration") or duration
            views = (best_match.get("viewCount") or {}).get("short") or views
    except Exception:
        pass
    return title, artist, duration, views

async def download_exact_video_thumbnail(videoid: str, raw_path: str) -> bool:
    thumb_candidates = [
        f"https://i.ytimg.com/vi/{videoid}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/sddefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/mqdefault.jpg",
        f"https://i.ytimg.com/vi/{videoid}/default.jpg",
    ]
    for thumb_url in thumb_candidates:
        ok = await download_image(thumb_url, raw_path)
        if ok and os.path.exists(raw_path):
            try:
                if os.path.getsize(raw_path) > 1024:
                    return True
            except Exception:
                return True
    return False

# ✅ MAIN FUNCTION (Clone Owner Database Logic Included)
async def get_thumb(videoid, user_id, client):
    # --- 1. Bot Name Fetch ---
    try:
        me = await client.get_me()
        bot_name = me.first_name.upper()
        bot_id = me.id
    except:
        bot_name = "MUSIC BOT"
        bot_id = 0

    # --- 2. Clone Owner Name Fetch ---
    owner_name = "OWNER" 
    try:
        # Check if the current bot is a clone in the database
        bot_data = await clonebotdb.find_one({"bot_id": bot_id})
        
        if bot_data:
            # Extract the ID of the user who created this clone
            clone_owner_id = bot_data.get("user_id") 
            try:
                owner_obj = await client.get_users(clone_owner_id)
                owner_name = owner_obj.first_name.upper()
            except:
                owner_name = "CLONE OWNER"
        else:
            owner_name = "MAIN BOT"
    except Exception as e:
        owner_name = "OWNER"

    # --- 3. Cache Check ---
    filename = os.path.join(CACHE_DIR, f"{videoid}_{bot_id}.png")
    if os.path.isfile(filename):
        return filename

    try:
        raw_path = os.path.join(CACHE_DIR, f"raw_{videoid}_{bot_id}.jpg")

        title, artist, duration, views = await fetch_video_details(videoid)
        downloaded = await download_exact_video_thumbnail(videoid, raw_path)

        W, H = 1280, 720

        if downloaded and os.path.exists(raw_path):
            try:
                source = Image.open(raw_path).convert("RGBA")
            except Exception:
                source = create_fallback_cover()
        else:
            source = create_fallback_cover()

        # Background Blur & Contrast
        bg = source.resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=45))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        bg = ImageEnhance.Contrast(bg).enhance(1.08)

        # Dark overlay
        dark = Image.new("RGBA", (W, H), (10, 12, 20, 110))
        bg = Image.alpha_composite(bg, dark)

        # Glow effect
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse((40, 60, 420, 430), fill=(70, 110, 255, 55))
        gdraw.ellipse((900, 70, 1260, 430), fill=(255, 80, 150, 45))
        gdraw.ellipse((780, 400, 1180, 760), fill=(255, 180, 40, 35))
        glow = glow.filter(ImageFilter.GaussianBlur(75))
        bg = Image.alpha_composite(bg, glow)

        # Fonts
        title_font = get_font(48, bold=True)
        artist_font = get_font(28, bold=False)
        meta_font = get_font(24, bold=False)
        time_font = get_font(22, bold=True)
        badge_font = get_font(22, bold=True)
        footer_font = get_font(20, bold=False)
        top_font = get_font(30, bold=True)

        draw = ImageDraw.Draw(bg)

        # --- Top Left (Clone Owner Name) & Top Right (Bot Name) ---
        draw.text((35, 25), f"OWNER: {owner_name}", fill=(0, 255, 255, 255), font=top_font, stroke_width=2, stroke_fill="black")
        bot_w = text_width(top_font, bot_name)
        draw.text((W - bot_w - 35, 25), bot_name, fill=(255, 255, 0, 255), font=top_font, stroke_width=2, stroke_fill="black")

        # Album art (Rounded)
        cover_w, cover_h = 470, 470
        cover_x, cover_y = 90, (H - cover_h) // 2

        album = source.resize((cover_w, cover_h), Image.LANCZOS)
        mask = Image.new("L", (cover_w, cover_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, cover_w, cover_h), radius=38, fill=255)

        shadow = Image.new("RGBA", (cover_w + 40, cover_h + 40), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(shadow)
        sdraw.rounded_rectangle((20, 20, cover_w + 20, cover_h + 20), radius=42, fill=(0, 0, 0, 165))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18))
        bg.paste(shadow, (cover_x - 20, cover_y - 20), shadow)

        bg.paste(album, (cover_x, cover_y), mask)

        border = Image.new("RGBA", (cover_w, cover_h), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(border)
        bdraw.rounded_rectangle((0, 0, cover_w - 1, cover_h - 1), radius=38, outline=(255, 255, 255, 235), width=6)
        bg.paste(border, (cover_x, cover_y), border)

        # Right Translucent Panel
        panel_x1 = 620
        panel_y1 = cover_y
        panel_x2 = W - 60
        panel_y2 = cover_y + cover_h

        panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(panel)
        pdraw.rounded_rectangle((panel_x1, panel_y1, panel_x2, panel_y2), radius=34, fill=(255, 255, 255, 22), outline=(255, 255, 255, 32), width=2)
        bg = Image.alpha_composite(bg, panel)
        draw = ImageDraw.Draw(bg)

        # Badge
        badge_text = f"Now Playing • {bot_name}"
        badge_w = text_width(badge_font, badge_text) + 36
        badge_h = 42
        badge_x = panel_x1 + 36
        badge_y = panel_y1 + 28

        draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), radius=18, fill=(90, 120, 255, 85))
        draw.text((badge_x + 18, badge_y + 9), badge_text, font=badge_font, fill=(255, 255, 255, 240))

        # Title Text Wrap
        title_max_width = panel_x2 - panel_x1 - 72
        title_lines = wrap_text_lines(title, title_font, title_max_width, max_lines=2)

        title_y = panel_y1 + 95
        for idx, line in enumerate(title_lines):
            draw.text((panel_x1 + 36, title_y + (idx * 58)), line, font=title_font, fill=(255, 255, 255, 255))

        # Artist Info
        artist_text = trim_to_width(f"By {artist}", artist_font, title_max_width)
        draw.text((panel_x1 + 36, panel_y1 + 225), artist_text, font=artist_font, fill=(210, 215, 225, 235))

        # Views Info
        views_text = trim_to_width(f"Views • {views}", meta_font, title_max_width)
        draw.text((panel_x1 + 36, panel_y1 + 270), views_text, font=meta_font, fill=(170, 180, 195, 235))

        # Progress bar
        current_time, total_time = make_progress_time(duration)
        bar_x = panel_x1 + 36
        bar_y = panel_y1 + 360
        bar_w = panel_x2 - panel_x1 - 72
        bar_h = 12
        progress = 0.40

        draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=12, fill=(255, 255, 255, 70))
        fill_w = int(bar_w * progress)
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), radius=12, fill=(0, 200, 255, 255))

        knob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        kdraw = ImageDraw.Draw(knob)
        knob_x = bar_x + fill_w
        knob_y = bar_y + bar_h // 2

        kdraw.ellipse((knob_x - 16, knob_y - 16, knob_x + 16, knob_y + 16), fill=(255, 255, 255, 255))
        knob = knob.filter(ImageFilter.GaussianBlur(1))
        bg = Image.alpha_composite(bg, knob)
        draw = ImageDraw.Draw(bg)

        draw.text((bar_x, bar_y + 28), current_time, font=time_font, fill=(240, 240, 245, 235))
        total_bbox = draw.textbbox((0, 0), total_time, font=time_font)
        total_w = total_bbox[2] - total_bbox[0]
        draw.text((bar_x + bar_w - total_w, bar_y + 28), total_time, font=time_font, fill=(240, 240, 245, 235))

        # Footer
        footer_text = "High Quality Streaming Experience"
        draw.text((panel_x1 + 36, panel_y2 - 42), footer_text, font=footer_font, fill=(160, 175, 190, 220))

        # Save Final Image
        final_img = bg.convert("RGB")
        final_img.save(filename, quality=95)

        # Cleanup raw image to save disk space
        try:
            if os.path.exists(raw_path):
                os.remove(raw_path)
        except Exception:
            pass

        return filename

    except Exception as e:
        print(f"Thumbnail Generation Error: {e}")
        return get_random_fallback_img()
