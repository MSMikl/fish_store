import os
import pprint

import requests

from dotenv import load_dotenv


def main():
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    base_url = 'https://api.moltin.com'
    store_token = start_auth(base_url, client_id)

    get_products_list(store_token, base_url)
    cart = create_cart(store_token, base_url, 'test_cart')
    add_item_to_cart(store_token, base_url, cart, '10001', 2)


def start_auth(base_url, client_id):
    data = {
        'client_id': client_id,
        'grant_type': 'implicit'
    }
    response = requests.post(f'{base_url}/oauth/access_token', data=data)
    response.raise_for_status()
    return f"Bearer {response.json().get('access_token')}"


def get_products_list(token, url):
    headers = {
        'Authorization': token
    }
    response = requests.get(f'{url}/v2/products', headers=headers)
    return response.json()

def create_cart(token, url, cart_name):
    cart_data = {
        'data': {
            'name': cart_name
        }
    }
    headers = {
        'Authorization': token
    }
    response = requests.post(
        f'{url}/v2/carts',
        headers=headers,
        json=cart_data
    )
    response.raise_for_status()
    return response.json()['data']['id']


def add_item_to_cart(token, url, cart_id, sku, quantity):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    data = {
        'data': {
            'sku': sku,
            'quantity': quantity,
            "type": "cart_item"                      
        }
    }
    response = requests.post(
        f'{url}/v2/carts/{cart_id}/items',
        headers=headers,
        json=data
    )
    pprint.pprint(response.json())


if __name__ == '__main__':
    main()