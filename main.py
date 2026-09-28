import os
import secrets
import math
import sqlite3
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from database import (
    create_database,
    get_statistics,
    add_user,
    get_user,
    get_all_users,
    update_user_rank,
    activate_subscription,
    check_subscription,
    deactivate_expired_users,
    add_video,
    get_videos_for_rank,
    get_all_videos,
    delete_video,
    create_payment,
    get_payment,
    get_pending_payments,
    update_payment_status,
    get_active_users_for_video_rank,
    create_invite_link,
    get_invite_link,
    use_invite_link,
)


# ==========================================
# SOZLAMALAR
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 8504784898


# ==========================================
# OBUNA NARXLARI
# ==========================================

BRONZE_PRICE = 50000
SILVER_PRICE = 80000
GOLD_PRICE = 120000


# ==========================================
# KARTA
# ==========================================

CARD_NUMBER = "9860 1201 2590 1047"
CARD_OWNER = "Suhrob Ismatulloyev"


# ==========================================
# START
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    add_user(
        user.id,
        user.username,
        user.first_name
    )

    # ======================================
    # INVITE LINKNI TEKSHIRISH
    # ======================================

    if context.args:

        invite_token = context.args[0]

        invite = get_invite_link(
            invite_token
        )

        if not invite:

            await update.message.reply_text(
                "❌ Bu invite link mavjud emas."
            )

            return

        if invite[4] == 1:

            await update.message.reply_text(
                "❌ Bu invite link allaqachon "
                "ishlatilgan."
            )

            return

        result = use_invite_link(
            invite_token,
            user.id
        )

        if result is False:

            await update.message.reply_text(
                "❌ Bu invite link allaqachon "
                "ishlatilgan."
            )

            return

        if result is None:

            await update.message.reply_text(
                "❌ Invite link topilmadi."
            )

            return

        invite_rank = result["rank"]
        invite_days = result["days"]

        update_user_rank(
            user.id,
            invite_rank
        )

        activate_subscription(
            user.id,
            invite_days
        )

        await update.message.reply_text(

            "🎉 INVITE LINK QABUL QILINDI!\n\n"

            f"🏅 Rank: {invite_rank}\n"
            f"📅 Obuna: {invite_days} kun\n"
            "🟢 Holat: Faol\n\n"

            "Endi sizga tegishli "
            "videolardan foydalanishingiz mumkin."
        )

    # ======================================
    # ODDIY START
    # ======================================

    user_data = get_user(
        user.id
    )

    rank = user_data[3]

    active = check_subscription(
        user.id
    )

    if active:

        status = "Faol ✅"

        keyboard = [

            [
                InlineKeyboardButton(
                    "🎬 Videolar",
                    callback_data="my_videos"
                )
            ],

            [
                InlineKeyboardButton(
                    "👤 Profil",
                    callback_data="profile"
                )
            ],

            [
                InlineKeyboardButton(
                    "💳 Obunani uzaytirish",
                    callback_data="buy_subscription"
                )
            ]

        ]

    else:

        status = "Faol emas ❌"

        keyboard = [

            [
                InlineKeyboardButton(
                    "💳 Obuna sotib olish",
                    callback_data="buy_subscription"
                )
            ],

            [
                InlineKeyboardButton(
                    "👤 Profil",
                    callback_data="profile"
                )
            ]

        ]

    await update.message.reply_text(

        f"Assalomu alaykum, "
        f"{user.first_name}! 👋\n\n"

        f"🏅 Rankingiz: {rank}\n"
        f"📅 Obuna: {status}\n\n"

        "Kerakli bo‘limni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# ID
# ==========================================

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    await update.message.reply_text(

        f"Sizning Telegram ID'ingiz:\n\n"
        f"{user.id}"
    )


# ==========================================
# ADMIN PANEL
# ==========================================

async def admin_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ Siz admin emassiz."
        )

        return

    await send_admin_panel(
        update.message
    )


