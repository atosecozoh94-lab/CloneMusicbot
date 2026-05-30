import os
import re
import random
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from py_yt import VideosSearch

# PritiMusic ke imports
from PritiMusic import app
from config import YOUTUBE_IMG_URL

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Naya text helper func (Second file se)
def trim_to_width(text: str, font, max_width: int) -> str:
    ellipsis = "..."
    # Font error handling if getlength is not supported in older PIL
    try:
        length = font.getlength(text)
    except AttributeError:
        try:
            length, _ = font.getsize(text)
        except:
            length = len(text) * 15 # rough estimate

    if length <= max_width:
        return text
        
    for i in range(len(text), 0, -1):
        new = text[:i] + ellipsis
        try:
            new_len = font.getlength(new)
        except AttributeError:
            try:
                new_len, _ = font.getsize(new)
            except:
                new_len = len(new) * 15
                
        if new_len <= max_width:
            return new
    return ellipsis

# Helper for Random Fallback (Pehle file se)
def get_random_fallback_img():
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg" # Fallback

async def get_thumb(videoid):
    # PritiMusic ka purana cache format rakha gaya hai error se bachne ke liye
    cache_path = os.path.join(CACHE_DIR, f"{videoid}.png")
    if os.path.isfile(cache_path):
        return cache_path

    url = f"https://www.youtube.com/watch?v={videoid}"
    
    # Video ki detail nikal rahe hain
    try:
        results = VideosSearch(url, limit=1)
        search_result = await results.next()
        data = search_result.get("result", [])[0]

        title = data.get("title", "Unknown Title")
        title = re.sub("\W+", " ", title).title()
        
        artist = data.get("channel", {}).get("name", "Unknown Artist")
        duration = data.get("duration", "00:00")
        views = data.get("viewCount", {}).get("short", "0 views")
        thumbnail = data.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
    except Exception as e:
        title = "Unknown Title"
        artist = "Unknown Artist"
        duration = "05:00"
        views = "1M views"
        thumbnail = None

    if not thumbnail:
        return get_random_fallback_img()

    thumb_path = os.path.join(CACHE_DIR, f"raw_{videoid}.jpg")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(thumbnail) as r:
                if r.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await r.read())
    except:
        return get_random_fallback_img()

    # Nayi Design ke sath image banana shuru karte hain
    try:
        W, H = 1280, 720
        img = Image.open(thumb_path).convert("RGBA")
        bg = img.resize((W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.4) # Background ko dark kiya

        draw = ImageDraw.Draw(bg)

        # Aapke bot ke folder se fonts lena (PritiMusic ke paths)
        try:
            font_bold = "PritiMusic/assets/font2.ttf"
            font_med = "PritiMusic/assets/font.ttf"
            title_font = ImageFont.truetype(font_bold, 60)
            artist_font = ImageFont.truetype(font_med, 40)
            time_font = ImageFont.truetype(font_med, 32)
        except:
            title_font = artist_font = time_font = ImageFont.load_default()

        frame_w, frame_h = 450, 450
        frame_x, frame_y = 100, (H - frame_h) // 2 

        album = img.resize((frame_w, frame_h), Image.LANCZOS)
        
        mask = Image.new("L", (frame_w, frame_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, frame_w, frame_h), radius=40, fill=255)
        
        # Glow Effect Add Karna
        glow = Image.new("RGBA", (frame_w + 40, frame_h + 40), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle((20, 20, frame_w + 20, frame_h + 20), radius=40, fill=(0, 0, 0, 150))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=15))
        bg.paste(glow, (frame_x - 20, frame_y - 20), glow)

        # Image ko Paste Karna
        bg.paste(album, (frame_x, frame_y), mask)

        # Frame ki Boundary
        draw.rounded_rectangle(
            (frame_x, frame_y, frame_x + frame_w, frame_y + frame_h), 
            radius=40, 
            outline=(255, 255, 255, 80), 
            width=6
        )

        # Transparent Glass box logic
        text_x = 620
        glass_rect = [text_x - 40, frame_y, W - 60, frame_y + frame_h]
        overlay = Image.new('RGBA', (W, H), (0,0,0,0))
        d_overlay = ImageDraw.Draw(overlay)
        d_overlay.rounded_rectangle(glass_rect, radius=30, fill=(255, 255, 255, 25)) 
        bg.alpha_composite(overlay)

        # Fonts / Texts daalna
        clean_title = trim_to_width(title, title_font, 600)
        draw.text((text_x, frame_y + 40), clean_title, font=title_font, fill=(255, 255, 255, 255))
        
        clean_artist = trim_to_width(f"{artist}", artist_font, 550)
        draw.text((text_x, frame_y + 120), clean_artist, font=artist_font, fill=(200, 200, 200, 230))

        draw.text((text_x, frame_y + 190), f"Views: {views}", font=time_font, fill=(180, 180, 180, 200))

        # Progress Bar Code
        bar_width = 500
        bar_height = 8
        bar_x_pos = text_x
        bar_y_pos = frame_y + 320

        draw.rounded_rectangle((bar_x_pos, bar_y_pos, bar_x_pos + bar_width, bar_y_pos + bar_height), radius=4, fill=(255, 255, 255, 50))
        
        progress = 0.4 # Default Progress
        draw.rounded_rectangle((bar_x_pos, bar_y_pos, bar_x_pos + (bar_width * progress), bar_y_pos + bar_height), radius=4, fill=(0, 200, 255, 255))
        
        # Circle on progress bar
        circle_r = 10
        draw.ellipse((bar_x_pos + (bar_width * progress) - circle_r, bar_y_pos + (bar_height/2) - circle_r, 
                      bar_x_pos + (bar_width * progress) + circle_r, bar_y_pos + (bar_height/2) + circle_r), 
                      fill=(255, 255, 255, 255))

        draw.text((bar_x_pos, bar_y_pos + 25), "00:00", font=time_font, fill=(255, 255, 255, 200))
        draw.text((bar_x_pos + bar_width - 80, bar_y_pos + 25), duration, font=time_font, fill=(255, 255, 255, 200))

        # Image convert and save karna
        bg = bg.convert("RGB")
        bg.save(cache_path, quality=95)
        
        # Raw file remove karna taaki storage full na ho
        try:
            os.remove(thumb_path)
        except:
            pass

        return cache_path
        
    except Exception as e:
        print(f"Error in generating Thumbnail: {e}")
        return get_random_fallback_img()
