import os
import redis

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler


DB = None


def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton('Option 1', callback_data=1),
            InlineKeyboardButton('Option 2', callback_data=2)
        ],
        [InlineKeyboardButton('Option 3', callback_data=3)]
    ]

    update.message.reply_text(
        text='Приветствуем в рыбном магазине. Выберите опцию:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return 'ECHO'


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    context.bot.edit_message_text(
        text=f"Вы выбрали вариант {query.data}",
        chat_id=query.message.chat_id,
        message_id=query.message.message_id

    )
    return 'ECHO'

def echo(update: Update, context: CallbackContext):
    update.message.reply_text(text=update.message.text)
    return 'ECHO'


def get_db_connection():
    global DB
    if not DB:
        db_pass = os.getenv('DB_PASS')
        db_host = os.getenv('DB_HOST')
        db_port = int(os.getenv('DB_PORT'))
        DB = redis.Redis(
            host=db_host,
            port=db_port,
            password=db_pass,
            db=0
        )
    return DB


def user_input_handler(update: Update, context: CallbackContext):
    db = get_db_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query.data:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('UTF-8')

    states_function = {
        'START': start,
        'ECHO': button
    }

    state_handler = states_function[user_state]

    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def main():
    load_dotenv()
    tg_token = os.getenv('TG_TOKEN')
    updater = Updater(tg_token)

    bot_commands = [
        ('start', 'Начать диалог')
    ]
    updater.bot.set_my_commands(bot_commands)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(user_input_handler))
    dispatcher.add_handler(MessageHandler(Filters.text, user_input_handler))
    dispatcher.add_handler(CommandHandler('start', user_input_handler))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
