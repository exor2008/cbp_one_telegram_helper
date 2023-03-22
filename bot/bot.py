import enum
import logging
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

from bot import token
from bot.user import UserManager, TodayApp

manager = UserManager(r"users")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


(
    SELECTING_ACTION,
    ADD_APP,
    ASK_PASSWORD,
    ASK_CODES,
    STOPPING,
    SAVE_CODES,
    CHOOSE_APP,
    SHOW_LOGIN,
) = map(chr, range(8))
END = ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global manager

    buttons = [
        [
            InlineKeyboardButton(text="Добавить анкету", callback_data=str(ADD_APP)),
            InlineKeyboardButton(text="Получить логин", callback_data=str(CHOOSE_APP)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if update.message:
        user_t = update.message.from_user
        if not manager.is_registered(user_t.id):
            user = manager.create_user(user_t.id, user_t.full_name)
            manager.register(user)

        await update.message.reply_text(text="Выберите действие", reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_text(
            text="Выберите действие", reply_markup=keyboard
        )

    return SELECTING_ACTION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text("Bye! I hope we can talk again some day.")

    return ConversationHandler.END


# async def add_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     global manager

#     user = update.message.from_user

#     manager.add_application(user.id, user)

#     await update.message.reply_text("Введите email")

#     return States.ADD_ACCOUNT.value


async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    await update.callback_query.edit_message_text(text="Введите email.")

    return ASK_PASSWORD


async def ask_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text(text="Введите пароль.")

    return ASK_CODES


async def ask_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["password"] = update.message.text
    update.message.text
    await update.message.reply_text(text="Введите коды.")

    return SAVE_CODES


async def save_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global manager
    codes = update.message.text

    email = context.user_data["email"]
    app = manager.create_application(context.user_data["password"], codes.split())
    manager.add_application(update.message.from_user.id, email, app)

    del context.user_data["email"]
    del context.user_data["password"]

    logger.info(
        f"Application {email} added to user {update.message.from_user.full_name}"
    )
    await start(update, context)

    return END


async def choose_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global manager

    buttons = [
        [InlineKeyboardButton(text=email, callback_data=str(SHOW_LOGIN + "_" + email))]
        for email in manager.get_emails(update.callback_query.from_user.id)
    ]

    if not buttons:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="У вас нет анкет, добавьте хотя бы одну."
        )
        return END

    buttons.append(
        [InlineKeyboardButton(text="Все", callback_data=str(SHOW_LOGIN + "_" + "All"))]
    )
    keyboard = InlineKeyboardMarkup(buttons)

    await update.callback_query.answer()

    await update.callback_query.edit_message_text(
        text="Для какой анкеты?", reply_markup=keyboard
    )

    return SHOW_LOGIN


async def show_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global manager

    data = update.callback_query.data
    _, needed_email = data.split(sep="_", maxsplit=1)
    user = update.callback_query.from_user

    if needed_email.endswith("All"):
        emails = manager.get_emails(user.id)
        apps = [manager.get_today_app(user.id, email) for email in emails]

    else:
        apps = [manager.get_today_app(user.id, needed_email)]

    def pprint_apps(apps: List[TodayApp]):
        for app in apps:
            if app.password:
                info = f"Логин:\n`{app.email}`\n\nПароль:\n`{app.password}`\n\nКод:\n`{app.code}`\n\nКлючей осталось: {app.left}"
            else:
                info = f"У вас не осталось ключей для {app.email}"
            yield info

    await update.callback_query.answer()

    for line in pprint_apps(apps):
        await update.callback_query.message.reply_markdown(text=line)

    await start(update, context)

    return END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End Conversation by command."""
    await update.message.reply_text("Okay, bye.")

    return END


async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End conversation from InlineKeyboardButton."""
    await update.callback_query.answer()

    text = "See you around!"
    await update.callback_query.edit_message_text(text=text)

    return END


def start_app():
    application = ApplicationBuilder().token(token.token).build()

    add_app_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ask_email, pattern="^" + str(ADD_APP) + "$")
        ],
        states={
            ASK_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_password),
            ],
            ASK_CODES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_codes),
            ],
            SAVE_CODES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_codes),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
        ],
        map_to_parent={
            END: SELECTING_ACTION,
            STOPPING: STOPPING,
        },
    )

    show_log_pswd_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(choose_app, pattern="^" + str(CHOOSE_APP) + "$")
        ],
        states={
            SHOW_LOGIN: [
                CallbackQueryHandler(
                    show_login,
                    pattern="^"
                    + str(SHOW_LOGIN)
                    + "_\w+[@]\w+[.]\w+"
                    + "$|^"
                    + str(SHOW_LOGIN)
                    + "\w+",
                ),
            ],
        },
        fallbacks=[
            CommandHandler("stop", stop),
        ],
        map_to_parent={
            END: SELECTING_ACTION,
            STOPPING: STOPPING,
        },
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                add_app_conv,
                show_log_pswd_conv,
                CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
            ],
            STOPPING: [CommandHandler("start", start)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    application.add_handler(conv_handler)

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    application.run_polling()
