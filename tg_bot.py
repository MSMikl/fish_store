import os
import redis

from pprint import pprint

from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from shop import get_products, start_auth, get_file_link, add_item_to_cart, get_cart, delete_item


DB = None
STORE_TOKEN = None
BASE_URL = 'https://api.moltin.com'


def start(update: Update, context: CallbackContext):
    products = get_products(STORE_TOKEN, BASE_URL)
    keyboard = [
        [InlineKeyboardButton(product['name'], callback_data=product['id'])]
        for product in products['data']
    ] + [[InlineKeyboardButton('Моя корзина', callback_data='show_cart')]]
    message = update.message or update.callback_query.message
    context.bot.delete_message(
        chat_id=message.chat_id,
        message_id=message.message_id
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Приветствуем в рыбном магазине. Выберите опцию:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return 'INITIAL_CHOICE'


def button(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'show_cart':
        return show_cart(update, context)
    product = get_products(STORE_TOKEN, BASE_URL, query.data)['data']
    text = f"""Вы выбрали {product['name']}
    {product['description']}
    Всего {product['price'][0]['amount']/100} долларов за 1 килограмм
    Сколько бы вы хотели купить?"""
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
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
        image = get_file_link(STORE_TOKEN, BASE_URL, image_meta['data']['id'])
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
    return 'HANDLE_MENU'


def handle_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'back' or query.data == 'continue':
        return start(update, context)
    elif query.data == 'pay':
        return 'PAYMENT'
    elif query.data == 'show_cart':
        return show_cart(update, context)
    sku, quantity = query.data.split('_')
    cart = add_item_to_cart(
        STORE_TOKEN,
        BASE_URL,
        cart_id=update.effective_chat.id,
        sku=sku,
        quantity=int(quantity)
        )
    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
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
    return 'HANDLE_MENU'


def make_cart_description(cart):
    cart_content_text = '\n'.join([
        f"{item['name']} {item['quantity']} кг - {item['unit_price']*item['quantity']}$"
        for item in cart.get('items')
    ])
    text = f"""Сейчас у вас в корзине:
{cart_content_text}
Общая цена {cart.get('total_price', 0)}
    """
    return text


def show_cart(update: Update, context: CallbackContext):
    cart = get_cart(STORE_TOKEN, BASE_URL, update.effective_chat.id)
    context.bot.delete_message(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id
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
    return 'HANDLE_CART'


def handle_cart(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'continue':
        return start(update, context)
    elif query == 'pay':
        return 'PAYMENT'
    delete_item(STORE_TOKEN, BASE_URL, update.effective_chat.id, query.data)
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
        'HANDLE_CART': handle_cart
    }

    state_handler = states_function[user_state]

    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def main():
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    global STORE_TOKEN
    STORE_TOKEN = start_auth(BASE_URL, client_id)

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
