from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging
from datetime import datetime, timedelta
import json
import os

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WARNINGS_FILE = 'warnings.json'

GROUP_RULES = """
📋 <b>Guruh Qoidalari</b>

1️⃣ Barcha a'zolarga hurmat bilan muomala qiling
2️⃣ Spam va reklama taqiqlanadi
3️⃣ Haqoratli va nomaqbul kontent yuborilmaydi
4️⃣ Mavzudan tashqari xabarlarni ko'p yubormang
5️⃣ Boshqa a'zolarning shaxsiy ma'lumotlarini tarqatmang
6️⃣ Admin ko'rsatmalariga amal qiling

⚠️ <b>Qoidabuzarlik jarimasi:</b>
• 1-warn: Ogohlantirish
• 2-warn: Ogohlantirish
• 3-warn: 1 kunlik mute

Qoidalarga rioya qiling va yoqimli muloqot qiling! 😊
"""

class ModeratorBot:
    def __init__(self):
        self.warnings = self.load_warnings()
        self.max_warnings = 3
    
    def load_warnings(self):
        if os.path.exists(WARNINGS_FILE):
            try:
                with open(WARNINGS_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {}
                    return data
            except:
                return {}
        return {}
    
    def save_warnings(self):
        with open(WARNINGS_FILE, 'w') as f:
            json.dump(self.warnings, f, indent=2)
    
    def get_user_warnings(self, chat_id, user_id):
        key = f"{chat_id}_{user_id}"
        return self.warnings.get(key, 0)
    
    def add_warning(self, chat_id, user_id):
        key = f"{chat_id}_{user_id}"
        self.warnings[key] = self.warnings.get(key, 0) + 1
        self.save_warnings()
        return self.warnings[key]
    
    def remove_warnings(self, chat_id, user_id):
        key = f"{chat_id}_{user_id}"
        if key in self.warnings:
            del self.warnings[key]
            self.save_warnings()
            return True
        return False

bot_instance = ModeratorBot()

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Admin tekshirishda xatolik: {e}")
        return False

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name
        user_mention = f'<a href="tg://user?id={member.id}">{name}</a>'
        welcome_text = (
            f"👋 Salom, {user_mention}!\n\n"
            f"🎉 {update.effective_chat.title} guruhiga xush kelibsiz!\n\n"
            f"📋 Guruh qoidalari bilan tanishish uchun /rules buyrug'idan foydalaning.\n"
            f"Sizga yoqimli muloqot tilaymiz! 😊"
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 <b>Moderator Bot - Buyruqlar</b>

👋 <b>Salomlashish:</b>
Yangi a'zolarni avtomatik salomlaydi

🔇 <b>Mute/Unmute:</b>
/mute [javob/vaqt] - A'zoni mutelamoq
  Misol: /mute 1h, /mute 30m, /mute 2d
  Faqat /mute - 1 kunga mute
/unmute [javob] - Muteni bekor qilmoq

⚠️ <b>Warn/Unwarn:</b>
/warn [javob] [sabab] - Ogohlantirish berish
/unwarn [javob] - Ogohlantirishni bekor qilish
/warnings [javob] - Ogohlantirishlarni ko'rish
  *3 ta warn = 1 kun mute*

⛔ <b>Ban/Unban:</b>
/ban [javob] - A'zoni bloklash
/unban [javob/@username/id] - Blokni ochish

👑 <b>Admin boshqaruvi:</b>
/promote [javob] - Admin qilish
/unpromote [javob] - Adminlikdan chetlatish

📋 <b>Boshqa:</b>
/rules - Guruh qoidalari
/help - Bu yordam

<i>⚙️ Ko'pchilik buyruqlar admin huquqini talab qiladi</i>
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GROUP_RULES, parse_mode=ParseMode.HTML)

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, mutelamoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "1. Foydalanuvchi xabariga reply qiling\n"
            "2. <code>/mute 1h</code> yoki <code>/mute 30m</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_mute = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_mute.id}">{user_to_mute.first_name}</a>'
    
    duration = None
    time_msg = "1 kunga"
    
    if context.args:
        time_str = context.args[0]
        duration = parse_time(time_str)
        if duration:
            time_msg = f"{time_str} ga"
        else:
            duration = datetime.now() + timedelta(days=1)
    else:
        duration = datetime.now() + timedelta(days=1)
    
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            user_to_mute.id, 
            permissions,
            until_date=duration
        )
        await update.message.reply_text(
            f"🔇 {user_mention} {time_msg} mutelandi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Mutelashda xatolik: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, unmute qilmoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "Foydalanuvchi xabariga reply qilib <code>/unmute</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_unmute = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_unmute.id}">{user_to_unmute.first_name}</a>'
    
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_invite_users=True
        )
        await context.bot.restrict_chat_member(
            update.effective_chat.id, 
            user_to_unmute.id, 
            permissions
        )
        await update.message.reply_text(
            f"🔊 {user_mention} mutedan chiqarildi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Unmute qilishda xatolik: {str(e)}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, warn bermoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "1. Foydalanuvchi xabariga reply qiling\n"
            "2. <code>/warn sabab yozish</code> yoki shunchaki <code>/warn</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_warn = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "Sabab ko'rsatilmadi"
    user_mention = f'<a href="tg://user?id={user_to_warn.id}">{user_to_warn.first_name}</a>'
    
    warnings = bot_instance.add_warning(update.effective_chat.id, user_to_warn.id)
    
    if warnings >= bot_instance.max_warnings:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            duration = datetime.now() + timedelta(days=1)
            await context.bot.restrict_chat_member(
                update.effective_chat.id, 
                user_to_warn.id, 
                permissions,
                until_date=duration
            )
            await update.message.reply_text(
                f"⛔ {user_mention} {warnings} ta ogohlantirish oldi va 1 kunga mutelandi!\n"
                f"<b>Sabab:</b> {reason}",
                parse_mode=ParseMode.HTML
            )
            bot_instance.remove_warnings(update.effective_chat.id, user_to_warn.id)
        except Exception as e:
            await update.message.reply_text(f"❌ Mutelashda xatolik: {str(e)}")
    else:
        await update.message.reply_text(
            f"⚠️ {user_mention} ogohlantirish oldi!\n"
            f"<b>Sabab:</b> {reason}\n"
            f"<b>Ogohlantirishlar:</b> {warnings}/{bot_instance.max_warnings}\n\n"
            f"<i>💡 {bot_instance.max_warnings} ta ogohlantirish = 1 kunlik mute</i>",
            parse_mode=ParseMode.HTML
        )

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, unwarn qilmoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "Foydalanuvchi xabariga reply qilib <code>/unwarn</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_unwarn = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_unwarn.id}">{user_to_unwarn.first_name}</a>'
    
    if bot_instance.remove_warnings(update.effective_chat.id, user_to_unwarn.id):
        await update.message.reply_text(
            f"✅ {user_mention} ning barcha ogohlantirishlari o'chirildi!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("ℹ️ Foydalanuvchida ogohlantirish yo'q!")

async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        user_to_check = update.message.reply_to_message.from_user
    else:
        user_to_check = update.effective_user
    
    user_mention = f'<a href="tg://user?id={user_to_check.id}">{user_to_check.first_name}</a>'
    warnings = bot_instance.get_user_warnings(update.effective_chat.id, user_to_check.id)
    
    await update.message.reply_text(
        f"⚠️ {user_mention} - {warnings}/{bot_instance.max_warnings} ta ogohlantirish",
        parse_mode=ParseMode.HTML
    )

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, ban qilmoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "Foydalanuvchi xabariga reply qilib <code>/ban</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_ban = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_ban.id}">{user_to_ban.first_name}</a>'
    
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_ban.id)
        await update.message.reply_text(
            f"⛔ {user_mention} guruhdan bloklandi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Bloklashda xatolik: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    user_id = None
    user_name = None
    
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        user_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        arg = context.args[0]
        try:
            if arg.startswith('@'):
                username = arg[1:]
                try:
                    chat_member = await context.bot.get_chat_member(update.effective_chat.id, f"@{username}")
                    user_id = chat_member.user.id
                    user_name = chat_member.user.first_name
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ @{username} username topilmadi yoki bu foydalanuvchi guruhda emas!\n"
                        f"User ID bilan sinab ko'ring."
                    )
                    return
            else:
                user_id = int(arg)
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri foydalanuvchi ID yoki username!")
            return
    else:
        await update.message.reply_text(
            "❌ Iltimos, quyidagi usullardan birini ishlating:\n\n"
            "💡 <b>1-usul:</b> Ban qilingan xabariga reply qiling\n"
            "   <code>/unban</code> (reply bilan)\n\n"
            "💡 <b>2-usul:</b> User ID kiriting\n"
            "   <code>/unban 123456789</code>\n\n"
            "💡 <b>3-usul:</b> Username kiriting\n"
            "   <code>/unban @username</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
        if user_name:
            await update.message.reply_text(f"✅ {user_name} blokdan chiqarildi!")
        else:
            await update.message.reply_text(f"✅ Foydalanuvchi (ID: {user_id}) blokdan chiqarildi!")
    except Exception as e:
        await update.message.reply_text(f"❌ Blokdan chiqarishda xatolik: {str(e)}")

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, admin qilmoqchi bo'lgan foydalanuvchi xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "Foydalanuvchi xabariga reply qilib <code>/promote</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_promote = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_promote.id}">{user_to_promote.first_name}</a>'
    
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user_to_promote.id,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_video_chats=True,
            can_promote_members=False
        )
        await update.message.reply_text(
            f"👑 {user_mention} admin qilindi!\n\n"
            f"<b>Huquqlar:</b>\n"
            f"✅ Xabar o'chirish\n"
            f"✅ Foydalanuvchini bloklash\n"
            f"✅ Havola orqali taklif qilish\n"
            f"✅ Xabarlarni qadash\n"
            f"✅ Jonli efirlarni boshqarish",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        error_message = str(e)
        if "RIGHT_FORBIDDEN" in error_message.upper() or "rights" in error_message.lower():
            await update.message.reply_text(
                "❌ Botda adminlarni qo'shish huquqi yo'q!\n\n"
                "📝 <b>Hal qilish:</b>\n"
                "1. Guruh sozlamalariga kiring\n"
                "2. Adminlar ro'yxatidan botni toping\n"
                "3. Bot huquqlariga \"Add new admins\" ni yoqing\n\n"
                "Yoki botni guruhdan chiqarib, qayta admin sifatida qo'shing va barcha huquqlarni bering!",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(f"❌ Admin qilishda xatolik: {str(e)}")

async def unpromote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Bu buyruqni faqat adminlar ishlatishi mumkin!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Iltimos, unpromote qilmoqchi bo'lgan admin xabariga reply qiling!\n\n"
            "💡 <b>Qanday ishlatiladi:</b>\n"
            "Admin xabariga reply qilib <code>/unpromote</code> deb yozing",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_to_unpromote = update.message.reply_to_message.from_user
    user_mention = f'<a href="tg://user?id={user_to_unpromote.id}">{user_to_unpromote.first_name}</a>'
    
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id,
            user_to_unpromote.id,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_video_chats=False,
            can_promote_members=False
        )
        await update.message.reply_text(
            f"📉 {user_mention} adminlikdan chetlatildi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Unpromote qilishda xatolik: {str(e)}")

def parse_time(time_str):
    try:
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            return datetime.now() + timedelta(minutes=minutes)
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            return datetime.now() + timedelta(hours=hours)
        elif time_str.endswith('d'):
            days = int(time_str[:-1])
            return datetime.now() + timedelta(days=days)
    except:
        pass
    return None

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("unwarn", unwarn_user))
    application.add_handler(CommandHandler("warnings", check_warnings))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("promote", promote_user))
    application.add_handler(CommandHandler("unpromote", unpromote_user))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    print("🤖 Bot ishga tushdi...")
    print("📋 Guruhingizga botni admin sifatida qo'shing!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()