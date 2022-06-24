import os
import re

from pprint import pprint
from textwrap import dedent

import redis

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from shop import get_products, get_auth_token, get_file_link, add_item_to_cart, get_cart, delete_item, create_customer


DB = None

def start(update: Update, context: CallbackContext):
    products = get_products(
        context.bot_data['store_token'],
        context.bot_data['base_url']
    )
    keyboard = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])]
        for product in products['data']
    ] + [[InlineKeyboardButton('Моя корзина', callback_data='show_cart')]]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Приветствуем в рыбном магазине. Выберите опцию:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    return 'INITIAL_CHOICE'


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'show_cart':
        return show_cart(update, context)
    product = get_products(
        context.bot_data['store_token'],
        context.bot_data['base_url'],
        query.data
    )['data']
    text = dedent(
        f"""
        Вы выбрали {product['name']}
        {product['description']}
        Всего {product['price'][0]['amount']/100} долларов за 1 килограмм
        Сколько бы вы хотели купить?
        """
    )
    keyboard = [
        [
            InlineKeyboardButton('1 кг', callback_data=product['sku'] + '_1'),
            InlineKeyboardButton('5 кг', callback_data=product['sku'] + '_5'),
            InlineKeyboardButton('10 кг', callback_data=product['sku'] + '_10')
        ],
        [InlineKeyboardButton('Назад', callback_data='back')],
        [InlineKeyboardButton('Моя корзина', callback_data='show_cart')]
    ]
    image_meta = product.get('relationships', {0: 0}).get('main_image')
    if image_meta:
        image = get_file_link(
            context.bot_data['store_token'],
            context.bot_data['base_url'],
            image_meta['data']['id']
        )
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image,
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'back' or query.data == 'continue':
        return start(update, context)
    elif query.data == 'pay':
        return payment(update, context)
    elif query.data == 'show_cart':
        return show_cart(update, context)
    sku, quantity = query.data.split('_')
    cart = add_item_to_cart(
        context.bot_data['store_token'],
        context.bot_data['base_url'],
        cart_id=update.effective_chat.id,
        sku=sku,
        quantity=int(quantity)
        )
    keyboard = [
        [InlineKeyboardButton('Оплатить', callback_data='pay')] if cart['total_price'] else None,
        [InlineKeyboardButton('Продолжить покупки', callback_data='continue')]
    ]
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Отлично, добавили в корзину!\n" + make_cart_description(cart),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )
    return 'HANDLE_MENU'


def make_cart_description(cart):
    cart_content_text = '\n    '.join([
        f"{item['name']} {item['quantity']} кг - {item['unit_price']*item['quantity']}$"
        for item in cart.get('items')
    ])
    text = dedent(f"""
    Сейчас у вас в корзине:
    {cart_content_text}
    Общая цена {cart.get('total_price', 0)}
    """)
    return text


def show_cart(update: Update, context: CallbackContext):
    cart = get_cart(
        context.bot_data['store_token'],
        context.bot_data['base_url'],
        update.effective_chat.id
    )
    keyboard = [
        [InlineKeyboardButton(f"Убрать из корзины {item['name']}", callback_data=f"{item['id']}")]
        for item in cart.get('items')
    ]
    keyboard.append([InlineKeyboardButton('Продолжить покупки', callback_data='continue')])
    if cart['total_price']:
        keyboard.append([InlineKeyboardButton('Оплатить', callback_data='pay')])
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=make_cart_description(cart),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.bot.delete_message(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id
    )
    return 'HANDLE_CART'


def payment(update: Update, context: CallbackContext):
    message = update.effective_message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Пожалуйста, оставьте свою почту, чтобы мы связались с вами по оплате'
    )
    return 'WAITING_EMAIL'


def get_email(update: Update, context: CallbackContext):
    user_reply = update.message.text
    if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", user_reply):
        return payment(update, context)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Вы оставили почту {user_reply}"
    )
    create_customer(
        context.bot_data['store_token'],
        context.bot_data['base_url'],
        str(update.effective_chat.id),
        user_reply
    )
    return 'FINISH'


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'continue':
        return start(update, context)
    elif query.data == 'pay':
        return payment(update, context)
    delete_item(
        context.bot_data['store_token'],
        context.bot_data['base_url'],
        update.effective_chat.id,
        query.data
    )
    return show_cart(update, context)


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
        'INITIAL_CHOICE': button,
        'HANDLE_MENU': handle_menu,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': get_email
    }

    state_handler = states_function[user_state]

    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def refresh_token(context: CallbackContext):
    client_id = os.getenv('CLIENT_ID')
    context.bot_data['store_token'] = get_auth_token(
        context.bot_data['base_url'],
        client_id
    )


def main():
    load_dotenv()
    tg_token = os.getenv('TG_TOKEN')
    updater = Updater(tg_token)
    job_queue = updater.job_queue
    updater.dispatcher.bot_data['base_url'] = 'https://api.moltin.com'
    job_queue.run_repeating(refresh_token, interval=3600, first=1)

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
