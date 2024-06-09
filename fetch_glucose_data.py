import requests
import json
import os
import datetime

# Définir les variables d'environnement
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')
NIGHTSCOUT_API_SECRET = os.getenv('NIGHTSCOUT_API_SECRET')
NIGHTSCOUT_URL = os.getenv('NIGHTSCOUT_URL')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')

proxies = {
    "http": f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}",
    "https": f"https://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}",
}

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

    session = requests.Session()
    session.proxies.update(proxies)
    response = session.post(login_url, json=payload, headers=headers)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
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

    session = requests.Session()
    session.proxies.update(proxies)
    response = session.get(data_url, headers=headers)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    response.raise_for_status()
    return response.json()['data']

def send_to_nightscout(glucose_data):
    entries_url = f"{NIGHTSCOUT_URL}/api/v1/entries"
    headers = {
        'API-SECRET': NIGHTSCOUT_API_SECRET,
        'Content-Type': 'application/json'
    }

    for connection in glucose_data:
        if 'glucoseMeasurement' in connection:
            glucose_measurement = connection['glucoseMeasurement']
            entry = {
                "date": int(datetime.datetime.strptime(glucose_measurement['Timestamp'], '%Y-%m-%dT%H:%M:%S').timestamp() * 1000),
                "sgv": glucose_measurement['Value'],
                "direction": "Flat",
                "device": "LibreLinkUp"
            }

            response = requests.post(entries_url, headers=headers, json=entry)
            print(f"Nightscout Response Status Code: {response.status_code}")
            print(f"Nightscout Response Text: {response.text}")
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

