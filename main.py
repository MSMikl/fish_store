import os

import requests

from dotenv import load_dotenv

def main():
    load_dotenv()
    client_id = os.getenv('CLIENT_ID')
    BASE_URL = 'https://api.moltin.com'
    data = {
        'client_id': client_id,
        'grant_type': 'implicit'
    }
    response = requests.post(f'{BASE_URL}/oauth/access_token', data=data)
    response.raise_for_status()
    store_token = f"Bearer {response.json().get('access_token')}"
    headers = {
        'Authorization': store_token
    }
    response = requests.get(f'{BASE_URL}/v2/products', headers=headers)
    print(response.json())
    
    
if __name__ == '__main__':
    main()