from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

WARNINGS_FILE = 'warnings.json'
USERS_FILE = 'users.json'

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
• 3-warn: Ogohlantirish
• 4-warn: Ogohlantirish
• 5-warn: 1 kunlik mute 💣

Qoidalarga rioya qiling va yoqimli muloqat qiling! 😊
"""

class ModeratorBot:
    def __init__(self):
        self.warnings = self.load_warnings()
        self.users = self.load_users()
        self.max_warnings = 5
    
    # WARNINGS
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

    # USERS CACHE
    def load_users(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_users(self):
        with open(USERS_FILE, "w") as f:
            json.dump(self.users, f, indent=2)
    
    def remember_user(self, user):
        if user.username:
            self.users[user.username.lower()] = {
                "id": user.id,
                "first_name": user.first_name
            }
            self.save_users()
    
    def get_user_by_username(self, username):
        return self.users.get(username.lower())

bot_instance = ModeratorBot()

# ---------------- UTILS ----------------

async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply yoki username orqali foydalanuvchini olish"""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user, None

    if context.args:
        arg = context.args[0]
        if arg.startswith("@"):
            username = arg[1:]
            user_data = bot_instance.get_user_by_username(username)
            if not user_data:
                return None, (
                    f"❌ @{username} topilmadi.\n\n"
                    "ℹ️ Foydalanuvchi bot ishga tushgandan keyin "
                    "kamida 1 marta xabar yozgan bo‘lishi kerak."
                )
            fake_user = type(
                "UserObj",
                (),
                {
                    "id": user_data["id"],
                    "first_name": user_data["first_name"]
                }
            )
            return fake_user, None
        else:
            try:
                user_id = int(arg)
                chat_member = await context.bot.get_chat_member(
                    update.effective_chat.id, user_id
                )
                return chat_member.user, None
            except:
                return None, "❌ Noto‘g‘ri user ID!"
    return None, None

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception as e:
        logger.error(f"Admin tekshirishda xatolik: {e}")
        return False

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

