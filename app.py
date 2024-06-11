from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json
import os

app = Flask(__name__)

LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')

session_token = None
glucose_data = None

# Correct proxy handling
proxy_auth = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}"
proxies = {
    "http": proxy_auth,
    "https": proxy_auth
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
    response = requests.post(login_url, data=json.dumps(payload), headers=headers, proxies=proxies)
    print(f"Login Response Status Code: {response.status_code}")
    print(f"Login Response Text: {response.text}")
    response.raise_for_status()
    
    auth_data = response.json().get('data')
    if not auth_data:
        raise ValueError("Login response does not contain valid 'data'")
    
    if auth_data.get('redirect'):
        region = auth_data['region']
        region_url = f"https://api-{region}.libreview.io/llu/auth/login"
        response = requests.post(region_url, data=json.dumps(payload), headers=headers, proxies=proxies)
        print(f"Region Login Response Status Code: {response.status_code}")
        print(f"Region Login Response Text: {response.text}")
        response.raise_for_status()
        auth_data = response.json().get('data')
        if not auth_data or 'authTicket' not in auth_data:
            raise ValueError("Region login response does not contain 'authTicket'")
    
    return auth_data['authTicket']['token']

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.get(data_url, headers=headers, proxies=proxies)
    print(f"Glucose Data Response Status Code: {response.status_code}")
    print(f"Glucose Data Response Text: {response.text}")
    response.raise_for_status()
    connections = response.json().get('data')
    glucose_data = []
    for connection in connections:
        if 'glucoseMeasurement' in connection:
            glucose_measurement = connection['glucoseMeasurement']
            glucose_data.append({
                'Connection ID': connection['id'],
                'Timestamp': glucose_measurement['Timestamp'],
                'Value': glucose_measurement['Value']
            })
        else:
            print(f"No glucose measurement data available for connection ID: {connection['id']}")
    return glucose_data

def fetch_glucose_data():
    global session_token, glucose_data
    try:
        if session_token is None:
            session_token = get_librelinkup_session()
        glucose_data = get_glucose_data(session_token)
        print("Glucose data updated.")
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_glucose_data, 'interval', minutes=1)
scheduler.start()

@app.route('/glucose', methods=['GET'])
def glucose():
    return jsonify(glucose_data)

if __name__ == '__main__':
    try:
        fetch_glucose_data()  # Initial fetch
    except Exception as e:
        print(f"An error occurred during initial fetch: {e}")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
