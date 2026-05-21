import time
import random
import asyncio
import logging
from pyrogram import filters, Client
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, InputMediaPhoto, InputMediaVideo
from py_yt import VideosSearch

import config
from PritiMusic import app
from PritiMusic.misc import _boot_
from PritiMusic.plugins.sudo.sudoers import sudoers_list
from PritiMusic.utils.formatters import get_readable_time

# Config Imports
from config import BANNED_USERS, OWNER_ID, START_IMG_URL, CMBOT, EFFECT_ID

# Module Imports
from PritiMusic.utils.decorators.language import LanguageStart, languageCB
from strings import get_string
from PritiMusic.utils.database.clonedb import get_owner_id_from_db, get_cloned_support_chat, get_cloned_support_channel
from PritiMusic.utils.database import add_served_user_clone, add_served_chat_clone
from PritiMusic.utils.database import clonebotdb

# Extra Import for Transfer Logic
from PritiMusic.core.mongo import mongodb
cloneownerdb = mongodb.cloneownerdb

# Initialize logging
LOG = logging.getLogger(__name__)

# =====================================================================
# INTERNAL BUTTON HELPERS (Defined inside same file)
# =====================================================================

def make_start_panel(bot_username, owner_url, 
                     txt_add, txt_support, txt_channel, txt_owner, txt_help, 
                     support_chat, support_channel,
                     custom_btn=None, btn_pos="TOP"):
    
    # Base Buttons
    buttons = []

    # 1. Add to Group
    if txt_add != "HIDDEN":
        buttons.append([InlineKeyboardButton(text=txt_add, url=f"https://t.me/{bot_username}?startgroup=true")])

    # 2. Help Button
    if txt_help != "HIDDEN":
        buttons.append([InlineKeyboardButton(text=txt_help, callback_data="settings_back_helper")])

    # 3. Support & Channel (Row)
    row_support = []
    if txt_support != "HIDDEN":
        row_support.append(InlineKeyboardButton(text=txt_support, url=support_chat))
    if txt_channel != "HIDDEN":
        row_support.append(InlineKeyboardButton(text=txt_channel, url=support_channel))
    if row_support:
        buttons.append(row_support)

    # 4. Owner Button
    if txt_owner != "HIDDEN":
        buttons.append([InlineKeyboardButton(text=txt_owner, url=owner_url)])

    # --- Custom Button Logic ---
    if custom_btn and custom_btn.get("text"):
        c_btn = InlineKeyboardButton(text=custom_btn["text"], url=custom_btn["url"])
        
        if btn_pos in ["UP", "TOP"]:
            buttons.insert(0, [c_btn])
        elif btn_pos in ["DOWN", "BOTTOM"]:
            buttons.append([c_btn])
        elif btn_pos in ["MID", "MIDDLE"]:
            # Insert in middle (after Add to Group)
            if len(buttons) >= 1:
                buttons.insert(1, [c_btn])
            else:
                buttons.append([c_btn])
        elif btn_pos == "LEFT":
             if buttons and isinstance(buttons[0], list): buttons[0].insert(0, c_btn)
             else: buttons.insert(0, [c_btn])
        elif btn_pos == "RIGHT":
             if buttons and isinstance(buttons[0], list): buttons[0].append(c_btn)
             else: buttons.insert(0, [c_btn])
        else:
            buttons.insert(0, [c_btn])

    return InlineKeyboardMarkup(buttons)


