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
            return ImageFont.truetype("arial.ttf", size) # Fallback to standard arial
        except Exception:
            return ImageFont.load_default()

# 🔥 Clone Bot Premium Thumbnail Logic
async def get_thumb(videoid: str, *args, **kwargs) -> str:
    # Clone bot cache handling via args/kwargs
    cache_prefix = str(args[0]) if args else kwargs.get("bot_username", "main_bot")
    custom_thumb = kwargs.get("thumb_url") or kwargs.get("thumbnail")
    
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{cache_prefix}_v5_premium.png")
    if os.path.exists(cache_path):
        return cache_path

    # Unique temp file
    unique_id = f"{int(time.time())}_{random.randint(100, 999)}"
    thumb_path = os.path.join(CACHE_DIR, f"raw_{cache_prefix}_{videoid}_{unique_id}.png")

    # Fetch Data from YouTube
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        data = results_data.get("result", [])[0]
        title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        
        # Priority to Clone bot's custom thumbnail, else YouTube thumbnail
        if custom_thumb:
            thumbnail = custom_thumb
        else:
            thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
            
        duration = data.get("duration")
        views = data.get("viewCount", {}).get("short", "Unknown Views")
        channel_name = data.get("channel", {}).get("name", "YouTube")
    except Exception:
        title, thumbnail, duration, views, channel_name = "Unsupported Title", custom_thumb or YOUTUBE_IMG_URL, None, "Unknown Views", "YouTube"

    is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration or "00:00"

    # Download raw image
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except Exception:
        pass # Use fallback mechanism later if download fails

    try:
        # 1. Base Setup (Canvas 1280x720)
        W, H = 1280, 720
        try:
            raw_img = Image.open(thumb_path).convert("RGBA")
            base = ImageOps.fit(raw_img, (W, H), Image.LANCZOS)
        except Exception:
            base = Image.new("RGBA", (W, H), (15, 15, 20, 255))
            raw_img = base

        # 2. Background Dark & Blur
        bg = base.filter(ImageFilter.GaussianBlur(30))
        bg = ImageEnhance.Brightness(bg).enhance(0.4) # Darken background

        # 3. Premium Glass Card (Panel)
        PW, PH = 900, 600
        PX, PY = (W - PW) // 2, (H - PH) // 2
        
        card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(card)
        # Semi-transparent dark glass
        cdraw.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=40, fill=(20, 25, 30, 160))
        # Subtle border
        cdraw.rounded_rectangle((PX, PY, PX + PW, PY + PH), radius=40, outline=(255, 255, 255, 30), width=2)
        bg = Image.alpha_composite(bg, card)

        # 4. Inner Thumbnail Image (Fit exactly, no stretching)
        TW, TH = 760, 360
        TX, TY = PX + (PW - TW) // 2, PY + 40
        
        inner_thumb = ImageOps.fit(raw_img, (TW, TH), Image.LANCZOS)
        tmask = Image.new("L", (TW, TH), 0)
        ImageDraw.Draw(tmask).rounded_rectangle((0, 0, TW, TH), 25, fill=255)
        bg.paste(inner_thumb, (TX, TY), tmask)

        # 5. Fonts (Bada Size)
        # Update paths if your assets folder structure is different!
        title_font = load_font("SHUKLAMUSIC/assets/assets/font2.ttf", 46) # 🔥 Bada title
        meta_font = load_font("SHUKLAMUSIC/assets/assets/font.ttf", 26)   # 🔥 Bada meta
        time_font = load_font("SHUKLAMUSIC/assets/assets/font.ttf", 22)

        draw = ImageDraw.Draw(bg)

        # 6. Center Aligned Text
        MAX_T_WIDTH = 800
        safe_title = trim_to_width(title, title_font, MAX_T_WIDTH)
        title_w = get_text_width(title_font, safe_title)
        
        TITLE_X = PX + (PW - title_w) // 2
        TITLE_Y = TY + TH + 35
        # Draw Title (White)
        draw.text((TITLE_X, TITLE_Y), safe_title, fill=(255, 255, 255, 255), font=title_font)

        # Draw Meta (Gray)
        meta_text = f"👤 {channel_name}   |   👁 {views}"
        meta_w = get_text_width(meta_font, meta_text)
        META_X = PX + (PW - meta_w) // 2
        META_Y = TITLE_Y + 65
        draw.text((META_X, META_Y), meta_text, fill=(180, 190, 200, 255), font=meta_font)

        # 7. Progress Bar (YouTube Style)
        BAR_W = 660
        BAR_X = PX + (PW - BAR_W) // 2
        BAR_Y = META_Y + 60
        
        filled_len = int(BAR_W * 0.35) # Visually 35% filled
        
        # Empty Bar (Gray)
        draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_W, BAR_Y)], fill=(255, 255, 255, 60), width=8)
        # Filled Bar (Red)
        draw.line([(BAR_X, BAR_Y), (BAR_X + filled_len, BAR_Y)], fill=(255, 0, 50, 255), width=8)
        # Progress Dot (Knob)
        draw.ellipse([(BAR_X + filled_len - 10, BAR_Y - 10), (BAR_X + filled_len + 10, BAR_Y + 10)], fill=(255, 255, 255, 255))

        # Time Texts
        draw.text((BAR_X, BAR_Y + 20), "00:00", fill=(200, 200, 200, 255), font=time_font)
        dur_w = get_text_width(time_font, duration_text)
        dur_color = (255, 50, 50, 255) if is_live else (200, 200, 200, 255)
        draw.text((BAR_X + BAR_W - dur_w, BAR_Y + 20), duration_text, fill=dur_color, font=time_font)

        # 8. Add Icons if exist
        icons_path = "SHUKLAMUSIC/assets/assets/play_icons.png"
        if os.path.isfile(icons_path):
            try:
                # Resize keeping aspect ratio
                ic = Image.open(icons_path).convert("RGBA")
                ic_ratio = ic.width / ic.height
                IC_H = 40
                IC_W = int(IC_H * ic_ratio)
                ic = ic.resize((IC_W, IC_H))
                
                # Make white (since background is dark now)
                r, g, b, a = ic.split()
                white_ic = Image.merge("RGBA", (r.point(lambda *_: 255), g.point(lambda *_: 255), b.point(lambda *_: 255), a))
                
                # Center it right below the progress bar logic
                IC_X = PX + (PW - IC_W) // 2
                IC_Y = BAR_Y - 35 # Placed in the center above the bar
                bg.paste(white_ic, (IC_X, IC_Y), white_ic)
            except Exception:
                pass

        # Final Save
        bg.convert("RGB").save(cache_path, quality=95)
        return cache_path

    finally:
        # File Cleanup
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass
