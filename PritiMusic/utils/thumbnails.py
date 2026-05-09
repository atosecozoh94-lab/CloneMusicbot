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
        # 🔥 IMAGE PROCESSING START (AWESOME LOOK) 🔥
        # ==========================================
        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        
        # 1. Premium Blurred Dark Background
        background = image2.filter(filter=ImageFilter.GaussianBlur(15)) # GaussianBlur looks smoother
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.4) # Darkened for better text visibility
        
        # 2. Add Sharp Original Thumbnail in the center (Sleek UI)
        sharp_thumb = changeImageSize(768, 432, youtube).convert("RGBA")
        background.paste(sharp_thumb, (256, 70)) # Centered horizontally
        
        draw = ImageDraw.Draw(background)
        
        # 3. Fonts Setup (Added proper hierarchy)
        try:
            arial = ImageFont.truetype("PritiMusic/assets/font2.ttf", 30)
            font = ImageFont.truetype("PritiMusic/assets/font.ttf", 40) # Larger for Title
            small_font = ImageFont.truetype("PritiMusic/assets/font2.ttf", 25) # Smaller for extra details
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

        # Subtly placed watermark
        draw.text((1280 - text_width - 30, 25), bot_name, fill="#1DB954", font=small_font)
        
        # 5. Track Info (Title, Channel, Views)
        draw.text(
            (256, 520),
            clear(title),
            fill=(255, 255, 255), # Pure White
            font=font,
        )
        draw.text(
            (256, 575),
            f"👤 {channel}   |   👁️ {views[:23]}",
            fill=(200, 200, 200), # Light Grey for subtitle
            font=arial,
        )
        
        # 6. Two-Tone Modern Progress Bar
        theme_color = "#1DB954" # Premium Green color (You can change to "#FF0000" for Red)
        
        # Empty part of the line (Grey)
        draw.line(
            [(55, 660), (1220, 660)],
            fill="#555555",
            width=8,
            joint="curve",
        )
        # Played part of the line (Theme Color)
        draw.line(
            [(55, 660), (400, 660)],
            fill=theme_color,
            width=8,
            joint="curve",
        )
        # Playhead Scrubber (Circle)
        draw.ellipse(
            [(390, 648), (414, 672)],
            outline=theme_color,
            fill=theme_color,
            width=15,
        )
        
        # 7. Timestamps
        draw.text(
            (55, 680),
            "00:00",
            fill=(200, 200, 200),
            font=small_font,
        )
        draw.text(
            (1150, 680),
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
        # ✅ FIX: Return Single Random Image instead of List
        return get_random_fallback_img()
        
