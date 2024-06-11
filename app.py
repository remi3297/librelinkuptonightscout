from flask import Flask, jsonify
import requests
import json
import os
import datetime
import urllib.request
from dotenv import load_dotenv
import logging
import threading

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
    login_url = 'https://api-eu.libreview.io/llu/auth/login'  # Utilisation de l'API européenne
    payload = {
        'email': LIBRELINKUP_EMAIL,
        'password': LIBRELINKUP_PASSWORD
    }
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.2.1',  # Version spécifique du tutoriel
        'product': 'llu.ios',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive'
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
            return response_json['data']['authTicket']['token']
    except Exception as e:
        logging.error(f"Error during LibreLinkUp session retrieval: {e}")
        raise

def get_glucose_data(session_token):
    data_url = 'https://api-eu.libreview.io/llu/connections'  # Utilisation de l'API européenne
    headers = {
        'authorization': f'Bearer {session_token}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.2.1',  # Version spécifique du tutoriel
        'accept-encoding': 'gzip',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive'
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

def update_glucose_data():
    global glucose_data
    try:
        session_token = get_librelinkup_session()
        glucose_data = get_glucose_data(session_token)
        logging.info(f"Glucose data updated successfully: {glucose_data}")
    except Exception as e:
        logging.error(f"Error during glucose data update: {e}")

def schedule_updates():
    update_glucose_data()
    threading.Timer(60, schedule_updates).start()  # Planifier la mise à jour toutes les minutes

@app.route('/get_glucose', methods=['GET'])
def get_glucose():
    global glucose_data
    if glucose_data and 'glucoseMeasurement' in glucose_data[0]:
        glucose_value = glucose_data[0]['glucoseMeasurement']['Value']
        return jsonify({"glucose_value": glucose_value}), 200
    return jsonify({"error": "No glucose data available"}), 404

@app.route('/update_glucose', methods=['POST'])
def trigger_update():
    update_glucose_data()
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    logging.info("Starting the Flask app and scheduling updates.")
    schedule_updates()  # Commencer la mise à jour périodique des données de glucose
    app.run(host='0.0.0.0', port=5000)
