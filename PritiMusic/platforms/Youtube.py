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
from youtubesearchpython.__future__ import VideosSearch 
from PritiMusic import LOGGER
from PritiMusic.utils.formatters import time_to_seconds

# --- CONFIGURATION (xbit & Shruti) ---
YT_API_KEY = "xbit_283KQ7UaOqAMuVZeX6lePo-LGI4RRVYh"
YTPROXY = "https://tgapi.xbitcode.com"
FALLBACK_API_URL = "https://shrutibots.site"
YOUR_API_URL = None
CLIENT_SESSION = None

logger = LOGGER(__name__)

# Session Management
async def get_session():
    global CLIENT_SESSION
    if CLIENT_SESSION is None or CLIENT_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=500, ttl_dns_cache=300)
        CLIENT_SESSION = aiohttp.ClientSession(connector=connector)
    return CLIENT_SESSION

async def load_api_url():
    global YOUR_API_URL
    YOUR_API_URL = FALLBACK_API_URL # Shruti direct set kar di

# Cookie Utility
def cookie_txt_file():
    try:
        folder = f"{os.getcwd()}/cookies"
        files = glob.glob(os.path.join(folder, '*.txt'))
        return f"cookies/{os.path.basename(random.choice(files))}" if files else None
    except: return None

# Download Engines
async def _download_stream(url, path, headers=None):
    try:
        session = await get_session()
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200: return None
            async with aiofiles.open(path, mode='wb') as f:
                async for chunk in response.content.iter_chunked(524288): 
                    await f.write(chunk)
            return path
    except:
        if os.path.exists(path): 
            try: os.remove(path)
            except: pass
        return None

async def download_fallback_engine(link: str, is_video: bool) -> str:
    # Shruti API for fallback
    vid_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    ext = "mp4" if is_video else "mp3"
    path = os.path.join("downloads", f"{vid_id}.{ext}")
    if os.path.exists(path): return path
    try:
        session = await get_session()
        v_type = "video" if is_video else "audio"
        async with session.get(f"{FALLBACK_API_URL}/download", params={"url": vid_id, "type": v_type}, timeout=8) as resp:
            if resp.status != 200: return None
            data = await resp.json()
            token = data.get("download_token")
            if not token: return None
        dl_url = f"{FALLBACK_API_URL}/stream/{vid_id}?type={v_type}"
        return await _download_stream(dl_url, path, headers={"X-Download-Token": token})
    except: return None

async def download_proxy_engine(vid_id: str, title: str, is_video: bool) -> str:
    # xbit API
    ext = "mp4" if is_video else "mp3"
    fname = f"{title}.{ext}" if title else f"{vid_id}.{ext}"
    path = os.path.join("downloads", fname)
    if os.path.exists(path): return path
    try:
        session = await get_session()
        headers = {"x-api-key": YT_API_KEY}
        async with session.get(f"{YTPROXY}/info/{vid_id}", headers=headers, timeout=8) as resp:
            if resp.status != 200: return None
            data = await resp.json()
        if data.get('status') == 'success':
            url = data['video_url'] if is_video else data['audio_url']
            return await _download_stream(url, path)
        return None
    except: return None

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"^(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|shorts\/|v\/|playlist\?list=)?([a-zA-Z0-9_-]{11})"

    def _get_hd_thumbnail(self, vid_id: str) -> str:
        return f"https://img.youtube.com/vi/{vid_id}/maxresdefault.jpg"

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        return bool(re.search(self.regex, link))

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        try:
            results = VideosSearch(link.split("&")[0], limit=1)
            res = (await results.next())["result"][0]
            vid_id = res["id"]
            return res["title"], res["duration"], int(time_to_seconds(res["duration"])), self._get_hd_thumbnail(vid_id), vid_id
        except: return None, "0", 0, None, None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid: link = self.base + link
        results = VideosSearch(link.split("&")[0], limit=1)
        vid_id = (await results.next())["result"][0]["id"]
        return self._get_hd_thumbnail(vid_id)

    async def download(self, link: str, mystic, video=False, videoid=None, songaudio=False, songvideo=False, format_id=None, title=None):
        vid_id = link if videoid else (link.split('v=')[-1].split('&')[0] if 'v=' in link else link)
        is_video = bool(video or songvideo)
        
        # Concurrent downloads for speed
        task1 = asyncio.create_task(download_fallback_engine(link, is_video))
        task2 = asyncio.create_task(download_proxy_engine(vid_id, title, is_video))
        
        pending = {task1, task2}
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                res = task.result()
                if res:
                    for p in pending: p.cancel()
                    return res, True
        return None, False

    # (Baki functions jaise title, duration, playlist, slider wahi rahenge jo aapke purane code me the)
