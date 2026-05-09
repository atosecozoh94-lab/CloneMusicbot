import random
import string
import asyncio
import re
from random import randint
from urllib.parse import urlparse, parse_qs

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message, InlineKeyboardButton
from pytgcalls.exceptions import NoActiveGroupCall
from PritiMusic.utils.database import get_assistant
import config
from PritiMusic import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app
from PritiMusic.core.call import Lucky
from PritiMusic.misc import SUDOERS, db

# ✅ IMPORT: Ab 'buttons.py' se import ho raha hai
from PritiMusic.cplugin.buttons import (
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
    queue_markup,
    stream_markup,
    stream_markup2,
    panel_markup_1,
    panel_markup_2,
    panel_markup_3,
    panel_markup_4,
    panel_markup_5,
    panel_markup_clone,
    telegram_markup
)

from PritiMusic.utils import seconds_to_min, time_to_seconds
from PritiMusic.utils.channelplay import get_channeplayCB
from PritiMusic.utils.decorators.language import languageCB
from PritiMusic.utils.decorators.play import CPlayWrapper
from PritiMusic.utils.formatters import formats
from PritiMusic.utils.inline import close_markup, aq_markup

from PritiMusic.utils.database import (
    add_served_user_clone,
    is_active_chat,
    add_active_video_chat,
    clonebotdb
)

from PritiMusic.utils.database.clonedb import (
    get_owner_id_from_db, 
    get_cloned_support_chat, 
    get_clone_search_settings,
    get_clone_stream_caption
)

from PritiMusic.utils.exceptions import AssistantErr
from PritiMusic.utils.pastebin import LuckyBin
from PritiMusic.utils.stream.queue import put_queue, put_queue_index
from PritiMusic.utils.logger import play_logs, clone_bot_logs
from PritiMusic.cplugin.setinfo import get_logging_status, get_log_channel
from PritiMusic.cplugin.utils.cthumbnail import get_thumb

from config import BANNED_USERS, lyrical
from time import time
from datetime import datetime
from typing import Union

user_last_message_time = {}
user_command_count = {}
SPAM_THRESHOLD = 2
SPAM_WINDOW_SECONDS = 5

def get_random_img(img_list):
    if img_list:
        if isinstance(img_list, list):
            return random.choice(img_list)
        return img_list
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

# 🛡️ SECURITY PATCH: Anti Command-Injection Function
def is_safe_input(text):
    if not text:
        return True
    # Blocks shell execution characters that hackers use to dump variables or run commands
    dangerous_chars = [';', '$', '|', '&', '`', '{', '}', '<', '>', '\\', '\n', '\r']
    if any(char in text for char in dangerous_chars):
        return False
    return True

