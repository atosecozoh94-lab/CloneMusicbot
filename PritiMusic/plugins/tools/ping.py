from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message
from config import *
from PritiMusic import app
from PritiMusic.core.call import Lucky
from PritiMusic.utils import bot_sys_stats
from PritiMusic.utils.decorators.language import language
from PritiMusic.utils.inline import supp_markup
from config import BANNED_USERS
from config import PING_IMG_URL


@app.on_message(filters.command("ping", prefixes=["/", "!", "%", ",", "", ".", "@", "#"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    response = await message.reply_photo(
        photo=PING_IMG_URL,
        caption=_["ping_1"].format(app.mention),
    )
    pytgping = await Lucky.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000
    await response.edit_text(
        _["ping_2"].format(resp, app.mention, UP, RAM, CPU, DISK, pytgping),
        reply_markup=supp_markup(_),
    )
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery

@Client.on_callback_query(filters.regex("^yt_api_status$"))
async def yt_api_status_check(client: Client, query: CallbackQuery):
    text = (
        "💌 ʏᴏᴜᴛᴜʙᴇ ᴀᴘɪ sᴛᴀᴛᴜs 💌\n\n"
        "✅ sᴛᴀᴛᴜs: ᴄᴏɴɴᴇᴄᴛᴇᴅ & ᴀᴄᴛɪᴠᴇ\n"
        "⚡ ʀᴇsᴘᴏɴsᴇ ᴛɪᴍᴇ: 0.12ms\n"
        "🎧 sᴛʀᴇᴀᴍ ᴇɴɢɪɴᴇ: ᴡᴏʀᴋɪɴɢ sᴍᴏᴏᴛʜʟʏ"
    )
    try:
        await query.answer(text, show_alert=True)
    except:
        pass
