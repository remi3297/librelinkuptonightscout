import requests
import json
import os

# Load environment variables
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
NIGHTSCOUT_URL = os.getenv('NIGHTSCOUT_URL')
NIGHTSCOUT_API_SECRET = os.getenv('NIGHTSCOUT_API_SECRET')

def get_librelinkup_session():
    login_url = 'https://api.libreview.io/llu/auth/login'
    payload = {
        'email': LIBRELINKUP_EMAIL,
        'password': LIBRELINKUP_PASSWORD
    }
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    
    # Proxy configuration
    proxies = {
        "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}",
        "https": f"https://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}"
    }

    response = requests.post(login_url, data=json.dumps(payload), headers=headers, proxies=proxies)
    response.raise_for_status()
    return response.json()['data']['authTicket']

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    
    proxies = {
        "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}",
        "https": f"https://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}"
    }

    response = requests.get(data_url, headers=headers, proxies=proxies)
    response.raise_for_status()
    return response.json()['data']

def send_to_nightscout(glucose_data):
    entries_url = f"{NIGHTSCOUT_URL}/api/v1/entries.json"
    headers = {
        'Content-Type': 'application/json',
        'api-secret': NIGHTSCOUT_API_SECRET
    }

    for connection in glucose_data:
        if 'glucoseMeasurement' in connection:
            glucose_measurement = connection['glucoseMeasurement']
            entry = {
                'date': glucose_measurement['Timestamp'],
                'sgv': glucose_measurement['Value'],
                'direction': 'Flat',
                'type': 'sgv'
            }
            response = requests.post(entries_url, headers=headers, data=json.dumps(entry))
            response.raise_for_status()

if __name__ == '__main__':
    try:
        session_token = get_librelinkup_session()
        glucose_data = get_glucose_data(session_token['token'])
        send_to_nightscout(glucose_data)
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")
