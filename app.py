from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json
import os

# Extraction des informations de connexion des variables d'environnement
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')

app = Flask(__name__)
scheduler = BackgroundScheduler()

def get_librelinkup_session():
    login_url = 'https://api.libreview.io/llu/auth/login'
    payload = {'email': LIBRELINKUP_EMAIL, 'password': LIBRELINKUP_PASSWORD}
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.post(login_url, data=json.dumps(payload), headers=headers)
    response.raise_for_status()
    return response.json()['data']['authTicket']

def fetch_glucose_data():
    session_token = get_librelinkup_session()
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token["token"]}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.get(data_url, headers=headers)
    response.raise_for_status()
    return response.json()['data']

latest_data = []

@app.route('/glucose')
def glucose():
    return jsonify(latest_data)

@scheduler.scheduled_job('interval', minutes=1)
def timed_job():
    global latest_data
    try:
        latest_data = fetch_glucose_data()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    scheduler.start()
    app.run(host='0.0.0.0', port=5000)
