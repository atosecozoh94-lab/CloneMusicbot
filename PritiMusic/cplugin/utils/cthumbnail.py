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

# Helper: Text ki exact width nikalne ke liye
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

async def get_thumb(videoid: str, *args, **kwargs) -> str:
    # Clone bot ko alag rakhne ke liye
    cache_prefix = str(args[0]) if args else kwargs.get("bot_username", "main")
    
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{cache_prefix}_v4_first_img.png")
    if os.path.exists(cache_path):
        return cache_path

    # YouTube video data fetch karne ke liye (Gaane ka hi thumbnail chahiye)
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        result_items = results_data.get("result", [])
        if not result_items:
            raise ValueError("No results found.")
        data = result_items[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        
        # YouTube ka actual thumbnail nikal rahe hain
        song_thumbnail = data.get("thumbnails", [{}])[0].get("url")
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
    except Exception:
        title, song_thumbnail, duration, views = "Unsupported Title", None, None, "Unknown Views"

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "00:00"

    # Agar YouTube ka thumbnail nahi mila toh Config ya Clone ke file par fallback karega
    clone_custom_thumb = kwargs.get("thumbnail") or kwargs.get("thumb_url")
    final_target = song_thumbnail if song_thumbnail else (clone_custom_thumb or YOUTUBE_IMG_URL)

    # Clone Bot Local File Fix: Check if it's already a downloaded/local file
    is_local_file = False
    if final_target and os.path.isfile(str(final_target)):
        is_local_file = True
        raw_image_path = final_target
    else:
        unique_id = f"{int(time.time())}_{random.randint(100, 999)}"
        raw_image_path = os.path.join(CACHE_DIR, f"raw_{cache_prefix}_{videoid}_{unique_id}.png")

    # Sirf tab download karega jab wo local file na ho (Clone file error bachega)
    if not is_local_file:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(final_target) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(raw_image_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            if not os.path.exists(raw_image_path):
                return YOUTUBE_IMG_URL

    try:
        # Layout Coordinates Calculation (Exactly like 1st Image)
        W, H = 1280, 720
        PANEL_W, PANEL_H = 763, 545
        PANEL_X = (W - PANEL_W) // 2
        PANEL_Y = 88
        
        THUMB_W, THUMB_H = 542, 273
        THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
        THUMB_Y = PANEL_Y + 36
        
        # 🔥 FIX: Sab kuch thumbnail ke ekdum LEFT me align kiya hai (1st image ki tarah)
        TITLE_X = THUMB_X
        META_X = THUMB_X
        TITLE_Y = THUMB_Y + THUMB_H + 20
        META_Y = TITLE_Y + 45
        
        # Progress bar ab thumbnail ki puri chaudaai (width) lega
        BAR_X = THUMB_X
        BAR_Y = META_Y + 50
        BAR_TOTAL_LEN = THUMB_W # Exact thumbnail ke barabar
        BAR_RED_LEN = int(BAR_TOTAL_LEN * 0.35) # 35% bhara hua dikhega

        # Base Image & Background Blur
        try:
            raw_img = Image.open(raw_image_path).convert("RGBA")
        except Exception:
            raw_img = Image.new("RGBA", (W, H), (20, 20, 20, 255))

        base = ImageOps.fit(raw_img, (W, H), Image.LANCZOS)
        bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

        # Frosted glass panel
        panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
        overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, 170)) # 170 Transparency
        frosted = Image.alpha_composite(panel_area, overlay)
        mask = Image.new("L", (PANEL_W, PANEL_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
        bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

        draw = ImageDraw.Draw(bg)
        
        # 🔥 Fonts: 1st image ki tarah BADA aur BOLD font size (36)
        try:
            title_font = ImageFont.truetype("SHUKLAMUSIC/assets/assets/font2.ttf", 36)
            regular_font = ImageFont.truetype("SHUKLAMUSIC/assets/assets/font.ttf", 20)
        except OSError:
            try:
                title_font = ImageFont.truetype("arial.ttf", 36)
                regular_font = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                title_font = regular_font = ImageFont.load_default()

        # Inner Thumbnail (Bina pichke set hoga)
        thumb = ImageOps.fit(raw_img, (THUMB_W, THUMB_H), Image.LANCZOS)
        tmask = Image.new("L", thumb.size, 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
        bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

        # Text Drawing (Left aligned with thumbnail)
        MAX_TITLE_WIDTH = THUMB_W
        safe_title = trim_to_width(title, title_font, MAX_TITLE_WIDTH)
        
        draw.text((TITLE_X, TITLE_Y), safe_title, fill="black", font=title_font)
        draw.text((META_X, META_Y), f"YouTube | {views}", fill=(40, 40, 40, 255), font=regular_font)

        # Progress bar (Exact size of 1st image)
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
        draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
        draw.ellipse([(BAR_X + BAR_RED_LEN - 8, BAR_Y - 8), (BAR_X + BAR_RED_LEN + 8, BAR_Y + 8)], fill="red")

        # Time Texts (Left & Right perfectly aligned)
        draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
        end_text = "Live" if is_live else duration_text
        end_w = get_text_width(regular_font, end_text)
        draw.text((BAR_X + BAR_TOTAL_LEN - end_w, BAR_Y + 15), end_text, fill="red" if is_live else "black", font=regular_font)

        # Icons (Centered)
        ICONS_W, ICONS_H = 415, 45
        ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
        ICONS_Y = BAR_Y + 55
        
        icons_path = "SHUKLAMUSIC/assets/assets/play_icons.png"
        if os.path.isfile(icons_path):
            ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
            r, g, b, a = ic.split()
            black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
            bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

        # Final save
        bg.convert("RGB").save(cache_path, quality=95)
        return cache_path

    finally:
        # Cleanup: Local clone file hogi toh wo delete nahi hogi
        if not is_local_file and os.path.exists(raw_image_path):
            try:
                os.remove(raw_image_path)
            except OSError:
                pass
