import json
import logging
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
BASE = Path.home() / "energy-ittifoq"
DATA_FILE = BASE / "energy_data.json"
TOKEN_FILE = Path.home() / ".config/energy-ittifoq/token"
OWNER_ID = 8772850121

def get_token():
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    import os
    return os.environ.get("BOT_TOKEN", "").strip()

def load_data():
    try:
        d = json.loads(DATA_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        d = {}
    d.setdefault("applications", {})
    d.setdefault("members", {})
    d.setdefault("admins", [OWNER_ID])
    d.setdefault("groups", {})
    if OWNER_ID not in d["admins"]:
        d["admins"].append(OWNER_ID)
    return d

data = load_data()

def save():
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
    )

def is_admin(uid):
    return uid == OWNER_ID or uid in data["admins"]

def main_menu(uid):
    rows = [
        [InlineKeyboardButton(
            "⚡ ENERGY ITTIFOQGA QO‘SHILISH",
            callback_data="join"
        )],
        [
            InlineKeyboardButton("👤 Holatim", callback_data="status"),
            InlineKeyboardButton("👥 ENERGY FAMILY", callback_data="family")
        ],
        [InlineKeyboardButton("ℹ️ Ittifoq haqida", callback_data="about")]
    ]
    if is_admin(uid):
        rows.append([InlineKeyboardButton(
            "👑 ADMIN PANEL", callback_data="admin"
        )])
    return InlineKeyboardMarkup(rows)

def join_keyboard(username):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ BOTNI GURUHGA QO‘SHISH",
            url=f"https://t.me/{username}?startgroup=true"
        )],
        [InlineKeyboardButton(
            "✅ TEKSHIRISH", callback_data="check_group"
        )],
        [InlineKeyboardButton(
            "❌ BEKOR QILISH", callback_data="cancel"
        )],
        [InlineKeyboardButton(
            "⬅️ ASOSIY MENYU", callback_data="home"
        )]
    ])

