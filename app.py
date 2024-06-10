from flask import Flask, jsonify
import requests
import json
import os
import datetime
import urllib.request
from dotenv import load_dotenv
import logging
import threading
import time
import schedule

app = Flask(__name__)

# Configurer les logs
logging.basicConfig(level=logging.DEBUG)

# Charger les variables d'environnement depuis un fichier .env si présent
load_dotenv()

# Définir les variables d'environnement
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')

glucose_data = {}

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
    
    try:
        req = urllib.request.Request(login_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            logging.info(f"Response Status Code: {response.getcode()}")
            logging.info(f"Response Text: {response_data}")
            response_json = json.loads(response_data)
            
            if 'redirect' in response_json['data'] and response_json['data']['redirect']:
                region = response_json['data']['region']
                login_url = f'https://api-{region}.libreview.io/llu/auth/login'
                req = urllib.request.Request(login_url, data=json.dumps(payload).encode('utf-8'), headers=headers)
                with urllib.request.urlopen(req) as response:
                    response_data = response.read().decode('utf-8')
                    logging.info(f"Response Status Code after redirect: {response.getcode()}")
                    logging.info(f"Response Text after redirect: {response_data}")
                    response_json = json.loads(response_data)

            return response_json['data']['authTicket']['token']
    except Exception as e:
        logging.error(f"Error during LibreLinkUp session retrieval: {e}")
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
    
    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}',
        'https': f'http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}'
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)
    
    try:
        req = urllib.request.Request(data_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            logging.info(f"Response Status Code: {response.getcode()}")
            logging.info(f"Response Text: {response_data}")
            response_json = json.loads(response_data)
            return response_json['data']
    except urllib.error.HTTPError as e:
        logging.error(f"HTTP error occurred: {e.code} - {e.reason}")
        if e.code == 401:
            logging.error("Unauthorized access - possible issues with session token.")
        raise
    except Exception as e:
        logging.error(f"Error during glucose data retrieval: {e}")
        raise

@app.route('/update_glucose', methods=['POST'])
def update_glucose():
    global glucose_data
    try:
        session_token = get_librelinkup_session()
        glucose_data = get_glucose_data(session_token)
        logging.info("Glucose data updated successfully.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Failed to update glucose data: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_glucose', methods=['GET'])
def get_glucose():
    if glucose_data:
        glucose_measurements = [
            {
                "timestamp": item["glucoseMeasurement"]["Timestamp"],
                "value": item["glucoseMeasurement"]["Value"]
            }
            for item in glucose_data
        ]
        return jsonify(glucose_measurements), 200
    return jsonify([]), 200

def job():
    with app.app_context():
        update_glucose()

# Planifiez le travail à exécuter chaque minute
schedule.every(1).minute.do(job)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Exécuter le planificateur dans un thread séparé
    scheduler_thread = threading.Thread(target=run_schedule)
    scheduler_thread.start()
    
    # Exécuter l'application Flask
    app.run(host='0.0.0.0', port=5000)
