import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
from PritiMusic.utils.decorators.language import language

# Main Bot Link (Where users can create a clone)
# Ideally, this should be in config, but hardcoding here works too.
BOT_LINK = "https://t.me/CLOONE_MUSIC_BOT"

# ✅ Helper to safely get Random Start Image
def get_random_start_img():
    if config.START_IMG_URL:
        if isinstance(config.START_IMG_URL, list):
            return random.choice(config.START_IMG_URL)
        return config.START_IMG_URL
    return "https://graph.org/file/b0c653f31190c72a55060-854eb9a703f571d442.mp4" # Fallback Image

@Client.on_message(filters.command("clone"))
@language
async def ping_clone(client: Client, message: Message, _):
    # ✅ Random Photo + Spoiler Logic
    await message.reply_photo(
        photo=get_random_start_img(),
        caption=_["NO_CLONE_MSG"],
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("ɢᴏ ᴀɴᴅ ᴄʟᴏɴᴇ", url=BOT_LINK)]
            ]
        ),
        has_spoiler=True  # ✨ Spoiler Added
    )
