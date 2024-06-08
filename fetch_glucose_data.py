import requests
import json
import datetime

LIBRELINKUP_EMAIL = 'votre_email@exemple.com'
LIBRELINKUP_PASSWORD = 'votre_mot_de_passe'
NIGHTSCOUT_URL = 'https://votre_instance_nightscout.railway.app'
NIGHTSCOUT_API_SECRET = 'votre_api_secret'

def get_librelinkup_session():
    login_url = 'https://api.libreview.io/llu/auth/login'
    payload = {
        'email': LIBRELINKUP_EMAIL,
        'password': LIBRELINKUP_PASSWORD
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(login_url, data=json.dumps(payload), headers=headers)
    response.raise_for_status()
    return response.json()['data']['authTicket']

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(data_url, headers=headers)
    response.raise_for_status()
    connections = response.json()['data']
    glucose_data = []
    for connection in connections:
        for record in connection['glucoseData']:
            glucose_data.append({
                'date': record['Timestamp'],
                'value': record['Value']
            })
    return glucose_data

def send_to_nightscout(glucose_data):
    for record in glucose_data:
        payload = {
            'date': int(datetime.datetime.strptime(record['date'], '%Y-%m-%dT%H:%M:%S.%fZ').timestamp() * 1000),
            'sgv': record['value'],
            'direction': 'None',
            'type': 'sgv'
        }
        headers = {
            'API-SECRET': NIGHTSCOUT_API_SECRET,
            'Content-Type': 'application/json'
        }
        response = requests.post(f'{NIGHTSCOUT_URL}/api/v1/entries', data=json.dumps(payload), headers=headers)
        response.raise_for_status()

if __name__ == '__main__':
    session_token = get_librelinkup_session()
    glucose_data = get_glucose_data(session_token)
    send_to_nightscout(glucose_data)