JOIN_TEXT = (
    "📝 ENERGY ITTIFOQga qo‘shilish\n\n"
    "🤖 1/2. Botni guruhga qo‘shing va administrator huquqini bering.\n\n"
    "👑 Arizani faqat guruh egasi yubora oladi.\n\n"
    "Keyin guruh ichida:\n/check\n"
    "buyrug‘ini yuboring."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.effective_message.reply_text(
        f"⚡ ENERGY ITTIFOQ ⚡\n\nAssalomu alaykum, {u.first_name}!\n"
        "Kerakli bo‘limni tanlang.",
        reply_markup=main_menu(u.id)
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not chat or chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text(
            "ℹ️ /check buyrug‘ini guruh ichida yuboring."
        )
        return

    try:
        owner = await context.bot.get_chat_member(chat.id, user.id)
        bot_member = await context.bot.get_chat_member(
            chat.id, context.bot.id
        )
    except Exception:
        await update.effective_message.reply_text(
            "❌ Tekshirib bo‘lmadi. Botga administrator huquqini bering."
        )
        return

    if owner.status != "creator":
        await update.effective_message.reply_text(
            "👑 Arizani faqat guruh egasi yubora oladi."
        )
        return

    if bot_member.status != "administrator":
        await update.effective_message.reply_text(
            "❌ Avval botni guruhga administrator qiling."
        )
        return

    gid = str(chat.id)
    data["groups"][gid] = {
        "id": chat.id,
        "title": chat.title or "Guruh",
        "owner_id": user.id,
        "owner_name": user.full_name
    }
    data["applications"][str(user.id)] = {
        "id": user.id,
        "name": user.full_name,
        "username": user.username or "",
        "group_id": chat.id,
        "group_title": chat.title or "Guruh"
    }
    save()

    await update.effective_message.reply_text(
        "✅ TEKSHIRUV MUVAFFAQIYATLI!\n\n"
        f"👥 Guruh: {chat.title}\n"
        "📝 Arizangiz admin ko‘rib chiqishi uchun yuborildi."
    )
    for admin in data["admins"]:
        try:
            await context.bot.send_message(
                admin,
                f"📝 YANGI ITTIFOQ ARIZASI\n\n"
                f"👤 Egasi: {user.full_name}\n"
                f"🆔 ID: {user.id}\n"
                f"👥 Guruh: {chat.title}\n"
                f"🆔 Guruh ID: {chat.id}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "✅ QABUL", callback_data=f"approve:{user.id}"
                    ),
                    InlineKeyboardButton(
                        "❌ RAD", callback_data=f"reject:{user.id}"
                    )
                ]])
            )
        except Exception:
            logging.exception("Admin xabarini yuborib bo‘lmadi")

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data["applications"].pop(uid, None)
    save()
    await update.effective_message.reply_text(
        "❌ Arizangiz bekor qilindi."
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    key = q.data

    if key == "join":
        await q.message.reply_text(
            JOIN_TEXT, reply_markup=join_keyboard(context.bot.username)
        )

    elif key == "check_group":
        app = data["applications"].get(str(uid))
        if str(uid) in data["members"]:
            await q.message.reply_text("✅ Siz ittifoq a'zosisiz.")
        elif app:
            await q.message.reply_text(
                "⏳ Arizangiz adminga yuborilgan.\n"
                "Guruh: " + app.get("group_title", "Guruh")
            )
        else:
            await q.message.reply_text(
                "🔎 Guruh hali tekshirilmagan.\n\n"
                "1. Botni guruhga qo‘shing.\n"
                "2. Botga administrator huquqini bering.\n"
                "3. Guruh egasi guruh ichida /check yuborsin."
            )

    elif key == "cancel":
        data["applications"].pop(str(uid), None)
        save()
        await q.message.reply_text(
            "❌ Ariza bekor qilindi.",
            reply_markup=main_menu(uid)
        )

    elif key == "home":
        await q.message.reply_text(
            "⚡ ENERGY ITTIFOQ", reply_markup=main_menu(uid)
        )

    elif key == "status":
        if str(uid) in data["members"]:
            msg = "✅ Siz ittifoq a'zosisiz."
        elif str(uid) in data["applications"]:
            msg = "⏳ Arizangiz ko‘rib chiqilmoqda."
        else:
            msg = "Siz hali ariza yubormagansiz."
        await q.message.reply_text(msg)


    elif key == "admin":
        if not is_admin(uid):
            await q.message.reply_text("⛔ Ruxsat yo‘q.")
            return

        await q.message.reply_text(
            "👑 ENERGY ITTIFOQ — ADMIN PANEL\n\n"
            f"📝 Arizalar: {len(data["applications"])}\n"
            f"👥 A'zolar: {len(data["members"])}\n"
            f"🏘 Guruhlar: {len(data["groups"])}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Arizalar", callback_data="applications")],
                [InlineKeyboardButton("👥 A'zolar", callback_data="family")],
                [InlineKeyboardButton("➕ A'ZO QO‘SHISH", callback_data="add_member")],
                [InlineKeyboardButton("➖ A'ZO OLIB TASHLASH", callback_data="remove_member")],
                [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
                [InlineKeyboardButton("📢 Xabar yuborish", callback_data="broadcast")],
                [InlineKeyboardButton("📌 XABARNI QADASH", callback_data="pin_info")],
                [InlineKeyboardButton("⬅️ Menyu", callback_data="home")]
            ])
        )

    elif key == "remove_member":
        if not is_admin(uid):
            await q.message.reply_text("⛔ Ruxsat yo‘q.")
            return

        context.user_data["remove_member"] = True

        await q.message.reply_text(
            "➖ A'ZO OLIB TASHLASH\n\n"
            "Olib tashlamoqchi bo‘lgan a'zoning Telegram ID sini yuboring.\n\n"
            "Masalan:\n"
            "7985663471"
        )

    elif key == "about":
        groups = data.get("groups", {})

        msg = "⚡ ENERGY ITTIFOQ\n\n"
        msg += "Birlik • Hurmat • Ishonch\n\n"
        msg += "🏘 AZO GURUHLAR:\n\n"

        if isinstance(groups, dict):
            items = groups.values()
        elif isinstance(groups, list):
            items = groups
        else:
            items = []

        found = False

        for n, g in enumerate(items, 1):
            if isinstance(g, dict):
                name = g.get("name") or g.get("title") or g.get("chat_title")
            else:
                name = str(g)

            if name:
                msg += f"{n}. {name}\n"
                found = True

        if not found:
            msg += "Hozircha guruhlar yo‘q.\n"

        await q.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ MENYU", callback_data="home")]
            ])
        )

    elif key == "add_member":
        if not is_admin(uid):
            await q.message.reply_text("⛔ Ruxsat yo‘q.")
            return

        context.user_data["add_member"] = True

        await q.message.reply_text(
            "➕ A'ZO QO‘SHISH\n\n"
            "Yangi a'zoning Telegram ID sini yuboring.\n\n"
            "Masalan:\n"
            "8772850121\n\n"
            "Keyin uning ismini yuborasiz."
        )

    elif key == "family":
        members = data.get("members", {})
        msg = "🌐 ENERGY FAMILY\n\n"
        msg += "Jamoamiz a'zolari:\n\n"

        buttons = []

        if isinstance(members, dict) and members:
            for mid, m in members.items():
                if isinstance(m, dict):
                    name = m.get("name", "A’zo")
                else:
                    name = str(m)

                buttons.append([
                    InlineKeyboardButton(
                        f"👤 {name} ↗",
                        url=f"tg://user?id={mid}"
                    )
                ])
        else:
            msg += "Hozircha a'zolar yo‘q.\n"

        buttons.append([
            InlineKeyboardButton(
                "⬅️ MENYU",
                callback_data="home"
            )
        ])

        await q.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif key == "applications":
        if not is_admin(uid):
            return
        if not data["applications"]:
            await q.message.reply_text("📝 Kutilayotgan arizalar yo‘q.")
            return
        for aid, a in list(data["applications"].items()):
            await q.message.reply_text(
                f"📝 ARIZA\n👤 {a.get('name')}\n"
                f"🆔 {aid}\n👥 {a.get('group_title', '-')}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "✅ Qabul", callback_data=f"approve:{aid}"
                    ),
                    InlineKeyboardButton(
                        "❌ Rad", callback_data=f"reject:{aid}"
                    )
                ]])
            )

    elif key == "stats":
        if is_admin(uid):
            await q.message.reply_text(
                f"📊 STATISTIKA\n\n👥 A'zolar: {len(data['members'])}\n"
                f"📝 Arizalar: {len(data['applications'])}\n"
                f"🏘 Guruhlar: {len(data['groups'])}"
            )

    elif key == "pin_info":
        if not is_admin(uid):
            await q.message.reply_text("⛔ Ruxsat yo‘q.")
            return

        await q.message.reply_text(
            "📌 XABARNI QADASH\n\n"
            "1️⃣ ENERGY ITTIFOQ guruhiga kiring.\n"
            "2️⃣ Qadamoqchi bo‘lgan xabarga Reply qiling.\n"
            "3️⃣ /pin yuboring.\n\n"
            "🤖 Bot xabarni avtomatik qadab qo‘yadi."
        )

    elif key == "broadcast":
        if is_admin(uid):
            context.user_data["broadcast"] = True
            await q.message.reply_text(
                "📢 Yuboriladigan xabarni yozing.\n"
                "/cancel bilan bekor qilishingiz mumkin."
            )

    elif key.startswith("approve:") or key.startswith("reject:"):
        if not is_admin(uid):
            await q.message.reply_text("⛔ Ruxsat yo‘q.")
            return
        aid = key.split(":", 1)[1]
        app = data["applications"].get(aid)
        if not app:
            await q.message.reply_text("Ariza topilmadi yoki ko‘rib chiqilgan.")
            return
        if key.startswith("approve:"):
            data["members"][aid] = {
                "id": int(aid),
                "name": app.get("name", "A’zo"),
                "group_id": app.get("group_id")
            }
            data["applications"].pop(aid, None)
            save()
            await q.message.reply_text("✅ Ariza qabul qilindi.")
            try:
                await context.bot.send_message(
                    int(aid), "🎉 ENERGY ITTIFOQ arizangiz qabul qilindi!"
                )
            except Exception:
                pass
        else:
            data["applications"].pop(aid, None)
            save()
            await q.message.reply_text("❌ Ariza rad etildi.")
            try:
                await context.bot.send_message(
                    int(aid), "Arizangiz rad etildi."
                )
            except Exception:
                pass

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not is_admin(uid):
        return

    msg = update.effective_message
    text_msg = (msg.text or "").strip()

    # =========================
    # A'ZO QO'SHISH — ISM BOSQICHI
    # =========================
    if context.user_data.get("add_member_name"):
        member_id = context.user_data.get("add_member_id")

        if not member_id:
            context.user_data.pop("add_member_name", None)
            await msg.reply_text("❌ ID topilmadi. Qaytadan urinib ko'ring.")
            return

        if not text_msg:
            await msg.reply_text("❌ Ism bo'sh bo'lishi mumkin emas.")
            return

        members = data.setdefault("members", {})

        members[str(member_id)] = {
            "name": text_msg,
            "id": member_id
        }

        save()

        context.user_data.pop("add_member_id", None)
        context.user_data.pop("add_member_name", None)

        await msg.reply_text(
            "✅ A'ZO MUVAFFAQIYATLI QO'SHILDI!\n\n"
            f"👤 Ism: {text_msg}\n"
            f"🆔 ID: {member_id}"
        )
        return

    # =========================
    # A'ZO QO'SHISH — ID BOSQICHI
    # =========================
    if context.user_data.get("add_member"):
        try:
            member_id = int(text_msg)
        except ValueError:
            await msg.reply_text(
                "❌ Telegram ID noto'g'ri.\n\n"
                "Faqat raqam yuboring. Masalan:\n"
                "7985663471"
            )
            return

        context.user_data.pop("add_member", None)
        context.user_data["add_member_id"] = member_id
        context.user_data["add_member_name"] = True

        await msg.reply_text(
            "👤 Endi yangi a'zoning ismini yuboring."
        )
        return

    # =========================
    # BROADCAST
    # =========================
    if not context.user_data.get("broadcast"):
        return

    context.user_data["broadcast"] = False

    sent = 0
    pinned = 0

    groups = data.get("groups", {})

    if isinstance(groups, dict):
        items = groups.values()
    elif isinstance(groups, list):
        items = groups
    else:
        items = []

    for g in items:
        try:
            if isinstance(g, dict):
                chat_id = (
                    g.get("group_id")
                    or g.get("chat_id")
                    or g.get("id")
                )
            else:
                chat_id = g

            if not chat_id:
                continue

            sent_message = await context.bot.send_message(
                chat_id=int(chat_id),
                text=text_msg
            )

            sent += 1

            try:
                await context.bot.pin_chat_message(
                    chat_id=int(chat_id),
                    message_id=sent_message.message_id,
                    disable_notification=False
                )
                pinned += 1
            except Exception:
                pass

        except Exception:
            pass

    await msg.reply_text(
        f"📢 Xabar yuborildi!\n\n"
        f"🏘 Guruhlar: {sent}\n"
        f"📌 Qadalgan: {pinned}"
    )

