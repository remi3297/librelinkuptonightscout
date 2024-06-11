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
    response.raise_for_status()
    return response.json()['data']['authTicket']

def get_glucose_data():
    global session_token, glucose_data
    if session_token is None:
        session_token = get_librelinkup_session()
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.get(data_url, headers=headers, proxies=proxies)
    response.raise_for_status()
    glucose_data = response.json()['data']

def fetch_glucose_data():
    try:
        get_glucose_data()
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
    fetch_glucose_data()  # Initial fetch
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
