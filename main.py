import os
import pprint

import requests

from dotenv import load_dotenv

def main():
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    base_url = 'https://api.moltin.com'
    data = {
        'client_id': client_id,
        'grant_type': 'implicit'
    }
    response = requests.post(f'{base_url}/oauth/access_token', data=data)
    response.raise_for_status()
    store_token = f"Bearer {response.json().get('access_token')}"
    headers = {
        'Authorization': store_token
    }
    response = requests.get(f'{base_url}/v2/products', headers=headers)
    response.raise_for_status()
    
    cart_data = {
        'data':{
            'name': 'test_cart'
        }
    }
    
    response = requests.post(f'{base_url}/v2/carts', headers=headers, json=cart_data)
    response.raise_for_status()
    cart = response.json()['data']['id']
    add_item_to_cart(store_token, base_url, cart, '10001', 2)
    
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