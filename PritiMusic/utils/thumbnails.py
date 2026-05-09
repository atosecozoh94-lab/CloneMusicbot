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

def get_random_fallback_img():
    if YOUTUBE_IMG_URL:
        if isinstance(YOUTUBE_IMG_URL, list):
            return random.choice(YOUTUBE_IMG_URL)
        return YOUTUBE_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

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
        # 🔥 FINAL PERFECT STRUCTURE (= ALIGNMENT)
        # ==========================================
        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        
        # 1. Dark Blurred Background
        background = image2.filter(filter=ImageFilter.GaussianBlur(20))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.3) # Dark for text clarity
        
        # 2. Main Center Thumbnail (Size: 854x480)
        sharp_thumb = changeImageSize(854, 480, youtube).convert("RGBA")
        
        # X=213 par place kiya taaki exactly center me rahe (1280-854)/2 = 213
        margin_x = 213 
        end_x = margin_x + 854 # = 1067 (Ye Right margin hai)
        
        background.paste(sharp_thumb, (margin_x, 40)) 
        
        draw = ImageDraw.Draw(background)
        
        # 3. Fonts
        try:
            arial = ImageFont.truetype("PritiMusic/assets/font2.ttf", 30)
            font = ImageFont.truetype("PritiMusic/assets/font.ttf", 38) 
            small_font = ImageFont.truetype("PritiMusic/assets/font2.ttf", 25) 
        except:
            arial = ImageFont.load_default()
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
            
        # 4. Watermark (Top Right Corner)
        bot_name = "CLONNE MUSIC BOT"
        try:
            left, top, right, bottom = draw.textbbox((0, 0), bot_name, font=small_font)
            text_width = right - left
        except:
            try:
                text_width, _ = draw.textsize(bot_name, font=small_font)
            except:
                text_width = 250
        draw.text((1280 - text_width - 30, 20), bot_name, fill="#1DB954", font=small_font)
        
        # 5. Title & Channel (ALIGNED TO THUMBNAIL LEFT EDGE)
        final_title = clear(title)
        if len(final_title) > 45:
            final_title = final_title[:45] + "..."

        draw.text(
            (margin_x, 540), # Margin_x = 213
            final_title,
            fill="white", 
            font=font,
        )
        draw.text(
            (margin_x, 595), # Margin_x = 213
            f"{channel}  •  {views[:23]}",
            fill=(180, 180, 180), 
            font=arial,
        )
        
        # 6. Progress Bar (MATCHES THUMBNAIL WIDTH EXACTLY)
        theme_color = "#1DB954" 
        
        # Empty Track Line (From Thumbnail Left to Thumbnail Right)
        draw.line(
            [(margin_x, 660), (end_x, 660)], 
            fill="#555555",
            width=8,
            joint="curve",
        )
        # Played Track Line
        draw.line(
            [(margin_x, 660), (margin_x + 250, 660)],
            fill=theme_color,
            width=8,
            joint="curve",
        )
        # Playhead Circle
        draw.ellipse(
            [(margin_x + 240, 648), (margin_x + 264, 672)],
            outline=theme_color,
            fill=theme_color,
            width=15,
        )
        
        # 7. Timestamps
        # Left Time (00:00)
        draw.text(
            (margin_x, 675),
            "00:00",
            fill=(180, 180, 180),
            font=small_font,
        )
        
        # Right Time (Duration) aligned perfectly to the right end of progress bar
        try:
            left, top, right, bottom = draw.textbbox((0, 0), f"{duration[:23]}", font=small_font)
            dur_width = right - left
        except:
            try:
                dur_width, _ = draw.textsize(f"{duration[:23]}", font=small_font)
            except:
                dur_width = 60
                
        draw.text(
            (end_x - dur_width, 675), 
            f"{duration[:23]}",
            fill=(180, 180, 180),
            font=small_font,
        )
        
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
        
