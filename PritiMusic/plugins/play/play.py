import random
import string
import re
from urllib.parse import urlparse, parse_qs

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from PritiMusic import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app, LOGGER
from PritiMusic.core.call import Lucky
from PritiMusic.utils import seconds_to_min, time_to_seconds
from PritiMusic.utils.channelplay import get_channeplayCB
from PritiMusic.utils.decorators.language import languageCB
from PritiMusic.utils.decorators.play import PlayWrapper
from PritiMusic.utils.formatters import formats
from PritiMusic.utils.inline import (
    botplaylist_markup,
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from PritiMusic.utils.logger import play_logs
from PritiMusic.utils.stream.stream import stream
from config import BANNED_USERS, lyrical

# ✅ Helper function for Random Image
def get_random_img(img_list):
    if img_list:
        if isinstance(img_list, list):
            return random.choice(img_list)
        return img_list
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg" # Fallback

# 🛡️ SECURITY PATCH: Anti Command-Injection Function
def is_safe_input(text):
    if not text:
        return True
    # Blocks shell execution characters: ; $ | & ` { } < > \ \n \r
    dangerous_chars = [';', '$', '|', '&', '`', '{', '}', '<', '>', '\\', '\n', '\r']
    if any(char in text for char in dangerous_chars):
        return False
    return True

@app.on_message(
   filters.command(["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"] ,prefixes=["/", "!", "%", ",", "", ".", "@", "#"])
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )

    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )

    if audio_telegram:
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
            )
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name,
                    message.chat.id, streamtype="telegram", forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_2"].format(ex_type)
                    LOGGER(__name__).error(ex_type, exc_info=True)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return

    elif video_telegram:
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(
                        _["play_7"].format(f"{' | '.join(formats)}")
                    )
            except:
                return await mystic.edit_text(
                    _["play_7"].format(f"{' | '.join(formats)}")
                )
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name,
                    message.chat.id, video=True, streamtype="telegram", forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e 
                else:
                    err = _["general_2"].format(ex_type)
                    LOGGER(__name__).error(ex_type, exc_info=True)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return

    elif url:
        # 🛡️ SECURITY: Character Injection Check
        if not is_safe_input(url):
            LOGGER(__name__).warning(f"Malicious URL playback attempt blocked from {user_id}")
            return await mystic.edit_text("❌ **Security Alert:** Malicious link detected. Request blocked.")

        # 🛡️ SECURITY: Block Local Files
        if not url.startswith(("http://", "https://")):
            return await mystic.edit_text("❌ **Security Error:** Local files and invalid protocols are not allowed.")

        # 🛡️ SECURITY: Domain Whitelist Validation
        allowed_domains = [
            "youtube.com", "youtu.be",
            "spotify.com", "open.spotify.com",
            "soundcloud.com", "m.soundcloud.com",
            "music.apple.com", "resso.com"
        ]
        
        if not any(domain in url for domain in allowed_domains):
             return await mystic.edit_text(
                 "❌ **Unsupported Link!**\n\n"
                 "Only YouTube, Spotify, SoundCloud, Apple Music, and Resso are supported."
             )

        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                        message.from_user.id,
                    )
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
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
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text(
                    "» sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ.\n\nᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."
                )
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spplay"
                img = get_random_img(config.SPOTIFY_PLAYLIST_IMG_URL)
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spalbum"
                img = get_random_img(config.SPOTIFY_ALBUM_IMG_URL)
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
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
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_12"].format(app.mention, message.from_user.mention)
                img = url
            else:
                return await mystic.edit_text(_["play_3"])
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except:
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"
            img = details["thumb"]
            cap = _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try:
                details, track_path = await SoundCloud.download(url)
            except:
                return await mystic.edit_text(_["play_3"])
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
                )
            try:
                await stream(
                    _, mystic, user_id, details, chat_id, user_name,
                    message.chat.id, streamtype="soundcloud", forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_2"].format(ex_type)
                    LOGGER(__name__).error(ex_type, exc_info=True)
                return await mystic.edit_text(err)
            return await mystic.delete()
        else:
            try:
                await Lucky.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=_["play_17"],
                )
            except Exception as e:
                return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _, mystic, message.from_user.id, url, chat_id, message.from_user.first_name,
                    message.chat.id, video=video, streamtype="index", forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e 
                else:
                    err = _["general_2"].format(ex_type)
                    LOGGER(__name__).error(ex_type, exc_info=True)
                return await mystic.edit_text(err)
            return await play_logs(message, streamtype="M3u8 or Index Link")

    else:
        # ✅ FIX: Handle /play with no arguments (Send Random Photo + Spoiler)
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            await mystic.delete()
            return await message.reply_photo(
                photo=get_random_img(config.PLAYLIST_IMG_URL),
                caption=_["play_18"],
                reply_markup=InlineKeyboardMarkup(buttons),
                has_spoiler=True
            )
            
        slider = True
        query = message.text.split(None, 1)[1]
        
        # 🛡️ SECURITY: Check Text Query for Injection
        if not is_safe_input(query):
            LOGGER(__name__).warning(f"Malicious Text Query blocked from {user_id}")
            return await mystic.edit_text("❌ **Security Alert:** Malicious search query detected.")

        if "-v" in query:
            query = query.replace("-v", "")
        try:
            details, track_id = await YouTube.track(query)
        except:
            return await mystic.edit_text(_["play_3"])
        streamtype = "youtube"

    if str(playmode) == "Direct":
        if not plist_type:
            if details["duration_min"]:
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
                    )
            else:
                buttons = livestream_markup(
                    _, track_id, user_id, "v" if video else "a",
                    "c" if channel else "g", "f" if fplay else "d",
                )
                return await mystic.edit_text(
                    _["play_13"], reply_markup=InlineKeyboardMarkup(buttons),
                )
        try:
            await stream(
                _, mystic, user_id, details, chat_id, user_name,
                message.chat.id, video=video, streamtype=streamtype,
                spotify=spotify, forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            if ex_type == "AssistantErr":
                err = e 
            else:
                err = _["general_2"].format(ex_type)
                LOGGER(__name__).error(ex_type, exc_info=True)
            return await mystic.edit_text(err)
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(
                _, ran_hash, message.from_user.id, plist_type,
                "c" if channel else "g", "f" if fplay else "d",
            )
            await mystic.delete()
            
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
                has_spoiler=True
            )
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else:
            if slider:
                buttons = slider_markup(
                    _, track_id, message.from_user.id, query, 0,
                    "c" if channel else "g", "f" if fplay else "d",
                )
                await mystic.delete()
                
                await message.reply_photo(
                    photo=details["thumb"],
                    caption=_["play_10"].format(
                        details["title"].title(),
                        details["duration_min"],
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    has_spoiler=True
                )
                return await play_logs(message, streamtype=f"Searched on Youtube")
            else:
                buttons = track_markup(
                    _, track_id, message.from_user.id,
                    "c" if channel else "g", "f" if fplay else "d",
                )
                await mystic.delete()
                
                await message.reply_photo(
                    photo=img,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    has_spoiler=True
                )
                return await play_logs(message, streamtype=f"URL Searched Inline")

# ✅ FIX: Fixed the syntax error at the end of the file.
@app.on_callback_query(filters.regex("MusicStream") & ~BANNED_USERS)
@languageCB
async def play_music(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    vidid, user_id, mode, cplay, fplay = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except:
        return
    user_name = CallbackQuery.from_user.first_name
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except:
        pass
    mystic = await CallbackQuery.message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    
    # Structure aur syntax complete kar diya gaya hai
    try:
        details, track_id = await YouTube.track(vidid)
        await stream(
            _,
            mystic,
            CallbackQuery.from_user.id,
            details,
            chat_id,
            user_name,
            CallbackQuery.message.chat.id,
            video=False,
            streamtype="youtube",
            forceplay=fplay,
        )
        await mystic.delete()
    except Exception as e:
        ex_type = type(e).__name__
        err = _["general_2"].format(ex_type)
        return await mystic.edit_text(err)