@Client.on_message(
    filters.command(
        [
            "play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"
        ],
        prefixes=["/", "!", "%", "", ".", "@", "#"],
    )
    & filters.group
    & ~BANNED_USERS
)
@CPlayWrapper
async def play_commnd(client, message: Message, _, chat_id, video, channel, playmode, url, fplay):
    cuser = await client.get_me()
    try:
        if cuser.username:
            await clonebotdb.update_one(
                {"username": cuser.username},
                {"$set": {"last_activity": datetime.now()}}
            )
    except Exception:
        pass

    bot_id = cuser.id
    user_id = message.from_user.id

    if hasattr(client, "assistant") and client.assistant:
        userbot = client.assistant
    else:
        userbot = await get_assistant(chat_id)

    C_BOT_OWNER_ID = await get_owner_id_from_db(bot_id)
    bot_mention = cuser.mention
    
    try:
        C_LOG_STATUS = await get_logging_status(bot_id)
        C_LOGGER_ID = await get_log_channel(bot_id)
    except:
        C_LOG_STATUS = True 
        C_LOGGER_ID = config.CLONE_LOGGER

    if str(C_LOGGER_ID) == "-100":
        C_LOGGER_ID = C_BOT_OWNER_ID

    clone_logger_id = C_LOGGER_ID

    current_time = time()
    last_message_time = user_last_message_time.get(user_id, 0)

    if current_time - last_message_time < SPAM_WINDOW_SECONDS:
        user_last_message_time[user_id] = current_time
        user_command_count[user_id] = user_command_count.get(user_id, 0) + 1
        if user_command_count[user_id] > SPAM_THRESHOLD:
            hu = await message.reply_text(f"**{message.from_user.mention} Please do not spam. Try again in 5 seconds.**")
            await asyncio.sleep(3)
            await hu.delete()
            return
    else:
        user_command_count[user_id] = 1
        user_last_message_time[user_id] = current_time

    await add_served_user_clone(message.chat.id, bot_id)
    
    try:
        stype, scontent = await get_clone_search_settings(bot_id)
        if stype == "text" and scontent:
            mystic = await message.reply_text(scontent)
        elif stype == "sticker" and scontent:
            mystic = await message.reply_sticker(scontent)
        elif stype == "animation" and scontent:
            mystic = await message.reply_animation(scontent)
        elif stype == "video" and scontent:
            mystic = await message.reply_video(scontent)
        elif stype == "photo" and scontent:
            mystic = await message.reply_photo(scontent)
        else:
            mystic = await message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])
    except Exception as e:
        mystic = await message.reply_text(_["play_2"].format(channel) if channel else _["play_1"])

    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.mention

    audio_telegram = ((message.reply_to_message.audio or message.reply_to_message.voice) if message.reply_to_message else None)
    video_telegram = ((message.reply_to_message.video or message.reply_to_message.document) if message.reply_to_message else None)
    
    if audio_telegram:
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, cuser.mention))
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            try:
                await stream(client, _, mystic, user_id, details, chat_id, user_name, message.chat.id, streamtype="telegram", forceplay=fplay, userbot=userbot)
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                print(e)
                return await mystic.edit_text(e)
            return await mystic.delete()
        return
    elif video_telegram:
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))
            except:
                return await mystic.edit_text(_["play_7"].format(f"{' | '.join(formats)}"))
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {"title": file_name, "link": message_link, "path": file_path, "dur": dur}
            try:
                await stream(client, _, mystic, user_id, details, chat_id, user_name, message.chat.id, video=True, streamtype="telegram", forceplay=fplay, userbot=userbot)
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                print(e)
                return await mystic.edit_text(e)
            return await mystic.delete()
        return
    elif url:
        # 🛡️ SECURITY: Character Injection Check for URL
        if not is_safe_input(url):
            return await mystic.edit_text("❌ **Security Alert:** Malicious link detected. Request blocked.")

        if not url.startswith(("http://", "https://")):
            return await mystic.edit_text("❌ **Security Error:** Local files are not allowed.")
            
        allowed_domains = ["youtube.com", "youtu.be", "spotify.com", "soundcloud.com", "m.soundcloud.com", "music.apple.com", "resso.com"]
        if not any(domain in url for domain in allowed_domains):
             return await mystic.edit_text("❌ **Unsupported Link!**")
             
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(url, config.PLAYLIST_FETCH_LIMIT, message.from_user.id)
                except Exception as e:
                    print(e)
                    return await mystic.edit_text("❌ Failed to fetch playlist.")
                streamtype = "playlist"
                plist_type = "yt"
                
                # 🛡️ SECURITY: Safe ID Extraction using urlparse
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                if "list" in query_params:
                    plist_id = query_params["list"][0]
                else:
                    return await mystic.edit_text("❌ **Error:** Invalid playlist link structure.")
                
                img = get_random_img(config.PLAYLIST_IMG_URL)
                cap = _["play_10"]
            elif "https://youtu.be" in url:
                videoid = url.split("/")[-1].split("?")[0]
                details, track_id = await YouTube.track(f"https://www.youtube.com/watch?v={videoid}")
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except Exception as e:
                    print(e)
                    return await mystic.edit_text("❌ Error fetching YouTube track.")
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text("» Spotify is not supported yet.")
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except:
                    return await mystic.edit_text("❌ Error fetching Spotify track.")
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text("❌ Error fetching Spotify playlist.")
                streamtype = "playlist"
                plist_type = "spplay"
                img = get_random_img(config.SPOTIFY_PLAYLIST_IMG_URL)
                cap = _["play_11"].format(cuser.mention, message.from_user.mention)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except:
                    return await mystic.edit_text("❌ Error fetching Spotify album.")
                streamtype = "playlist"
                plist_type = "spalbum"
                img = get_random_img(config.SPOTIFY_ALBUM_IMG_URL)
                cap = _["play_11"].format(cuser.mention, message.from_user.mention)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except:
                    return await mystic.edit_text("❌ Error fetching Spotify artist.")
                streamtype = "playlist"
                plist_type = "spartist"
                img = get_random_img(config.SPOTIFY_ARTIST_IMG_URL)
                cap = _["play_11"].format(message.from_user.first_name)
            else:
                return await mystic.edit_text(_["play_15"])
        elif await Apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Apple.track(url)
                except:
                    return await mystic.edit_text("❌ Error fetching Apple track.")
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except:
                    return await mystic.edit_text("❌ Error fetching Apple playlist.")
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_12"].format(cuser.mention, message.from_user.mention)
                img = url
            else:
                return await mystic.edit_text("❌ Error: Invalid Apple Music link.")
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except:
                return await mystic.edit_text("❌ Error fetching Resso track.")
            streamtype = "youtube"
            img = details["thumb"]
            cap = _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try:
                details, track_path = await SoundCloud.download(url)
            except:
                return await mystic.edit_text("❌ Error fetching SoundCloud track.")
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, cuser.mention))
            try:
                await stream(client, _, mystic, user_id, details, chat_id, user_name, message.chat.id, streamtype="soundcloud", forceplay=fplay, userbot=userbot)
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                print(e)
                return await mystic.edit_text(e)
            return await mystic.delete()
        else:
            try:
                await Lucky.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await app.send_message(chat_id=config.CLONE_LOGGER, text=_["play_17"])
            except Exception as e:
                if "phone.CreateGroupCall" in str(e):
                    await mystic.edit_text(_["black_9"])
                    return await app.send_message(chat_id=config.CLONE_LOGGER, text=_["play_17"])
                else:
                    print(e)
                    return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try:
                await stream(client, _, mystic, message.from_user.id, url, chat_id, message.from_user.first_name, message.chat.id, video=video, streamtype="index", forceplay=fplay, userbot=userbot)
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                print(e)
                return await mystic.edit_text(e)
            if C_LOG_STATUS:
                try:
                    await clone_bot_logs(client, message, bot_mention, clone_logger_id, streamtype="M3u8 or Index Link")
                except Exception as e:
                    print(f"[ERROR] Failed to send logging enabled message: {e}")
            return await play_logs(message, streamtype="M3u8 or Index Link")
    else:
        if len(message.command) < 2:
            try:
                a = await client.get_me()
                C_BOT_SUPPORT_CHAT = await get_cloned_support_chat(a.id)
                if C_BOT_SUPPORT_CHAT:
                    C_SUPPORT_CHAT = C_BOT_SUPPORT_CHAT if "https://" in C_BOT_SUPPORT_CHAT else f"https://t.me/{C_BOT_SUPPORT_CHAT}"
                else:
                    C_SUPPORT_CHAT = config.SUPPORT_CHAT
            except:
                C_SUPPORT_CHAT = config.SUPPORT_CHAT
            buttons = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Support", url=C_SUPPORT_CHAT), InlineKeyboardButton(text="Close", callback_data="close")]]
            )
            play_img = get_random_img(config.PLAYLIST_IMG_URL)
            try:
                stype, scontent = await get_clone_search_settings(bot_id)
                if stype == "photo" and scontent:
                     play_img = scontent
            except:
                pass
            await mystic.delete()
            return await message.reply_photo(photo=play_img, caption=_["play_18"], reply_markup=buttons, has_spoiler=True)
            
        slider = True
        query = message.text.split(None, 1)[1]
        
        # 🛡️ SECURITY: Check Text Query for Injection
        if not is_safe_input(query):
            return await mystic.edit_text("❌ **Security Alert:** Malicious search query detected.")
            
        if "-v" in query:
            query = query.replace("-v", "")
        try:
            details, track_id = await YouTube.track(query)
        except:
            return await mystic.edit_text("❌ Error searching on YouTube.")
        streamtype = "youtube"

    if str(playmode) == "Direct":
        if not plist_type:
            if details["duration_min"]:
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(_["play_6"].format(config.DURATION_LIMIT_MIN, cuser.mention))
            else:
                buttons = livestream_markup(_, track_id, user_id, "v" if video else "a", "c" if channel else "g", "f" if fplay else "d")
                return await mystic.edit_text(_["play_13"], reply_markup=InlineKeyboardMarkup(buttons))
        try:
            await stream(client, _, mystic, user_id, details, chat_id, user_name, message.chat.id, video=video, streamtype=streamtype, spotify=spotify, forceplay=fplay, userbot=userbot)
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
            print(e)
            return await mystic.edit_text(e)
        await mystic.delete()
        if C_LOG_STATUS:
            try:
                await clone_bot_logs(client, message, bot_mention, clone_logger_id, streamtype=streamtype)
            except Exception as e:
                print(f"[ERROR] Failed to send logging enabled message: {e}")
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(_, ran_hash, message.from_user.id, plist_type, "c" if channel else "g", "f" if fplay else "d")
            await mystic.delete()
            await message.reply_photo(photo=img, caption=cap, reply_markup=InlineKeyboardMarkup(buttons), has_spoiler=True)
            if C_LOG_STATUS:
                try:
                    await clone_bot_logs(client, message, bot_mention, clone_logger_id, streamtype=f"Playlist : {plist_type}")
                except Exception as e:
                    print(f"[ERROR] Failed to send logging enabled message: {e}")
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else:
            if slider:
                buttons = slider_markup(_, track_id, message.from_user.id, query, 0, "c" if channel else "g", "f" if fplay else "d")
                await mystic.delete()
                
                # ✅ FIX: Syntax complete karke reply bheja jaa raha hai
                await message.reply_photo(
                    photo=details["thumb"],
                    caption=_["play_10"].format(
                        details["title"].title(),
                        details["duration_min"],
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    has_spoiler=True
                )
                if C_LOG_STATUS:
                    try:
                        await clone_bot_logs(client, message, bot_mention, clone_logger_id, streamtype=f"Searched on Youtube")
                    except Exception as e:
                        pass
                return await play_logs(message, streamtype=f"Searched on Youtube")
            else:
                buttons = track_markup(_, track_id, message.from_user.id, "c" if channel else "g", "f" if fplay else "d")
                await mystic.delete()
                
                # ✅ FIX: Syntax complete karke reply bheja jaa raha hai
                await message.reply_photo(
                    photo=img, 
                    caption=cap, 
                    reply_markup=InlineKeyboardMarkup(buttons), 
                    has_spoiler=True
                )
                if C_LOG_STATUS:
                    try:
                        await clone_bot_logs(client, message, bot_mention, clone_logger_id, streamtype=f"URL Searched Inline")
                    except Exception as e:
                        pass
                return await play_logs(message, streamtype=f"URL Searched Inline")