async def send_admin_panel(message):

    keyboard = [

        [
            InlineKeyboardButton(
                "👥 Foydalanuvchilar",
                callback_data="users"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 Statistika",
                callback_data="statistics"
            )
        ],

        [
            InlineKeyboardButton(
                "🎬 Video qo‘shish",
                callback_data="add_video"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 Video o‘chirish",
                callback_data="delete_videos"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 To‘lovlar",
                callback_data="payments"
            )
        ],

        [
            InlineKeyboardButton(
                "🎟 Invite link",
                callback_data="invite_links"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 Xabarnoma",
                callback_data="notification"
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 Video qidirish",
                callback_data="search_videos"
            )
        ],
        [
            InlineKeyboardButton(
                "💾 Backup yaratish",
                callback_data="backup_database"
            )
        ]

    ]

    await message.reply_text(

        "🔐 ADMIN PANEL\n\n"
        "Kerakli bo‘limni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# VIDEO QABUL QILISH
# ==========================================

async def receive_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    if context.user_data.get(
        "adding_video"
    ) != True:

        return

    if not update.message.video:
        return

    file_id = update.message.video.file_id

    context.user_data[
        "video_file_id"
    ] = file_id

    context.user_data[
        "waiting_video_title"
    ] = True

    await update.message.reply_text(

        "✅ Video qabul qilindi!\n\n"

        "Endi video nomini yozing.\n\n"

        "Masalan:\n"
        "IELTS Listening Test 1"
    )


# ==========================================
# VIDEO NOMI
# ==========================================

async def receive_video_title(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if user.id != ADMIN_ID:
        return

    if context.user_data.get("waiting_video_search") is True:
        search_text = update.message.text.strip().casefold()
        context.user_data["waiting_video_search"] = False

        videos = get_all_videos()
        matches = [
            video for video in videos
            if search_text in str(video[2]).casefold()
            or search_text in str(video[0])
        ]

        if not matches:
            await update.message.reply_text(
                "🔎 Hech qanday video topilmadi."
            )
            return

        lines = ["🔎 QIDIRUV NATIJALARI:\\n"]
        for video in matches[:50]:
            lines.append(
                f"🎬 ID: {video[0]}\\n"
                f"📌 Nomi: {video[2]}\\n"
                f"🏅 Rank: {video[3]}\\n"
            )
        await update.message.reply_text("\\n".join(lines))
        return

    if context.user_data.get(
        "waiting_video_title"
    ) != True:

        return

    title = update.message.text.strip()

    if not title:

        await update.message.reply_text(
            "❌ Video nomi bo‘sh bo‘lishi mumkin emas."
        )

        return

    context.user_data[
        "video_title"
    ] = title

    context.user_data[
        "waiting_video_title"
    ] = False

    keyboard = [

        [
            InlineKeyboardButton(
                "🥉 Bronze",
                callback_data="save_video_Bronze"
            )
        ],

        [
            InlineKeyboardButton(
                "🥈 Silver",
                callback_data="save_video_Silver"
            )
        ],

        [
            InlineKeyboardButton(
                "🥇 Gold",
                callback_data="save_video_Gold"
            )
        ]

    ]

    await update.message.reply_text(

        "🏅 Bu video qaysi rank uchun?\n\n"

        "🥉 Bronze → barcha ranklar\n"
        "🥈 Silver → Silver + Gold\n"
        "🥇 Gold → faqat Gold\n\n"

        "Rankni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# OBUNA TARIFLARI
# ==========================================

async def show_subscription_plans(
    query
):

    keyboard = [

        [
            InlineKeyboardButton(
                f"🥉 Bronze — {BRONZE_PRICE:,} so‘m",
                callback_data="buy_Bronze"
            )
        ],

        [
            InlineKeyboardButton(
                f"🥈 Silver — {SILVER_PRICE:,} so‘m",
                callback_data="buy_Silver"
            )
        ],

        [
            InlineKeyboardButton(
                f"🥇 Gold — {GOLD_PRICE:,} so‘m",
                callback_data="buy_Gold"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Orqaga",
                callback_data="back_user"
            )
        ]

    ]

    await query.edit_message_text(

        "💳 OBUNA SOTIB OLISH\n\n"

        "Kerakli tarifni tanlang:\n\n"

        f"🥉 Bronze — {BRONZE_PRICE:,} so‘m / 30 kun\n"
        f"🥈 Silver — {SILVER_PRICE:,} so‘m / 30 kun\n"
        f"🥇 Gold — {GOLD_PRICE:,} so‘m / 30 kun",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# TO‘LOV MA'LUMOTI
# ==========================================

async def show_payment_info(
    query,
    context,
    rank
):

    if rank == "Bronze":

        amount = BRONZE_PRICE

    elif rank == "Silver":

        amount = SILVER_PRICE

    elif rank == "Gold":

        amount = GOLD_PRICE

    else:

        return

    context.user_data[
        "payment_rank"
    ] = rank

    context.user_data[
        "payment_amount"
    ] = amount

    keyboard = [

        [
            InlineKeyboardButton(
                "📸 Chek yuborish",
                callback_data="send_receipt"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Tariflar",
                callback_data="buy_subscription"
            )
        ]

    ]

    await query.edit_message_text(

        f"💳 {rank.upper()} OBUNA\n\n"

        f"💰 Narx: {amount:,} so‘m\n"
        f"📅 Muddat: 30 kun\n\n"

        f"💳 Karta:\n"
        f"{CARD_NUMBER}\n\n"

        f"👤 Karta egasi:\n"
        f"{CARD_OWNER}\n\n"

        "⚠️ To‘lovni amalga oshirgandan keyin "
        "chekni yuboring.\n\n"

        "Admin to‘lovni tekshiradi va tasdiqlaydi.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# CHEK SO‘RASH
# ==========================================

async def request_receipt(
    query,
    context
):

    rank = context.user_data.get(
        "payment_rank"
    )

    amount = context.user_data.get(
        "payment_amount"
    )

    if not rank or not amount:

        await query.edit_message_text(

            "❌ To‘lov ma'lumotlari topilmadi.\n\n"
            "Iltimos, jarayonni qaytadan boshlang."
        )

        return

    context.user_data[
        "waiting_receipt"
    ] = True

    await query.edit_message_text(

        "📸 CHEK YUBORISH\n\n"

        "To‘lov qilganingizdan keyin "
        "chek yoki to‘lov tasdiqlangan "
        "screenshotni shu yerga yuboring.\n\n"

        f"🏅 Tarif: {rank}\n"
        f"💰 Summa: {amount:,} so‘m\n\n"

        "Faqat rasm yuboring."
    )


# ==========================================
# CHEK QABUL QILISH
# ==========================================

async def receive_receipt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if context.user_data.get(
        "waiting_receipt"
    ) != True:

        return

    if not update.message.photo:

        await update.message.reply_text(

            "❌ Iltimos, to‘lov chekini "
            "rasm ko‘rinishida yuboring."
        )

        return

    photo = update.message.photo[-1]

    receipt_file_id = photo.file_id

    rank = context.user_data.get(
        "payment_rank"
    )

    amount = context.user_data.get(
        "payment_amount"
    )

    if not rank or not amount:

        await update.message.reply_text(

            "❌ To‘lov ma'lumotlari topilmadi.\n\n"
            "Iltimos, /start orqali qaytadan boshlang."
        )

        context.user_data.clear()

        return

    payment_id = create_payment(

        telegram_id=user.id,

        rank=rank,

        amount=amount,

        receipt_file_id=receipt_file_id
    )

    context.user_data.clear()

    await update.message.reply_text(

        "✅ CHEK QABUL QILINDI!\n\n"

        f"🧾 To‘lov ID: #{payment_id}\n"
        f"🏅 Tarif: {rank}\n"
        f"💰 Summa: {amount:,} so‘m\n\n"

        "⏳ Admin to‘lovni tekshiradi.\n"
        "Tasdiqlangandan keyin obunangiz faollashadi."
    )

    try:

        keyboard = [

            [
                InlineKeyboardButton(
                    "💰 To‘lovlarni ko‘rish",
                    callback_data="payments"
                )
            ]

        ]

        await context.bot.send_message(

            chat_id=ADMIN_ID,

            text=(

                "🔔 YANGI TO‘LOV!\n\n"

                f"🧾 To‘lov ID: #{payment_id}\n"
                f"👤 Foydalanuvchi: "
                f"{user.first_name}\n"
                f"🆔 Telegram ID: {user.id}\n"
                f"🏅 Rank: {rank}\n"
                f"💰 Summa: {amount:,} so‘m\n\n"

                "Chekni ko‘rish va tasdiqlash "
                "uchun tugmani bosing."
            ),

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

    except Exception as error:

        print(
            f"Admin xabari yuborilmadi: {error}"
        )


# ==========================================
# USER VIDEOLARI
# ==========================================
async def show_profile(query, user_id):
    user = get_user(user_id)

    if not user:
        await query.edit_message_text(
            "❌ Profil topilmadi."
        )
        return

    telegram_id = user[0]
    username = user[1]
    first_name = user[2]
    rank = user[3]
    subscription_start = user[4]
    subscription_end = user[5]
    is_active = user[6]

    # Obuna holatini tekshirish
    active = check_subscription(telegram_id)

    if active and subscription_end:
        try:
            end_date = datetime.fromisoformat(subscription_end)
            remaining_seconds = (end_date - datetime.now()).total_seconds()
            remaining_days = max(0, math.ceil(remaining_seconds / 86400))
            status = "🟢 Faol"
        except Exception:
            remaining_days = 0
            status = "🟢 Faol"
    else:
        remaining_days = 0
        status = "🔴 Faol emas"

    start_date = (
        subscription_start[:16]
        if subscription_start
        else "Mavjud emas"
    )

    end_date_text = (
        subscription_end[:16]
        if subscription_end
        else "Mavjud emas"
    )

    text = (
        "👤 <b>PROFILIM</b>\n\n"
        f"👨‍💼 Ism: <b>{first_name}</b>\n"
        f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
        f"🏆 Daraja: <b>{rank}</b>\n"
        f"📊 Obuna: <b>{status}</b>\n"
        f"📅 Boshlangan sana: <b>{start_date}</b>\n"
        f"📅 Tugash sanasi: <b>{end_date_text}</b>\n"
        f"⏳ Qolgan vaqt: <b>{remaining_days} kun</b>\n"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 Obunani uzaytirish",
                callback_data="buy_subscription"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Bosh sahifa",
                callback_data="back_user"
            )
        ]
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def show_user_videos(
    query,
    telegram_id
):

    user_data = get_user(
        telegram_id
    )

    if not user_data:

        await query.edit_message_text(
            "❌ Foydalanuvchi topilmadi."
        )

        return

    active = check_subscription(
        telegram_id
    )

    if not active:

        keyboard = [

            [
                InlineKeyboardButton(
                    "💳 Obuna sotib olish",
                    callback_data="buy_subscription"
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Bosh sahifa",
                    callback_data="back_user"
                )
            ]

        ]

        await query.edit_message_text(

            "🔒 Sizning obunangiz faol emas.\n\n"
            "Obuna sotib olib videolardan "
            "foydalanishingiz mumkin.",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    rank = user_data[3]

    videos = get_videos_for_rank(
        rank
    )

    if not videos:

        keyboard = [

            [
                InlineKeyboardButton(
                    "⬅️ Bosh sahifa",
                    callback_data="back_user"
                )
            ]

        ]

        await query.edit_message_text(

            "🎬 Hozircha siz uchun "
            "videolar mavjud emas.",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    for video in videos:

        file_id = video[1]

        title = video[2]

        video_rank = video[3]

        await query.message.chat.send_video(

            video=file_id,

            caption=(
                f"🎬 {title}\n"
                f"🏅 {video_rank}"
            ),

            protect_content=True
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "⬅️ Bosh sahifa",
                callback_data="back_user"
            )
        ]

    ]

    await query.message.chat.send_message(

        "✅ Barcha mavjud videolar yuborildi.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# ADMIN TO‘LOVLARI
# ==========================================

async def show_payments(
    query
):

    payments = get_pending_payments()

    if not payments:

        keyboard = [

            [
                InlineKeyboardButton(
                    "⬅️ Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            "💰 TO‘LOVLAR\n\n"
            "⏳ Hozircha kutilayotgan "
            "to‘lovlar yo‘q.",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    keyboard = []

    for payment in payments:

        payment_id = payment[0]

        rank = payment[2]

        amount = payment[3]

        keyboard.append(

            [
                InlineKeyboardButton(

                    f"🧾 #{payment_id} — "
                    f"{rank} — {amount:,} so‘m",

                    callback_data=(
                        f"payment_{payment_id}"
                    )
                )
            ]
        )

    keyboard.append(

        [
            InlineKeyboardButton(
                "⬅️ Admin panel",
                callback_data="back_admin"
            )
        ]
    )

    await query.edit_message_text(

        "💰 KUTILAYOTGAN TO‘LOVLAR\n\n"
        "Tekshirish uchun to‘lovni tanlang:",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# TO‘LOVNI KO‘RISH
# ==========================================

async def show_payment(
    query,
    payment_id
):

    payment = get_payment(
        payment_id
    )

    if not payment:

        await query.edit_message_text(
            "❌ To‘lov topilmadi."
        )

        return

    payment_id = payment[0]
    telegram_id = payment[1]
    rank = payment[2]
    amount = payment[3]
    receipt_file_id = payment[4]
    status = payment[5]
    created_at = payment[6]

    if status != "pending":

        await query.edit_message_text(

            "ℹ️ Bu to‘lov allaqachon ko‘rib chiqilgan.\n\n"
            f"Holat: {status}"
        )

        return

    try:

        await query.message.reply_photo(

            photo=receipt_file_id,

            caption=(

                "🧾 TO‘LOV CHEKI\n\n"

                f"ID: #{payment_id}\n"
                f"👤 Telegram ID: {telegram_id}\n"
                f"🏅 Rank: {rank}\n"
                f"💰 Summa: {amount:,} so‘m\n"
                f"📅 Sana: {created_at}"
            )
        )

    except Exception as error:

        print(
            f"Chek yuborishda xato: {error}"
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "✅ TASDIQLASH",
                callback_data=(
                    f"approve_payment_{payment_id}"
                )
            )
        ],

        [
            InlineKeyboardButton(
                "❌ RAD ETISH",
                callback_data=(
                    f"reject_payment_{payment_id}"
                )
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ To‘lovlar",
                callback_data="payments"
            )
        ]

    ]

    await query.message.reply_text(

        "⚠️ To‘lovni tekshiring.\n\n"
        "Chek haqiqiy bo‘lsa "
        "tasdiqlang.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# TO‘LOVNI TASDIQLASH
# ==========================================

async def approve_payment(
    query,
    context,
    payment_id
):

    payment = get_payment(
        payment_id
    )

    if not payment:

        await query.edit_message_text(
            "❌ To‘lov topilmadi."
        )

        return

    telegram_id = payment[1]
    rank = payment[2]
    status = payment[5]

    if status != "pending":

        await query.edit_message_text(

            "⚠️ Bu to‘lov allaqachon "
            "ko‘rib chiqilgan."
        )

        return

    update_user_rank(
        telegram_id,
        rank
    )

    activate_subscription(
        telegram_id,
        30
    )

    update_payment_status(
        payment_id,
        "approved"
    )

    try:

        await context.bot.send_message(

            chat_id=telegram_id,

            text=(

                "🎉 TO‘LOV TASDIQLANDI!\n\n"

                f"🏅 Rank: {rank}\n"
                "📅 Obuna: 30 kun\n"
                "🟢 Holat: Faol\n\n"

                "Endi barcha sizga tegishli "
                "videolardan foydalanishingiz mumkin."
            )
        )

    except Exception as error:

        print(
            f"Userga xabar yuborilmadi: {error}"
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "💰 Kutilayotgan to‘lovlar",
                callback_data="payments"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Admin panel",
                callback_data="back_admin"
            )
        ]

    ]

    await query.edit_message_text(

        "✅ TO‘LOV TASDIQLANDI!\n\n"

        f"🧾 To‘lov ID: #{payment_id}\n"
        f"👤 Telegram ID: {telegram_id}\n"
        f"🏅 Rank: {rank}\n"
        "📅 Obuna: 30 kun\n"
        "🟢 Holat: Faol\n\n"

        "Foydalanuvchiga xabar yuborildi.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# TO‘LOVNI RAD ETISH
# ==========================================

async def reject_payment(
    query,
    context,
    payment_id
):

    payment = get_payment(
        payment_id
    )

    if not payment:

        await query.edit_message_text(
            "❌ To‘lov topilmadi."
        )

        return

    telegram_id = payment[1]
    status = payment[5]

    if status != "pending":

        await query.edit_message_text(

            "⚠️ Bu to‘lov allaqachon "
            "ko‘rib chiqilgan."
        )

        return

    update_payment_status(
        payment_id,
        "rejected"
    )

    try:

        await context.bot.send_message(

            chat_id=telegram_id,

            text=(

                "❌ TO‘LOV RAD ETILDI.\n\n"

                f"🧾 To‘lov ID: #{payment_id}\n\n"

                "Iltimos, to‘lov chekini "
                "tekshiring va kerak bo‘lsa "
                "qaytadan to‘lov qilib, "
                "yangi chek yuboring."
            )
        )

    except Exception as error:

        print(
            f"Userga xabar yuborilmadi: {error}"
        )

    keyboard = [

        [
            InlineKeyboardButton(
                "💰 Kutilayotgan to‘lovlar",
                callback_data="payments"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Admin panel",
                callback_data="back_admin"
            )
        ]

    ]

    await query.edit_message_text(

        "❌ TO‘LOV RAD ETILDI!\n\n"

        f"🧾 To‘lov ID: #{payment_id}\n"
        f"👤 Telegram ID: {telegram_id}\n\n"

        "Foydalanuvchiga xabar yuborildi.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# INVITE LINK YARATISH
# ==========================================

async def create_invite_for_admin(
    query,
    context,
    rank
):

    token = (
        "INVITE_"
        + secrets.token_urlsafe(16)
    )

    create_invite_link(
        token,
        rank,
        30
    )

    bot_info = await context.bot.get_me()

    bot_username = bot_info.username

    invite_url = (
        f"https://t.me/{bot_username}"
        f"?start={token}"
    )

    keyboard = [

        [
            InlineKeyboardButton(
                "🎟 Yana link yaratish",
                callback_data="invite_links"
            )
        ],

        [
            InlineKeyboardButton(
                "🏠 Admin panel",
                callback_data="back_admin"
            )
        ]

    ]

    await query.edit_message_text(

        "✅ BIR MARTALIK INVITE LINK YARATILDI!\n\n"

        f"🏅 Rank: {rank}\n"
        "📅 Muddat: 30 kun\n"
        "🔢 Ishlatish: 1 marta\n\n"

        "🔗 LINK:\n"
        f"{invite_url}\n\n"

        "⚠️ Bu linkni faqat bitta odam "
        "ishlatishi mumkin.\n\n"

        "Linkni nusxalab kerakli odamga yuboring.",

        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# ==========================================
# BUTTON HANDLER
# ==========================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    data = query.data


    # ======================================
    # USER BUTTONS
    # ======================================

    if data == "profile":
        await show_profile(query, user.id)
        return

    if data == "my_videos":

        await show_user_videos(
            query,
            user.id
        )

        return


    if data == "buy_subscription":

        await show_subscription_plans(
            query
        )

        return


    if data.startswith("buy_"):

        rank = data.replace(
            "buy_",
            ""
        )

        await show_payment_info(
            query,
            context,
            rank
        )

        return


    if data == "send_receipt":

        await request_receipt(
            query,
            context
        )

        return


    if data == "back_user":

        user_data = get_user(
            user.id
        )

        if not user_data:
            return

        rank = user_data[3]

        active = check_subscription(
            user.id
        )

        if active:

            keyboard = [

                [
                    InlineKeyboardButton(
                        "🎬 Videolar",
                        callback_data="my_videos"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "👤 Profil",
                        callback_data="profile"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "💳 Obunani uzaytirish",
                        callback_data="buy_subscription"
                    )
                ]

            ]

        else:

            keyboard = [

                [
                    InlineKeyboardButton(
                        "💳 Obuna sotib olish",
                        callback_data="buy_subscription"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "👤 Profil",
                        callback_data="profile"
                    )
                ]

            ]

        await query.edit_message_text(

            f"Assalomu alaykum, "
            f"{user.first_name}! 👋\n\n"

            f"🏅 Rankingiz: {rank}\n"
            f"📅 Obuna: "
            f"{'Faol ✅' if active else 'Faol emas ❌'}",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # ADMIN SECURITY
    # ======================================

    if user.id != ADMIN_ID:

        await query.edit_message_text(
            "⛔ Siz admin emassiz."
        )

        return


    # ======================================
    # VIDEO SEARCH
    # ======================================

    if data == "search_videos":
        context.user_data["waiting_video_search"] = True
        await query.edit_message_text(
            "🔎 VIDEO QIDIRISH\\n\\n"
            "Video nomi yoki ID raqamini yuboring."
        )
        return

    # ======================================
    # DATABASE BACKUP
    # ======================================

    if data == "backup_database":
        db_candidates = [
            BASE_DIR / "bot.db",
            BASE_DIR / "database.db",
            BASE_DIR / "videos.db",
        ]
        db_path = next((path for path in db_candidates if path.exists()), None)

        if db_path is None:
            await query.edit_message_text(
                "❌ Ma’lumotlar bazasi fayli topilmadi."
            )
            return

        backup_dir = BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / (
            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        try:
            source = sqlite3.connect(str(db_path))
            destination = sqlite3.connect(str(backup_path))
            source.backup(destination)
            destination.close()
            source.close()

            with open(backup_path, "rb") as backup_file:
                await context.bot.send_document(
                    chat_id=ADMIN_ID,
                    document=backup_file,
                    filename=backup_path.name,
                    caption="✅ Bot ma’lumotlar bazasining backup nusxasi."
                )

            await query.edit_message_text(
                f"✅ Backup yaratildi va adminga yuborildi.\\n"
                f"📁 Fayl: {backup_path.name}"
            )
        except Exception as error:
            print(f"Backup xatosi: {error}")
            await query.edit_message_text(
                "❌ Backup yaratishda xatolik. Terminalni tekshiring."
            )
        return

    # ======================================
    # STATISTICS
    # ======================================

    if data == "statistics":

        stats = get_statistics()

        keyboard = [

            [
                InlineKeyboardButton(
                    "🔄 Yangilash",
                    callback_data="statistics"
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            "📊 <b>BOT STATISTIKASI</b>\n\n"

            f"👥 Jami foydalanuvchilar: "
            f"<b>{stats['total_users']}</b>\n\n"

            f"🟢 Faol obunalar: "
            f"<b>{stats['active_users']}</b>\n"

            f"⏰ Muddati tugaganlar: "
            f"<b>{stats['expired_users']}</b>\n"

            f"⚪ Faol emaslar: "
            f"<b>{stats['inactive_users']}</b>\n\n"

            f"🥉 Bronze: "
            f"<b>{stats['bronze_users']}</b>\n"

            f"🥈 Silver: "
            f"<b>{stats['silver_users']}</b>\n"

            f"🥇 Gold: "
            f"<b>{stats['gold_users']}</b>\n\n"

            f"🎬 Jami videolar: "
            f"<b>{stats['total_videos']}</b>\n"

            f"💰 Kutilayotgan to‘lovlar: "
            f"<b>{stats['pending_payments']}</b>",

            parse_mode="HTML",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # PAYMENTS
    # ======================================

    if data == "payments":

        await show_payments(
            query
        )

        return


    if data.startswith("payment_"):

        payment_id = int(
            data.replace(
                "payment_",
                ""
            )
        )

        await show_payment(
            query,
            payment_id
        )

        return


    if data.startswith(
        "approve_payment_"
    ):

        payment_id = int(
            data.replace(
                "approve_payment_",
                ""
            )
        )

        await approve_payment(
            query,
            context,
            payment_id
        )

        return


    if data.startswith(
        "reject_payment_"
    ):

        payment_id = int(
            data.replace(
                "reject_payment_",
                ""
            )
        )

        await reject_payment(
            query,
            context,
            payment_id
        )

        return


    # ======================================
    # ADD VIDEO
    # ======================================

    if data == "add_video":

        context.user_data.clear()

        context.user_data[
            "adding_video"
        ] = True

        await query.edit_message_text(

            "🎬 VIDEO QO‘SHISH\n\n"
            "Endi menga video yuboring."
        )

        return


    # ======================================
    # SAVE VIDEO
    # ======================================

    if data.startswith(
        "save_video_"
    ):

        rank = data.replace(
            "save_video_",
            ""
        )

        file_id = context.user_data.get(
            "video_file_id"
        )

        title = context.user_data.get(
            "video_title"
        )

        if not file_id or not title:

            await query.edit_message_text(

                "❌ Video ma'lumotlari "
                "topilmadi.\n\n"
                "Video qo‘shishni qaytadan "
                "boshlang."
            )

            context.user_data.clear()

            return

        add_video(
            file_id,
            title,
            rank
        )

        eligible_users = get_active_users_for_video_rank(
            rank
        )

        notified_count = 0
        failed_count = 0

        notification_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🎬 Videoni ko‘rish",
                        callback_data="my_videos"
                    )
                ]
            ]
        )

        for user_data in eligible_users:

            telegram_id = user_data[0]

            try:

                await context.bot.send_message(

                    chat_id=telegram_id,

                    text=(

                        "🔔 YANGI VIDEO!\n\n"

                        f"🎬 {title}\n"
                        f"🏅 Rank: {rank}\n\n"

                        "Sizning obunangiz ushbu "
                        "videoni ko‘rish imkonini beradi.\n\n"

                        "Videoni ko‘rish uchun "
                        "tugmani bosing:"
                    ),

                    reply_markup=notification_keyboard
                )

                notified_count += 1

            except Exception as error:

                failed_count += 1

                print(
                    f"Xabarnoma yuborilmadi "
                    f"(ID: {telegram_id}): {error}"
                )

        context.user_data.clear()

        keyboard = [

            [
                InlineKeyboardButton(
                    "🎬 Yana video qo‘shish",
                    callback_data="add_video"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            f"✅ VIDEO SAQLANDI!\n\n"

            f"🎬 Nomi: {title}\n"
            f"🏅 Rank: {rank}\n\n"

            "👥 Ko‘rinish:\n"

            "🥉 Bronze → barcha ranklar\n"
            "🥈 Silver → Silver + Gold\n"
            "🥇 Gold → faqat Gold\n\n"

            f"📢 Xabarnoma yuborildi: "
            f"{notified_count} ta user\n"

            f"⚠️ Yuborilmagan: "
            f"{failed_count} ta user",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # DELETE VIDEOS
    # ======================================

    if data == "delete_videos":

        videos = get_all_videos()

        if not videos:

            keyboard = [

                [
                    InlineKeyboardButton(
                        "⬅️ Admin panel",
                        callback_data="back_admin"
                    )
                ]

            ]

            await query.edit_message_text(

                "🗑 Hozircha videolar yo‘q.",

                reply_markup=InlineKeyboardMarkup(
                    keyboard
                )
            )

            return

        keyboard = []

        for video in videos:

            video_id = video[0]
            title = video[2]
            rank = video[3]

            keyboard.append(

                [
                    InlineKeyboardButton(

                        f"🗑 {video_id}. "
                        f"{title} [{rank}]",

                        callback_data=(
                            f"delete_video_{video_id}"
                        )
                    )
                ]
            )

        keyboard.append(

            [
                InlineKeyboardButton(
                    "⬅️ Admin panel",
                    callback_data="back_admin"
                )
            ]
        )

        await query.edit_message_text(

            "🗑 VIDEO O‘CHIRISH\n\n"
            "O‘chirmoqchi bo‘lgan videoni tanlang:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith(
        "delete_video_"
    ):

        video_id = int(
            data.replace(
                "delete_video_",
                ""
            )
        )

        keyboard = [

            [
                InlineKeyboardButton(
                    "✅ Ha, o‘chirish",
                    callback_data=(
                        f"confirm_delete_{video_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "❌ Yo‘q",
                    callback_data="delete_videos"
                )
            ]

        ]

        await query.edit_message_text(

            "⚠️ Rostdan ham bu videoni "
            "o‘chirmoqchimisiz?",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith(
        "confirm_delete_"
    ):

        video_id = int(
            data.replace(
                "confirm_delete_",
                ""
            )
        )

        deleted = delete_video(
            video_id
        )

        if deleted:

            message = "✅ Video o‘chirildi."

        else:

            message = "❌ Video topilmadi."

        keyboard = [

            [
                InlineKeyboardButton(
                    "🗑 Yana video o‘chirish",
                    callback_data="delete_videos"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            message,

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # USERS
    # ======================================

    if data == "users":

        users = get_all_users()

        if not users:

            await query.edit_message_text(
                "👥 Hozircha foydalanuvchilar yo‘q."
            )

            return

        keyboard = []

        for user_data in users:

            telegram_id = user_data[0]
            username = user_data[1]
            first_name = user_data[2]
            rank = user_data[3]

            if username:

                name = f"@{username}"

            else:

                name = first_name or "Noma'lum"

            keyboard.append(

                [
                    InlineKeyboardButton(

                        f"{name} — {rank}",

                        callback_data=(
                            f"user_{telegram_id}"
                        )
                    )
                ]
            )

        keyboard.append(

            [
                InlineKeyboardButton(
                    "⬅️ Orqaga",
                    callback_data="back_admin"
                )
            ]
        )

        await query.edit_message_text(

            "👥 FOYDALANUVCHILAR\n\n"
            "Foydalanuvchini tanlang:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # USER DETAILS
    # ======================================

    if data.startswith("user_"):

        telegram_id = int(
            data.replace(
                "user_",
                ""
            )
        )

        user_data = get_user(
            telegram_id
        )

        if not user_data:

            await query.edit_message_text(
                "❌ Foydalanuvchi topilmadi."
            )

            return

        username = user_data[1]
        first_name = user_data[2]
        rank = user_data[3]
        subscription_start = user_data[4]
        subscription_end = user_data[5]

        if username:

            username_text = f"@{username}"

        else:

            username_text = "Username yo‘q"

        active = check_subscription(
            telegram_id
        )

        if active:

            status = "Faol ✅"

        else:

            status = "Faol emas ❌"

        keyboard = [

            [
                InlineKeyboardButton(
                    "🥉 Bronze",
                    callback_data=(
                        f"rank_Bronze_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "🥈 Silver",
                    callback_data=(
                        f"rank_Silver_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "🥇 Gold",
                    callback_data=(
                        f"rank_Gold_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "💳 30 kunlik obunani faollashtirish",
                    callback_data=(
                        f"activate_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Foydalanuvchilar",
                    callback_data="users"
                )
            ]

        ]

        await query.edit_message_text(

            f"👤 FOYDALANUVCHI\n\n"

            f"Ism: {first_name}\n"
            f"Username: {username_text}\n"
            f"Telegram ID: {telegram_id}\n\n"

            f"🏅 Rank: {rank}\n"
            f"📅 Obuna: {status}\n\n"

            f"Boshlanishi:\n"
            f"{subscription_start or 'Hali yo‘q'}\n\n"

            f"Tugashi:\n"
            f"{subscription_end or 'Hali yo‘q'}\n\n"

            "Kerakli amalni tanlang:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # RANK
    # ======================================

    if data.startswith("rank_"):

        parts = data.split("_")

        if len(parts) != 3:

            await query.edit_message_text(
                "❌ Noto‘g‘ri rank ma'lumoti."
            )

            return

        new_rank = parts[1]

        telegram_id = int(
            parts[2]
        )

        if new_rank not in (
            "Bronze",
            "Silver",
            "Gold"
        ):

            await query.edit_message_text(
                "❌ Noto‘g‘ri rank."
            )

            return

        update_user_rank(
            telegram_id,
            new_rank
        )

        keyboard = [

            [
                InlineKeyboardButton(
                    "👤 Userni ko‘rish",
                    callback_data=(
                        f"user_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Foydalanuvchilar",
                    callback_data="users"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            f"✅ Rank o‘zgartirildi!\n\n"
            f"👤 Telegram ID: {telegram_id}\n"
            f"🏅 Yangi rank: {new_rank}",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    # ======================================
    # MANUAL ACTIVATE
    # ======================================

    if data.startswith(
        "activate_"
    ):

        telegram_id = int(
            data.replace(
                "activate_",
                ""
            )
        )

        activate_subscription(
            telegram_id,
            30
        )

        user_data = get_user(
            telegram_id
        )

        if not user_data:

            await query.edit_message_text(
                "❌ Foydalanuvchi topilmadi."
            )

            return

        keyboard = [

            [
                InlineKeyboardButton(
                    "👤 Userni ko‘rish",
                    callback_data=(
                        f"user_{telegram_id}"
                    )
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Foydalanuvchilar",
                    callback_data="users"
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            "✅ OBUNA FAOLLASHTIRILDI!\n\n"

            f"👤 Ism: {user_data[2]}\n"
            f"🏅 Rank: {user_data[3]}\n\n"

            f"📅 Boshlanishi:\n"
            f"{user_data[4]}\n\n"

            f"📅 Tugashi:\n"
            f"{user_data[5]}\n\n"

            "🟢 Holat: Faol\n"
            "⏳ 30 kun qo‘shildi.",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        try:

            await context.bot.send_message(

                chat_id=telegram_id,

                text=(

                    "🎉 OBUNANGIZ FAOLLASHTIRILDI!\n\n"

                    f"🏅 Rank: {user_data[3]}\n"
                    "📅 30 kunlik obuna berildi.\n"
                    "🟢 Holat: Faol\n\n"

                    "Endi siz o‘zingizga tegishli "
                    "videolardan foydalanishingiz mumkin."
                )
            )

        except Exception as error:

            print(
                f"Userga admin aktivatsiyasi haqida "
                f"xabar yuborilmadi: {error}"
            )

        return


    # ======================================
    # INVITE LINKS
    # ======================================

    if data == "invite_links":

        keyboard = [

            [
                InlineKeyboardButton(
                    "🥉 Bronze — 30 kun",
                    callback_data="create_invite_Bronze"
                )
            ],

            [
                InlineKeyboardButton(
                    "🥈 Silver — 30 kun",
                    callback_data="create_invite_Silver"
                )
            ],

            [
                InlineKeyboardButton(
                    "🥇 Gold — 30 kun",
                    callback_data="create_invite_Gold"
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            "🎟 INVITE LINK\n\n"

            "Bir martalik access link yaratish.\n\n"

            "Link ishlatilganda foydalanuvchiga "
            "tanlangan rank va 30 kunlik obuna beriladi.\n\n"

            "Kerakli rankni tanlang:",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


    if data.startswith(
        "create_invite_"
    ):

        rank = data.replace(
            "create_invite_",
            ""
        )

        if rank not in (
            "Bronze",
            "Silver",
            "Gold"
        ):

            await query.edit_message_text(
                "❌ Noto‘g‘ri rank."
            )

            return

        await create_invite_for_admin(
            query,
            context,
            rank
        )

        return


    # ======================================
    # BACK ADMIN
    # ======================================

    if data == "back_admin":

        await send_admin_panel(
            query.message
        )

        return


    # ======================================
    # NOTIFICATION
    # ======================================

    if data == "notification":

        keyboard = [

            [
                InlineKeyboardButton(
                    "⬅️ Admin panel",
                    callback_data="back_admin"
                )
            ]

        ]

        await query.edit_message_text(

            "📢 XABARNOMA\n\n"

            "Yangi video qo‘shilganda "
            "mos rankdagi faol foydalanuvchilarga "
            "avtomatik xabar yuboriladi.",

            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return


# ==========================================
# EXPIRATION
# ==========================================

async def check_expired_subscriptions(
    context: ContextTypes.DEFAULT_TYPE
):

    expired_users = deactivate_expired_users()

    if not expired_users:
        return

    for user in expired_users:

        telegram_id = user[0]
        first_name = user[1]
        rank = user[2]
        subscription_end = user[3]

        try:

            keyboard = [

                [
                    InlineKeyboardButton(
                        "💳 Obunani qayta faollashtirish",
                        callback_data="buy_subscription"
                    )
                ]

            ]

            if subscription_end:

                expired_date = subscription_end[:10]

            else:

                expired_date = "Noma'lum"

            message = (

                "⏰ <b>OBUNANGIZ TUGADI</b>\n\n"

                f"👤 {first_name}\n"
                f"🏆 Daraja: <b>{rank}</b>\n"
                f"📅 Tugagan sana: {expired_date}\n\n"

                "Videolarga kirish vaqtincha yopildi.\n\n"

                "Obunani qayta faollashtirish "
                "uchun quyidagi tugmani bosing."
            )

            await context.bot.send_message(

                chat_id=telegram_id,

                text=message,

                parse_mode="HTML",

                reply_markup=InlineKeyboardMarkup(
                    keyboard
                )
            )

            print(
                "Obunasi tugagan userga xabar yuborildi: "
                f"{telegram_id}"
            )

        except Exception as error:

            print(
                "Userga expiration xabari yuborishda "
                f"xatolik ({telegram_id}): {error}"
            )


# ==========================================
# MAIN
# ==========================================

def main():

    if not TOKEN:

        raise ValueError(
            "BOT_TOKEN .env faylida topilmadi!"
        )

    create_database()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # ======================================
    # START
    # ======================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # ======================================
    # ID
    # ======================================

    app.add_handler(
        CommandHandler(
            "id",
            my_id
        )
    )

    # ======================================
    # ADMIN
    # ======================================

    app.add_handler(
        CommandHandler(
            "admin",
            admin_panel
        )
    )

    # ======================================
    # BUTTONS
    # ======================================

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # ======================================
    # VIDEO
    # ======================================

    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            receive_video
        )
    )

    # ======================================
    # RECEIPT PHOTO
    # ======================================

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_receipt
        )
    )

    # ======================================
    # TEXT
    # ======================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_video_title
        )
    )

    # ======================================
    # EXPIRATION CHECK
    # ======================================

    app.job_queue.run_repeating(
        check_expired_subscriptions,
        interval=60,
        first=10
    )

    print("Bot ishga tushdi!")

    app.run_polling()


# ==========================================
# PROGRAM START
# ==========================================

if __name__ == "__main__":
    main()