import os
import re
import random
import aiofiles
import aiohttp
import time

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
# 🟢 OLD THUMBNAIL LOGIC (STRICTLY FOR CLONE BOTS)
# ==========================================
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

def trim_to_width_old(text: str, font, max_width: int) -> str:
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
        lines[-1] = trim_to_width_old(lines[-1], font, max_width)
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

async def get_thumb_old(videoid: str, player_username: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{player_username}_old.png")
    # Agar pehle se bana hua hai, toh direct return karo
    if os.path.isfile(cache_path):
        return cache_path

    # 🔥 FIX: Unique temp file name banaya taaki conflict na ho
    unique_id = f"{videoid}_{int(time.time())}_{random.randint(100, 999)}"
    raw_path = os.path.join(CACHE_DIR, f"raw_{unique_id}.jpg")
    
    try:
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

        bg = source.resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=45))
        bg = ImageEnhance.Brightness(bg).enhance(0.32)
        bg = ImageEnhance.Contrast(bg).enhance(1.08)

        dark = Image.new("RGBA", (W, H), (10, 12, 20, 110))
        bg = Image.alpha_composite(bg, dark)

        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse((40, 60, 420, 430), fill=(70, 110, 255, 55))
        gdraw.ellipse((900, 70, 1260, 430), fill=(255, 80, 150, 45))
        glow = glow.filter(ImageFilter.GaussianBlur(75))
        bg = Image.alpha_composite(bg, glow)

        draw = ImageDraw.Draw(bg)
        title_font = get_font(48, bold=True)
        artist_font = get_font(28, bold=False)
        meta_font = get_font(24, bold=False)
        badge_font = get_font(22, bold=True)
        
        cover_w, cover_h = 470, 470
        cover_x, cover_y = 90, (H - cover_h) // 2
        album = source.resize((cover_w, cover_h), Image.LANCZOS)
        mask = Image.new("L", (cover_w, cover_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, cover_w, cover_h), radius=38, fill=255)
        bg.paste(album, (cover_x, cover_y), mask)

        panel_x1, panel_y1, panel_x2, panel_y2 = 620, cover_y, W - 60, cover_y + cover_h
        panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(panel).rounded_rectangle((panel_x1, panel_y1, panel_x2, panel_y2), radius=34, fill=(255, 255, 255, 22))
        bg = Image.alpha_composite(bg, panel)
        draw = ImageDraw.Draw(bg)

        badge_text = f"Now Playing • @{player_username}"
        draw.text((panel_x1 + 36 + 18, panel_y1 + 28 + 9), badge_text, font=badge_font, fill=(255, 255, 255, 240))

        title_lines = wrap_text_lines(title, title_font, panel_x2 - panel_x1 - 72, max_lines=2)
        for idx, line in enumerate(title_lines):
            draw.text((panel_x1 + 36, panel_y1 + 95 + (idx * 58)), line, font=title_font, fill=(255, 255, 255, 255))
        
        draw.text((panel_x1 + 36, panel_y1 + 225), f"By {artist}", font=artist_font, fill=(210, 215, 225, 235))
        draw.text((panel_x1 + 36, panel_y1 + 270), f"Views • {views}", font=meta_font, fill=(170, 180, 195, 235))

        final_img = bg.convert("RGB")
        final_img.save(cache_path, quality=95)
        return cache_path
    except Exception:
        return get_random_fallback_img()
    finally:
        # 🔥 FIX: Hamesha temp file delete karega
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
            except:
                pass


# ==========================================
# 🔴 NEW THUMBNAIL LOGIC (STRICTLY FOR MAIN BOT)
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

def trim_to_width_new(text: str, font, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

async def get_thumb_new(videoid: str, player_username: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{player_username}_new.png")
    # Agar pehle se bana hua hai, toh direct return karo
    if os.path.exists(cache_path):
        return cache_path

    # 🔥 FIX: Unique temp file naam taaki clone aur main aapas me file overwrite na karein
    unique_id = f"{videoid}_{int(time.time())}_{random.randint(100, 999)}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_new_{unique_id}.png")

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

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            return get_random_fallback_img()

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

        draw.text((TITLE_X, TITLE_Y), trim_to_width_new(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
        draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
        draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
        draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

        draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
        end_text = "Live" if is_live else duration_text
        draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

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
        # 🔥 FIX: Temp image file ko safely clean up karna
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass


# ==========================================
# 🚀 MAIN ROUTER (Automatically decides logic)
# ==========================================
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    """
    Ye function decide karega kaunsa thumbnail banana hai.
    Main bot -> Naya Thumbnail
    Clone bot -> Purana Thumbnail
    Flexible args ki wajah se chahe 1, 2, ya 3 arguments aayein, yeh function error nahi dega.
    """
    # Main bot ka actual username nikal rahe hain
    main_bot_username = getattr(app, "username", "MusicBot")
    
    # Argument parsing (*args aur **kwargs dono check karenge)
    player_username = None
    if len(args) > 0:
        player_username = str(args[0])
    elif "player_username" in kwargs:
        player_username = str(kwargs["player_username"])
        
    # Agar username "None" string me aya ho ya blank ho
    if not player_username or player_username == "None":
        current_username = main_bot_username
    else:
        current_username = player_username
    
    # Logic: Agar request bhejnewala Clone hai, toh old thumbnail return karo
    if current_username != main_bot_username:
        return await get_thumb_old(videoid, current_username)
        
    # Agar request bhejnewala Main bot hai, toh new thumbnail return karo
    else:
        return await get_thumb_new(videoid, current_username)
