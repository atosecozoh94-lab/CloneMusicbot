import asyncio
import glob
import json
import os
import random
import re
from typing import Union
import yt_dlp
import aiohttp
import aiofiles
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch
from PritiMusic import LOGGER
from PritiMusic.utils.formatters import time_to_seconds

# ==========================================
# 🔄 API FALLBACK CONFIGURATION
# ==========================================
API_1_URL = os.getenv("API_1_URL", "https://music.xbitcode.com")
API_1_KEY = os.getenv("API_1_KEY", "xbit_283KQ7UaOqAMuVZeX6lePo-LGI4RRVYh")

API_2_URL = os.getenv("API_2_URL", "https://api.onegrab.fun")
API_2_KEY = os.getenv("API_2_KEY", "6de93b_140J0YK7nrPJFe55Cg7tceSBKI1dPL3d")

API_3_URL = os.getenv("API_3_URL", "https://api.shrutibots.site")
API_3_KEY = os.getenv("API_3_KEY", "ShrutiBotsB9d7HIQ3ytzCU9GuCNeC")
# ==========================================

CLIENT_SESSION = None

logger = LOGGER(__name__)

async def get_session():
    global CLIENT_SESSION
    if CLIENT_SESSION is None or CLIENT_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=300)
        CLIENT_SESSION = aiohttp.ClientSession(connector=connector)
    return CLIENT_SESSION

def cookie_txt_file():
    try:
        folder = f"{os.getcwd()}/cookies"
        files = glob.glob(os.path.join(folder, '*.txt'))
        if not files: return None
        return f"cookies/{os.path.basename(random.choice(files))}"
    except:
        return None

async def check_file_size(link):
    async def get_format_info(link):
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp", "--cookies", cookie_txt_file() or "", "-J", link,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return json.loads(stdout.decode()) if proc.returncode == 0 else None

    info = await get_format_info(link)
    if not info: return None
    return sum(f.get('filesize', 0) for f in info.get('formats', []))

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    return out.decode("utf-8") if out else err.decode("utf-8")

async def _download_stream(url, path, headers=None):
    try:
        session = await get_session()
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200:
                return None
            
            async with aiofiles.open(path, mode='wb') as f:
                async for chunk in response.content.iter_chunked(524288): 
                    await f.write(chunk)
            return path
    except Exception:
        if os.path.exists(path):
            try: os.remove(path)
            except: pass
        return None

# ==========================================
# 🎵 MAIN API DOWNLOAD ENGINE
# ==========================================
async def download_from_api(api_url: str, api_key: str, vid_id: str, title: str, is_video: bool) -> str:
    ext = "mp4" if is_video else "mp3"
    fname = f"{title}.{ext}" if title else f"{vid_id}.{ext}"
    path = os.path.join("downloads", fname)
    
    if os.path.exists(path): return path

    try:
        session = await get_session()
        headers = {"x-api-key": api_key}
        
        async with session.get(f"{api_url}/info/{vid_id}", headers=headers, timeout=8) as resp:
            if resp.status != 200: return None
            data = await resp.json()
        
        if data.get('status') == 'success':
            url = data.get('video_url') if is_video else data.get('audio_url')
            if url:
                return await _download_stream(url, path)
        return None
    except Exception:
        return None

# ==========================================

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message: messages.append(message_1.reply_to_message)
        for msg in messages:
            if msg.entities:
                for ent in msg.entities:
                    if ent.type == MessageEntityType.URL:
                        return (msg.text or msg.caption)[ent.offset : ent.offset + ent.length]
            elif msg.caption_entities:
                for ent in msg.caption_entities:
                    if ent.type == MessageEntityType.TEXT_LINK:
                        return ent.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            res = (await results.next())["result"][0]
            dur = res["duration"]
            return res["title"], dur, int(time_to_seconds(dur)) if dur else 0, res["thumbnails"][0]["url"].split("?")[0], res["id"]
        except:
            return None, "0", 0, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        results = VideosSearch(link.split("&")[0], limit=1)
        return (await results.next())["result"][0]["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        results = VideosSearch(link.split("&")[0], limit=1)
        return (await results.next())["result"][0]["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        results = VideosSearch(link.split("&")[0], limit=1)
        return (await results.next())["result"][0]["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        fpath, _ = await self.download(link, None, video=True)
        return (1, fpath) if fpath else (0, "Failed")

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid: link = self.listbase + link
        link = link.split("&")[0]
        cmd = f"yt-dlp -i --get-id --flat-playlist --cookies {cookie_txt_file()} --playlist-end {limit} --skip-download {link}"
        out = await shell_cmd(cmd)
        return [x for x in out.split("\n") if x]

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        link = link.split("&")[0]
        res = (await VideosSearch(link, limit=1).next())["result"][0]
        return {
            "title": res["title"],
            "link": res["link"],
            "vidid": res["id"],
            "duration_min": res["duration"],
            "thumb": res["thumbnails"][0]["url"].split("?")[0],
        }, res["id"]

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        link = link.split("&")[0]
        ydl_opts = {"quiet": True, "cookiefile": cookie_txt_file()}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            formats = [
                {
                    "format": f["format"], "filesize": f.get("filesize"), 
                    "format_id": f["format_id"], "ext": f["ext"], 
                    "format_note": f.get("format_note"), "yturl": link
                } 
                for f in info["formats"] 
                if "dash" not in str(f.get("format", "")).lower() and f.get("filesize")
            ]
        return formats, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        link = link.split("&")[0]
        results = (await VideosSearch(link, limit=10).next()).get("result", [])
        
        valid = []
        for res in results:
            try:
                t = time_to_seconds(res.get("duration", "0:00"))
                if t <= 3600: valid.append(res)
            except: pass
            
        if not valid or query_type >= len(valid): raise ValueError("No video")
        sel = valid[query_type]
        return sel["title"], sel["duration"], sel["thumbnails"][0]["url"].split("?")[0], sel["id"]

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> tuple:
        if videoid:
            vid_id = link
            link = self.base + link
        else:
            vid_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link

        is_video = bool(video or songvideo)

        # 1️⃣ STEP 1: Pehle API 1 se song try karo
        result = await download_from_api(API_1_URL, API_1_KEY, vid_id, title, is_video)
        
        # 2️⃣ STEP 2: Agar API 1 fail hoti hai (None), toh API 2 use karo (Fallback)
        if not result:
            logger.info(f"API 1 Failed for {vid_id}. Switching to API 2...")
            result = await download_from_api(API_2_URL, API_2_KEY, vid_id, title, is_video)

        # 3️⃣ STEP 3: Agar API 2 bhi fail hoti hai, toh nayi API 3 use karo (2nd Fallback)
        if not result:
            logger.info(f"API 2 Failed for {vid_id}. Switching to API 3...")
            result = await download_from_api(API_3_URL, API_3_KEY, vid_id, title, is_video)

        # 4️⃣ STEP 4: Return result
        if result:
            return result, True
        
        # Agar teeno API fail ho jayein
        logger.error(f"All 3 APIs failed to download {vid_id}")
        return None, False
