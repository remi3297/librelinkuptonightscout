import requests
import json
import os
import datetime
import urllib.request
from dotenv import load_dotenv

# Charger les variables d'environnement depuis un fichier .env si présent
load_dotenv()

# Définir les variables d'environnement
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')
NIGHTSCOUT_API_SECRET = os.getenv('NIGHTSCOUT_API_SECRET')
NIGHTSCOUT_URL = os.getenv('NIGHTSCOUT_URL')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')

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
    
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}',
        'https': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
    
    req = urllib.request.Request(login_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        response_data = response.read().decode('utf-8')
        print(f"Response Status Code: {response.getcode()}")
        print(f"Response Text: {response_data}")
        response_json = json.loads(response_data)
        return response_json['data']['authTicket']

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}',
        'https': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
    
    req = urllib.request.Request(data_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        response_data = response.read().decode('utf-8')
        print(f"Response Status Code: {response.getcode()}")
        print(f"Response Text: {response_data}")
        response_json = json.loads(response_data)
        return response_json['data']

def send_to_nightscout(glucose_data):
    entries_url = f"{NIGHTSCOUT_URL}/api/v1/entries"
    headers = {
        'api-secret': NIGHTSCOUT_API_SECRET,
        'Content-Type': 'application/json'
    }
    print(f"Nightscout Headers: {headers}")
    for connection in glucose_data:
        if 'glucoseMeasurement' in connection:
            glucose_measurement = connection['glucoseMeasurement']
            # Convertir le format de date et heure reçu
            timestamp_str = glucose_measurement['Timestamp']
            timestamp_dt = datetime.datetime.strptime(timestamp_str, '%m/%d/%Y %I:%M:%S %p')
            entry = {
                "date": int(timestamp_dt.timestamp() * 1000),
                "sgv": glucose_measurement['Value'],
                "direction": "Flat",
                "device": "LibreLinkUp"
            }
            response = requests.post(entries_url, headers=headers, data=json.dumps(entry))
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
