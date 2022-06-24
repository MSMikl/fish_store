import os
import pprint

import requests

from dotenv import load_dotenv


def main():
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    base_url = 'https://api.moltin.com'
    store_token = start_auth(base_url, client_id)

    products = get_products(store_token, base_url)
    id = products['data'][0]['id']
    product = get_products(store_token, base_url, id)
    print(get_file_link(store_token, base_url, product['data']['relationships']['main_image']['data']['id']))
    pprint.pprint(add_item_to_cart(store_token, base_url, 'any_id', '10001', 2))
    pprint.pprint(get_cart(store_token, base_url, 'any_id'))


def start_auth(url, client_id):
    data = {
        'client_id': client_id,
        'grant_type': 'implicit'
    }
    response = requests.post(f'{url}/oauth/access_token', data=data)
    response.raise_for_status()
    return f"Bearer {response.json().get('access_token')}"


def get_products(token, url, id=None):
    headers = {
        'Authorization': token
    }
    response = requests.get(
        f'{url}/v2/products/{id if id else ""}',
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def get_file_link(token, url, id):
    headers = {
        'Authorization': token
    }
    response = requests.get(
        f"{url}/v2/files/{id}",
        headers=headers
    )
    return response.json().get('data', {0: 0}).get('link', {0: 0}).get('href')


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
    response.raise_for_status()
    return extract_data_from_cart(response.json())


def delete_item(token, url, cart_id, item_id):
    headers = {
        'Authorization': token
    }
    response = requests.delete(
        f"{url}/v2/carts/{cart_id}/items/{item_id}",
        headers=headers,
        )
    response.raise_for_status()
    return extract_data_from_cart(response.json())


def get_cart(token, url, cart_id):
    headers = {
        'Authorization': token
    }
    response = requests.get(
        f'{url}/v2/carts/{cart_id}/items',
        headers=headers
    )
    response.raise_for_status()
    return extract_data_from_cart(response.json())


def extract_data_from_cart(full_cart_data):
    result = {
        'items': [
            {
                'name': item['name'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price']['amount']/100,
                'id': item['id']
            }
            for item in full_cart_data['data']
        ],
        'total_price': full_cart_data['meta']['display_price']['with_tax']['amount']/100
    }
    return result


if __name__ == '__main__':
    main()