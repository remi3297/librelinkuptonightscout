import requests
import json
import os
import datetime
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
glucose_data = {}

LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')

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
        response.raise_for_status()
        return response.json()['data']['authTicket']
    except requests.exceptions.RequestException as e:
        print(f"Error during LibreLinkUp session retrieval: {e}")
        return None

def get_glucose_data(session_token):
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    try:
        response = requests.get(data_url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except requests.exceptions.RequestException as e:
        print(f"Error during glucose data retrieval: {e}")
        return None

def update_glucose():
    global glucose_data
    session = get_librelinkup_session()
    if session:
        data = get_glucose_data(session['token'])
        if data:
            glucose_data = data
            print(f"Glucose data updated successfully at {datetime.datetime.now()}")
        else:
            print("Failed to retrieve glucose data.")
    else:
        print("Failed to retrieve session token.")

@app.route('/get_glucose', methods=['GET'])
def get_glucose():
    if 'glucoseMeasurement' in glucose_data[0]:
        glucose_measurement = glucose_data[0]['glucoseMeasurement']
        return jsonify({
            'timestamp': glucose_measurement['Timestamp'],
            'glucose_value': glucose_measurement['Value']
        })
    else:
        return jsonify(glucose_data), 200

@app.route('/update_glucose', methods=['POST'])
def update_glucose_route():
    update_glucose()
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_glucose, 'interval', minutes=1)
    scheduler.start()
    print("Starting the Flask app and scheduling updates.")
    app.run(host='0.0.0.0', port=5000)