# ---------------- HANDLERS ----------------

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har xabar yozgan foydalanuvchini eslab qolish"""
    if update.message and update.message.from_user:
        bot_instance.remember_user(update.message.from_user)

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name
        user_mention = f'<a href="tg://user?id={member.id}">{name}</a>'
        welcome_text = (
            f"👋 Salom, {user_mention}!\n\n"
            f"🎉 {update.effective_chat.title} guruhiga xush kelibsiz!\n\n"
            f"📋 Qoidalar: /rules\n"
            f"Yoqimli muloqat! 😊"
        )
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 <b>Moderator Bot</b>

👋 <b>Salomlashish:</b>
Yangi a'zolarni avtomatik salomlaydi

🔇 <b>Mute/Unmute:</b>
/mute [reply/@username] [vaqt]
/unmute [reply/@username]

⚠️ <b>Warn/Unwarn:</b>
/warn [reply/@username] [sabab]
/unwarn [reply/@username]
/warnings [reply/@username]
<i>5 ta warn = 1 soat mute</i>

⛔ <b>Ban/Unban:</b>
/ban [reply/@username]
/unban [reply/@username/id]

👑 <b>Admin:</b>
/promote [reply/@username]
/unpromote [reply/@username]

📋 /rules - Qoidalar
/help - Yordam
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GROUP_RULES, parse_mode=ParseMode.HTML)

# ---------------- MUTE / UNMUTE ----------------

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_mute, error = await get_target_user(update, context)
    
    if not user_to_mute:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    user_mention = f'<a href="tg://user?id={user_to_mute.id}">{user_to_mute.first_name}</a>'
    
    duration = None
    time_msg = "1 kunga"
    
    time_arg = None
    if update.message.reply_to_message and context.args:
        time_arg = context.args[0]
    elif not update.message.reply_to_message and len(context.args) > 1:
        time_arg = context.args[1]
    
    if time_arg:
        duration = parse_time(time_arg)
        if duration:
            time_msg = f"{time_arg} ga"
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
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_unmute, error = await get_target_user(update, context)
    
    if not user_to_unmute:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
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
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

# ---------------- WARN / UNWARN / CHECK ----------------

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_warn, error = await get_target_user(update, context)
    
    if not user_to_warn:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    reason = ""
    if update.message.reply_to_message and context.args:
        reason = " ".join(context.args)
    elif not update.message.reply_to_message and len(context.args) > 1:
        reason = " ".join(context.args[1:])
    
    if not reason:
        reason = "Sabab ko'rsatilmadi"
    
    user_mention = f'<a href="tg://user?id={user_to_warn.id}">{user_to_warn.first_name}</a>'
    warnings = bot_instance.add_warning(update.effective_chat.id, user_to_warn.id)
    
    if warnings >= bot_instance.max_warnings:
        try:
            permissions = ChatPermissions(can_send_messages=False)
            duration = datetime.now() + timedelta(hours=1)
            await context.bot.restrict_chat_member(
                update.effective_chat.id, 
                user_to_warn.id, 
                permissions,
                until_date=duration
            )
            await update.message.reply_text(
                f"⛔ {user_mention} {warnings} ta warn oldi va 1 soatga mutelandi!\n"
                f"<b>Sabab:</b> {reason}",
                parse_mode=ParseMode.HTML
            )
            bot_instance.remove_warnings(update.effective_chat.id, user_to_warn.id)
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {str(e)}")
    else:
        await update.message.reply_text(
            f"⚠️ {user_mention} warn oldi!\n"
            f"<b>Sabab:</b> {reason}\n"
            f"<b>Warnlar:</b> {warnings}/{bot_instance.max_warnings}\n\n"
            f"<i>💡 5 ta warn = 1 soat mute</i>",
            parse_mode=ParseMode.HTML
        )

async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_unwarn, error = await get_target_user(update, context)
    
    if not user_to_unwarn:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    user_mention = f'<a href="tg://user?id={user_to_unwarn.id}">{user_to_unwarn.first_name}</a>'
    
    if bot_instance.remove_warnings(update.effective_chat.id, user_to_unwarn.id):
        await update.message.reply_text(
            f"✅ {user_mention} barcha warnlari o'chirildi!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("ℹ️ Foydalanuvchida warn yo'q!")

async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_to_check, error = await get_target_user(update, context)
    
    if not user_to_check:
        user_to_check = update.effective_user
    
    user_mention = f'<a href="tg://user?id={user_to_check.id}">{user_to_check.first_name}</a>'
    warnings = bot_instance.get_user_warnings(update.effective_chat.id, user_to_check.id)
    
    await update.message.reply_text(
        f"⚠️ {user_mention} - {warnings}/{bot_instance.max_warnings} ta warn",
        parse_mode=ParseMode.HTML
    )

# ---------------- BAN / UNBAN ----------------

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_ban, error = await get_target_user(update, context)
    
    if not user_to_ban:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    user_mention = f'<a href="tg://user?id={user_to_ban.id}">{user_to_ban.first_name}</a>'
    
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_to_ban.id)
        await update.message.reply_text(
            f"⛔ {user_mention} guruhdan bloklandi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_unban, error = await get_target_user(update, context)
    
    if not user_to_unban:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user_to_unban.id)
        user_mention = f'<a href="tg://user?id={user_to_unban.id}">{user_to_unban.first_name}</a>'
        await update.message.reply_text(
            f"✅ {user_mention} blokdan chiqarildi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

# ---------------- PROMOTE / UNPROMOTE ----------------

async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_promote, error = await get_target_user(update, context)
    
    if not user_to_promote:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
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
            f"👑 {user_mention} admin qilindi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def unpromote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Admin huquqi kerak!")
        return
    
    user_to_unpromote, error = await get_target_user(update, context)
    
    if not user_to_unpromote:
        await update.message.reply_text(error or "❌ Foydalanuvchini ko'rsating!")
        return
    
    try:
        await context.bot.promote_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_unpromote.id,
            can_change_info=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_video_chats=False
        )
        user_mention = f'<a href="tg://user?id={user_to_unpromote.id}">{user_to_unpromote.first_name}</a>'
        await update.message.reply_text(
            f"👑 {user_mention} adminlikdan chiqarildi!",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")
# ---------------- MAIN ----------------

def main():
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        logger.error("❌ TOKEN .env faylda yo'q!")
        return

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("rules", show_rules))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("unmute", unmute_user))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("unwarn", unwarn_user))
    app.add_handler(CommandHandler("warnings", check_warnings))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("promote", promote_user))
    app.add_handler(CommandHandler("unpromote", unpromote_user))

    # Messages
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track_users))

    logger.info("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()