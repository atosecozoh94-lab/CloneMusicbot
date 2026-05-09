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

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage

def clear(text):
    list = text.split(" ")
    title = ""
    for i in list:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()

# ✅ Helper for Random Fallback
def get_random_fallback_img():
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg" # Fallback

async def get_thumb(videoid):
    if os.path.isfile(f"cache/{videoid}.png"):
        return f"cache/{videoid}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub("\W+", " ", title)
                title = title.title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown Mins"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                views = result["viewCount"]["short"]
            except:
                views = "Unknown Views"
            try:
                channel = result["channel"]["name"]
            except:
                channel = "Unknown Channel"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        # ==========================================
        # 🔥 IMAGE PROCESSING START (PERFECT ALIGNMENT) 🔥
        # ==========================================
        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        
        # 1. Premium Blurred Dark Background
        background = image2.filter(filter=ImageFilter.GaussianBlur(15))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.4)
        
        # 2. Add Sharp Original Thumbnail in the center
        sharp_thumb = changeImageSize(768, 432, youtube).convert("RGBA")
        background.paste(sharp_thumb, (256, 50)) # Centered horizontally
        
        draw = ImageDraw.Draw(background)
        
        # 3. Fonts Setup
        try:
            arial = ImageFont.truetype("PritiMusic/assets/font2.ttf", 30)
            font = ImageFont.truetype("PritiMusic/assets/font.ttf", 40) 
            small_font = ImageFont.truetype("PritiMusic/assets/font2.ttf", 25) 
        except:
            arial = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            
        # 4. Watermark (Top Right)
        bot_name = "CLONNE MUSIC BOT"
        try:
            left, top, right, bottom = draw.textbbox((0, 0), bot_name, font=small_font)
            text_width = right - left
        except:
            try:
                text_width, _ = draw.textsize(bot_name, font=small_font)
            except:
                text_width = 250

        draw.text((1280 - text_width - 30, 25), bot_name, fill="#1DB954", font=small_font)
        
        # ==========================================
        # ✅ FIX: PERFECT LEFT ALIGNMENT STRUCTURE 
        # ==========================================
        margin_x = 70  # Har cheez yahan se shuru hogi (= structure)
        
        # 5. Track Info (Title, Channel, Views)
        final_title = clear(title)
        # Agar title bahut bada hai toh usko cut kar denge taaki screen ke bahar na jaye
        if len(final_title) > 55:
            final_title = final_title[:55] + "..."

        draw.text(
            (margin_x, 520),
            final_title,
            fill=(255, 255, 255), 
            font=font,
        )
        draw.text(
            (margin_x, 575),
            f"👤 {channel}   |   👁️ {views[:23]}",
            fill=(200, 200, 200), 
            font=arial,
        )
        
        # 6. Two-Tone Modern Progress Bar (Aligned with text)
        theme_color = "#1DB954" 
        
        # Empty Line
        draw.line(
            [(margin_x, 650), (1210, 650)],
            fill="#555555",
            width=8,
            joint="curve",
        )
        # Played Line
        draw.line(
            [(margin_x, 650), (350, 650)],
            fill=theme_color,
            width=8,
            joint="curve",
        )
        # Playhead Circle
        draw.ellipse(
            [(340, 638), (364, 662)],
            outline=theme_color,
            fill=theme_color,
            width=15,
        )
        
        # 7. Timestamps
        draw.text(
            (margin_x, 670),
            "00:00",
            fill=(200, 200, 200),
            font=small_font,
        )
        draw.text(
            (1135, 670), # Right aligned
            f"{duration[:23]}",
            fill=(200, 200, 200),
            font=small_font,
        )
        
        # ==========================================
        # 🔥 IMAGE PROCESSING END 🔥
        # ==========================================

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        background.save(f"cache/{videoid}.png")
        return f"cache/{videoid}.png"
        
    except Exception as e:
        print(e)
        return get_random_fallback_img()
