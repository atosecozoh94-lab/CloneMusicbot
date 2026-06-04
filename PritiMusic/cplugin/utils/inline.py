from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# --- STATIC BUTTONS ---
buttons = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="▷", callback_data="resume_cb"),
            InlineKeyboardButton(text="II", callback_data="pause_cb"),
            InlineKeyboardButton(text="‣‣I", callback_data="skip_cb"),
            InlineKeyboardButton(text="▢", callback_data="end_cb"),
        ],
        [
            InlineKeyboardButton(text="ʏᴛ-ᴀᴘɪ sᴛᴀᴛᴜs 💌", callback_data="yt_api_status")
        ]
    ]
)

close_key = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton(text="ʏᴛ-ᴀᴘɪ sᴛᴀᴛᴜs 💌", callback_data="yt_api_status")],
        [InlineKeyboardButton(text="✯ ᴄʟᴏsᴇ ✯", callback_data="close")]
    ]
)


# --- DYNAMIC STREAM MARKUP (For Live Progress Bar) ---
def stream_markup(chat_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="▷", callback_data=f"ADMIN Resume|{chat_id}"),
                InlineKeyboardButton(text="II", callback_data=f"ADMIN Pause|{chat_id}"),
                InlineKeyboardButton(text="‣‣I", callback_data=f"ADMIN Skip|{chat_id}"),
                InlineKeyboardButton(text="▢", callback_data=f"ADMIN Stop|{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="ʏᴛ-ᴀᴘɪ sᴛᴀᴛᴜs 💌", callback_data="yt_api_status")
            ],
            [
                InlineKeyboardButton(text="✯ ᴄʟᴏsᴇ ✯", callback_data="close")
            ]
        ]
    )

def telegram_markup(chat_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="▷", callback_data=f"ADMIN Resume|{chat_id}"),
                InlineKeyboardButton(text="II", callback_data=f"ADMIN Pause|{chat_id}"),
                InlineKeyboardButton(text="‣‣I", callback_data=f"ADMIN Skip|{chat_id}"),
                InlineKeyboardButton(text="▢", callback_data=f"ADMIN Stop|{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="ʏᴛ-ᴀᴘɪ sᴛᴀᴛᴜs 💌", callback_data="yt_api_status")
            ],
            [
                InlineKeyboardButton(text="✯ ᴄʟᴏsᴇ ✯", callback_data="close")
            ]
        ]
    )

def close_markup(_):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="ʏᴛ-ᴀᴘɪ sᴛᴀᴛᴜs 💌", callback_data="yt_api_status")
            ],
            [
                InlineKeyboardButton(text="✯ ᴄʟᴏsᴇ ✯", callback_data="close")
            ]
        ]
    )
