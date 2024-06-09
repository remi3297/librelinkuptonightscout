import requests
import json
import datetime
import os

LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL', 'remi.lecussan@yahoo.fr')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD', 'Remi32971997!')
NIGHTSCOUT_URL = os.getenv('NIGHTSCOUT_URL')
NIGHTSCOUT_API_SECRET = os.getenv('NIGHTSCOUT_API_SECRET')

print("Starting fetch_glucose_data.py script")

print(f"LIBRELINKUP_EMAIL: {LIBRELINKUP_EMAIL}")
print(f"LIBRELINKUP_PASSWORD: {'*' * len(LIBRELINKUP_PASSWORD) if LIBRELINKUP_PASSWORD else None}")
print(f"NIGHTSCOUT_URL: {NIGHTSCOUT_URL}")
print(f"NIGHTSCOUT_API_SECRET: {'*' * len(NIGHTSCOUT_API_SECRET) if NIGHTSCOUT_API_SECRET else None}")

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

    try:
        response = requests.post(login_url, data=json.dumps(payload), headers=headers)
        print(f"Initial Response Status Code: {response.status_code}")
        print(f"Initial Response Text: {response.text}")
        response.raise_for_status()
        data = response.json()

        if 'redirect' in data['data'] and data['data']['redirect']:
            print(f"Redirection suggested to region: {data['data']['region']}, but ignoring redirection")

        auth_ticket = data['data'].get('authTicket')
        if not auth_ticket:
            raise ValueError("authTicket not found in response")
        
        return auth_ticket

    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        raise
    except Exception as err:
        print(f"An error occurred: {err}")
        raise

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.get(data_url, headers=headers)
    print(f"Glucose Data Response Status Code: {response.status_code}")
    print(f"Glucose Data Response Text: {response.text}")
    response.raise_for_status()
    return response.json()['data']

def send_to_nightscout(glucose_data):
    for record in glucose_data:
        if 'glucoseMeasurement' in record:
            glucose_measurement = record['glucoseMeasurement']
            payload = {
                'date': int(datetime.datetime.strptime(glucose_measurement['Timestamp'], '%m/%d/%Y %I:%M:%S %p').timestamp() * 1000),
                'sgv': glucose_measurement['Value'],
                'direction': 'None',
                'type': 'sgv'
            }
            headers = {
                'API-SECRET': NIGHTSCOUT_API_SECRET,
                'Content-Type': 'application/json'
            }
            response = requests.post(f'{NIGHTSCOUT_URL}/api/v1/entries', data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            print(f"Successfully sent data to Nightscout: {payload}")

if __name__ == '__main__':
    try:
        session_token = get_librelinkup_session()
        print("Successfully obtained session token")
        connections = get_glucose_data(session_token)
        print("Successfully obtained glucose data")
        for connection in connections:
            print(f"Connection ID: {connection['id']}")
            if 'glucoseMeasurement' in connection:
                glucose_measurement = connection['glucoseMeasurement']
                print(f"Date: {glucose_measurement['Timestamp']}, Glucose Value: {glucose_measurement['Value']}")
                send_to_nightscout([connection])
            else:
                print("No glucose measurement data available.")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")