def make_gp_panel(bot_username, txt_add, txt_support, support_chat):
    buttons = [
        [
            InlineKeyboardButton(text=txt_add, url=f"https://t.me/{bot_username}?startgroup=true"),
            InlineKeyboardButton(text=txt_support, url=support_chat),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# =====================================================================
# Database Helpers
# =====================================================================

async def get_start_image(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_image")

async def get_start_caption(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_caption")

async def get_start_button(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_button")

async def get_start_btn_pos(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_btn_pos", "TOP")

async def get_start_video(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_video")

async def get_start_sticker(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_sticker")

async def get_start_animation(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_animation")

async def get_start_reaction(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_reaction")

async def get_start_effect(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_effect")

async def get_custom_btn_text(bot_id, key, default_text):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    val = d.get(f"btn_{key}", default_text)
    return val

# ✅ Helper to Add Random Content
async def add_start_content(bot_id, key, value):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    current = d.get(key)
    
    if current:
        # Backward compatibility check
        if isinstance(current, dict):
            current = f"{current['text']} - {current['url']}" 

        if value in current:
            return False 
        final_value = f"{current}|||{value}"
    else:
        final_value = value
        
    await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {key: final_value}}, upsert=True)
    return True

# --- General Helpers ---

def get_random_start_image():
    if START_IMG_URL:
        if isinstance(START_IMG_URL, list):
            return random.choice(START_IMG_URL)
        return START_IMG_URL
    return "https://graph.org/file/f464ff7c9a134295011ff-f58e0c87cd8bf16b25.jpg"

def format_link(val):
    if not val:
        return "https://t.me/Telegram" 
    if "https://" in val or "http://" in val:
        return val
    return f"https://t.me/{val}"

def get_mention_html(user_id, name):
    return f'<a href="tg://user?id={user_id}">{name}</a>'

# =====================================================================
# START COMMAND (PRIVATE)
# =====================================================================

@Client.on_message(filters.command("start") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    a = await client.get_me()
    bot_id = a.id
    await add_served_user_clone(message.from_user.id, bot_id)

    # 1. Loading Animation
    raw_sticker, raw_animation = await asyncio.gather(
        get_start_sticker(bot_id),
        get_start_animation(bot_id)
    )
    
    custom_sticker = random.choice(raw_sticker.split("|||")) if raw_sticker else None
    custom_animation = random.choice(raw_animation.split("|||")) if raw_animation else None
    
    loading = None

    if custom_sticker:
        try:
            loading = await message.reply_sticker(custom_sticker)
            await asyncio.sleep(2)
        except:
            pass
    elif custom_animation:
        try:
            loading = await message.reply_animation(custom_animation)
            await asyncio.sleep(2)
        except:
             pass
    else:
        # Original Loading Animation
        anim_frames = ["<b>ʟᴏᴀᴅɪɴɢ</b>", "<b>ʟᴏᴀᴅɪɴɢ.</b>", "<b>ʟᴏᴀᴅɪɴɢ..</b>", "<b>ʟᴏᴀᴅɪɴɢ...</b>"]
        try:
            loading = await message.reply_text(anim_frames[0])
            for frame in anim_frames[1:]:
                await asyncio.sleep(0.3)
                try:
                    await loading.edit_text(frame, parse_mode=ParseMode.HTML)
                except:
                    pass
        except:
            pass

    # ✅ Optimized: Fetch All Data in Parallel (Fastest Way)
    (
        C_BOT_OWNER_ID,
        raw_support,
        raw_channel,
        txt_add,
        txt_support,
        txt_channel,
        txt_owner,
        txt_help,
        raw_custom_btn,
        btn_pos,
        raw_video,
        raw_img,
        raw_caption,
        raw_reaction,
        raw_effect
    ) = await asyncio.gather(
        get_owner_id_from_db(bot_id),
        get_cloned_support_chat(bot_id),
        get_cloned_support_channel(bot_id),
        get_custom_btn_text(bot_id, "add", _["S_B_3"]),
        get_custom_btn_text(bot_id, "support", _["S_B_9"]),
        get_custom_btn_text(bot_id, "channel", _["S_B_6"]),
        get_custom_btn_text(bot_id, "owner", _["C_B_2"]),
        get_custom_btn_text(bot_id, "help", _["S_B_4"]),
        get_start_button(bot_id),
        get_start_btn_pos(bot_id),
        get_start_video(bot_id),
        get_start_image(bot_id),
        get_start_caption(bot_id),
        get_start_reaction(bot_id),
        get_start_effect(bot_id),
    )

    C_SUPPORT_CHAT = format_link(raw_support)
    C_SUPPORT_CHANNEL = format_link(raw_channel)
    OWNER_URL = f"tg://openmessage?user_id={C_BOT_OWNER_ID}"

    # ✅ 1. RANDOM REACTION LOGIC (Custom or Default)
    if raw_reaction:
        reaction_emoji = random.choice(raw_reaction.split("|||"))
    else:
        # Default Random Reactions
        reaction_emoji = random.choice(["🔥", "❤️", "🥰", "😍", "👍", "⚡", "🎉"])
    
    try:
        await message.react(reaction_emoji)
    except:
        pass

    try:
        if loading: await loading.delete()
    except:
        pass

    # Inline Arguments
    if len(message.text.split()) > 1:
        arg = message.text.split(None, 1)[1]
        
        if arg.startswith("help"):
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(_["S_B_9"], url=C_SUPPORT_CHAT)]])
            return await message.reply_photo(
                photo=get_random_start_image(),
                caption=_["help_1"].format(C_SUPPORT_CHAT),
                reply_markup=keyboard,
                has_spoiler=True
            )
        if arg.startswith("sud"):
            return await sudoers_list(client=client, message=message, _=_)
        if arg.startswith("inf"):
            m = await message.reply_text("🔎")
            q = arg.replace("info_", "", 1)
            try:
                results = await VideosSearch(f"https://www.youtube.com/watch?v={q}", limit=1).next()
                result = results["result"][0]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                caption = _["start_6"].format(result["title"], result["duration"], result["viewCount"]["short"], result["publishedTime"], result["channel"]["link"], result["channel"]["name"], a.mention)
                key = InlineKeyboardMarkup([[InlineKeyboardButton(_["S_B_8"], url=result["link"]), InlineKeyboardButton(_["S_B_9"], url=C_SUPPORT_CHAT)]])
                await m.delete()
                return await message.reply_photo(photo=thumbnail, caption=caption, reply_markup=key, has_spoiler=True)
            except Exception as e:
                LOG.error(e)
                return await m.edit_text("❌ Error fetching info.")

    # Custom Button Data Logic
    custom_button_data = None
    if raw_custom_btn:
        if isinstance(raw_custom_btn, dict):
            custom_button_data = raw_custom_btn
        elif isinstance(raw_custom_btn, str):
            chosen_str = random.choice(raw_custom_btn.split("|||"))
            if "-" in chosen_str:
                txt, url = chosen_str.split("-", 1)
                custom_button_data = {"text": txt.strip(), "url": url.strip()}
    
    # Generate Buttons using Internal Function
    markup = make_start_panel(a.username, OWNER_URL,
                              txt_add, txt_support, txt_channel, txt_owner, txt_help,
                              C_SUPPORT_CHAT, C_SUPPORT_CHANNEL,
                              custom_button_data, btn_pos)

    # Media & Caption Logic
    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    custom_caption = random.choice(raw_caption.split("|||")) if raw_caption else None
    
    user_mention = get_mention_html(message.from_user.id, message.from_user.first_name)
    bot_mention = get_mention_html(a.id, a.first_name)
    
    if custom_caption:
        try:
            caption = custom_caption.format(
                name=user_mention,
                firstname=message.from_user.first_name,
                botname=bot_mention,
                username=a.username
            )
        except:
            caption = custom_caption
    else:
        # ✅ ONLY WELCOME MESSAGE CHANGED
        formatted_text = (
            f"нєу ʙᴀʙʏ 𓂃⃪𑪖{user_mention}, 🥀\n"
            f"๏ ᴛʜɪs ɪs {bot_mention} : ғᴀsᴛ & ᴘᴏᴡᴇʀғᴜʟ ᴛɢ ᴍᴜsɪᴄ ʙᴏᴛ.\n"
            f"๏ sᴍᴏᴏᴛʜ ʙᴇᴀᴛs • sᴛᴀʙʟᴇ & sᴇᴀᴍʟᴇss ᴍᴜsɪᴄ ғʟᴏᴡ.\n"
            f"๏ ɴᴇᴡ ᴠᴇʀsɪᴏɴ ᴡɪᴛʜ sᴜᴘᴇʀ ғᴀsᴛ ʏᴏᴜᴛᴜʙᴇ ᴀᴘɪ ʙᴀsᴇᴅ.\n"
            f"•── ⋅ ⋅ ⋅ ────── ⋅  ⋅ ────── ⋅ ⋅ ⋅ ──•\n"
            f"๏ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴩ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs."
        )
        caption = f"<blockquote expandable>{formatted_text}</blockquote>"

    # ✅ 2. RANDOM EFFECT LOGIC [FIXED]
    if raw_effect:
        effect = random.choice(raw_effect.split("|||"))
    else:
        effect = random.choice(EFFECT_ID)
    
    # 🔥 CRITICAL FIX: Convert Effect ID to INT to prevent Crash
    try:
        effect = int(effect)
    except:
        effect = None

    if start_video:
        try:
            return await message.reply_video(start_video, caption=caption, reply_markup=markup, message_effect_id=effect, has_spoiler=True, parse_mode=ParseMode.HTML)
        except:
            pass
    
    photo = start_img if start_img else get_random_start_image()
    await message.reply_photo(photo, caption=caption, reply_markup=markup, message_effect_id=effect, has_spoiler=True, parse_mode=ParseMode.HTML)

# =====================================================================
# START COMMAND (GROUP)
# =====================================================================

@Client.on_message(filters.command("start") & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    a = await client.get_me()
    bot_id = a.id
    uptime = get_readable_time(int(time.time() - _boot_))
    
    # Optimized Group Fetch
    raw_support, txt_add, txt_support, raw_video, raw_img = await asyncio.gather(
        get_cloned_support_chat(a.id),
        get_custom_btn_text(a.id, "add", _["S_B_1"]),
        get_custom_btn_text(a.id, "support", _["S_B_2"]),
        get_start_video(bot_id),
        get_start_image(bot_id)
    )

    C_SUPPORT_CHAT = format_link(raw_support)

    markup = make_gp_panel(a.username, txt_add, txt_support, C_SUPPORT_CHAT)
    
    caption = _["start_1"].format(a.mention, uptime)
    
    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    
    if start_video:
        try:
            return await message.reply_video(start_video, caption=caption, reply_markup=markup, has_spoiler=True)
        except:
            pass
    
    photo = start_img if start_img else get_random_start_image()
    await message.reply_photo(photo, caption=caption, reply_markup=markup, has_spoiler=True)
    await add_served_chat_clone(message.chat.id, a.id)

# =====================================================================
# CALLBACKS & FAST ACTIONS (Super Fast Back Button)
# =====================================================================

@Client.on_callback_query(filters.regex("settingsback_home") & ~BANNED_USERS)
@languageCB
async def home_back_handler(client, CallbackQuery, _):
    a = await client.get_me()
    bot_id = a.id

    # ✅ SUPER FAST: Fetching all Database values in ONE GO using asyncio.gather
    (
        C_BOT_OWNER_ID,
        raw_support,
        raw_channel,
        txt_add,
        txt_support,
        txt_channel,
        txt_owner,
        txt_help,
        raw_custom_btn,
        btn_pos,
        raw_video,
        raw_img,
        raw_caption,
        raw_effect
    ) = await asyncio.gather(
        get_owner_id_from_db(bot_id),
        get_cloned_support_chat(bot_id),
        get_cloned_support_channel(bot_id),
        get_custom_btn_text(bot_id, "add", _["S_B_3"]),
        get_custom_btn_text(bot_id, "support", _["S_B_9"]),
        get_custom_btn_text(bot_id, "channel", _["S_B_6"]),
        get_custom_btn_text(bot_id, "owner", _["C_B_2"]),
        get_custom_btn_text(bot_id, "help", _["S_B_4"]),
        get_start_button(bot_id),
        get_start_btn_pos(bot_id),
        get_start_video(bot_id),
        get_start_image(bot_id),
        get_start_caption(bot_id),
        get_start_effect(bot_id),
    )

    C_SUPPORT_CHAT = format_link(raw_support)
    C_SUPPORT_CHANNEL = format_link(raw_channel)
    OWNER_URL = f"tg://openmessage?user_id={C_BOT_OWNER_ID}"

    custom_button_data = None
    if raw_custom_btn:
        if isinstance(raw_custom_btn, dict):
            custom_button_data = raw_custom_btn
        elif isinstance(raw_custom_btn, str):
            chosen_str = random.choice(raw_custom_btn.split("|||"))
            if "-" in chosen_str:
                txt, url = chosen_str.split("-", 1)
                custom_button_data = {"text": txt.strip(), "url": url.strip()}
    
    markup = make_start_panel(a.username, OWNER_URL,
                              txt_add, txt_support, txt_channel, txt_owner, txt_help,
                              C_SUPPORT_CHAT, C_SUPPORT_CHANNEL,
                              custom_button_data, btn_pos)

    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    custom_caption = random.choice(raw_caption.split("|||")) if raw_caption else None
    
    user_mention = get_mention_html(CallbackQuery.from_user.id, CallbackQuery.from_user.first_name)
    bot_mention = get_mention_html(a.id, a.first_name)
    
    if custom_caption:
        try:
            caption = custom_caption.format(name=user_mention, firstname=CallbackQuery.from_user.first_name, botname=bot_mention, username=a.username)
        except:
            caption = custom_caption
    else:
        # ✅ ONLY WELCOME MESSAGE CHANGED
        formatted_text = (
            f"нєу ʙᴀʙʏ 𓂃⃪𑪖{user_mention}, 🥀\n"
            f"๏ ᴛʜɪs ɪs {bot_mention} : ғᴀsᴛ & ᴘᴏᴡᴇʀғᴜʟ ᴛɢ ᴍᴜsɪᴄ ʙᴏᴛ.\n"
            f"๏ sᴍᴏᴏᴛʜ ʙᴇᴀᴛs • sᴛᴀʙʟᴇ & sᴇᴀᴍʟᴇss ᴍᴜsɪᴄ ғʟᴏᴡ.\n"
            f"๏ ɴᴇᴡ ᴠᴇʀsɪᴏɴ ᴡɪᴛʜ sᴜᴘᴇʀ ғᴀsᴛ ʏᴏᴜᴛᴜʙᴇ ᴀᴘɪ ʙᴀsᴇᴅ.\n"
            f"•── ⋅ ⋅ ⋅ ────── ⋅  ⋅ ────── ⋅ ⋅ ⋅ ──•\n"
            f"๏ ᴄʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴩ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs."
        )
        caption = f"<blockquote expandable>{formatted_text}</blockquote>"

    # ✅ Random Effect Logic (Callback)
    if raw_effect:
        effect = random.choice(raw_effect.split("|||"))
    else:
        effect = random.choice(EFFECT_ID)
    
    # 🔥 FIX: Convert to Int
    try:
        effect = int(effect)
    except:
        effect = None

    try:
        if start_video:
            await CallbackQuery.edit_message_media(media=InputMediaVideo(media=start_video, caption=caption), reply_markup=markup)
        else:
            photo = start_img if start_img else get_random_start_image()
            await CallbackQuery.edit_message_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=markup)
    except Exception as e:
        try:
            await CallbackQuery.message.delete()
        except:
            pass
        if start_video:
            await CallbackQuery.message.reply_video(start_video, caption=caption, reply_markup=markup, message_effect_id=effect, has_spoiler=True, parse_mode=ParseMode.HTML)
        else:
            photo = start_img if start_img else get_random_start_image()
            await CallbackQuery.message.reply_photo(photo, caption=caption, reply_markup=markup, message_effect_id=effect, has_spoiler=True, parse_mode=ParseMode.HTML)

# =====================================================================
# MANAGEMENT & SETTINGS
# =====================================================================

@Client.on_message(filters.command(["transfer", "transferowner"]) & ~BANNED_USERS)
async def transfer_owner(client, message):
    pass # Aapka code yahan ke aage jaisa tha waisa lagaiye