async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type not in ("group", "supergroup"):
        await update.effective_message.reply_text(
            "📌 /pin buyrug‘ini guruh ichida ishlating."
        )
        return

    uid = update.effective_user.id

    if not is_admin(uid):
        await update.effective_message.reply_text("⛔ Ruxsat yo‘q.")
        return

    msg = update.effective_message

    if not msg.reply_to_message:
        await msg.reply_text(
            "📌 Qaysi xabarni qadash kerak?\n\n"
            "Qadamoqchi bo‘lgan xabarga Reply qiling va /pin yuboring."
        )
        return

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=msg.reply_to_message.message_id,
            disable_notification=False
        )

        await msg.reply_text("📌 Xabar muvaffaqiyatli qadandi! ✅")

    except Exception:
        await msg.reply_text(
            "❌ Xabarni qadab bo‘lmadi.\n\n"
            "Bot guruhda administrator ekanini va "
            "xabarlarni qadash huquqi borligini tekshiring."
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["broadcast"] = False
    await update.effective_message.reply_text("Bekor qilindi.")

def main():
    token = get_token()
    if not token:
        raise SystemExit(
            "Token topilmadi. Tokenni ~/.config/energy-ittifoq/token fayliga saqlang."
        )
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("ittifoq_leave", leave))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("pin", pin_command))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("⚡ ENERGY ITTIFOQ ishga tushdi!")
    app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
