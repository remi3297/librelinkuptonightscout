from flask import Flask, jsonify
import requests
import json
import os
import logging
from dotenv import load_dotenv

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

BASE_URL = 'https://api-eu.libreview.io'
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
    'product': 'llu.android',
    'version': '4.7.0'
}

glucose_data = {}

def get_librelinkup_session():
    login_url = f'{BASE_URL}/llu/auth/login'
    payload = {
        'email': LIBRELINKUP_EMAIL,
        'password': LIBRELINKUP_PASSWORD
    }
    
    try:
        response = requests.post(login_url, headers=HEADERS, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        if response_data['status'] == 0 and 'redirect' in response_data['data']:
            region = response_data['data']['region']
            login_url = f'https://api-{region}.libreview.io/llu/auth/login'
            response = requests.post(login_url, headers=HEADERS, json=payload)
            response.raise_for_status()
            response_data = response.json()
        
        return response_data['data']['authTicket']['token']
    except Exception as e:
        logging.error(f"Error during LibreLinkUp session retrieval: {e}")
        raise

def get_patient_connections(session_token):
    connections_url = f'{BASE_URL}/llu/connections'
    headers = {**HEADERS, 'authorization': f'Bearer {session_token}'}
    
    try:
        response = requests.get(connections_url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except Exception as e:
        logging.error(f"Error during patient connections retrieval: {e}")
        raise

def get_glucose_data(session_token, patient_id):
    data_url = f'{BASE_URL}/llu/connections/{patient_id}/graph'
    headers = {**HEADERS, 'authorization': f'Bearer {session_token}'}
    
    try:
        response = requests.get(data_url, headers=headers)
        response.raise_for_status()
        return response.json()['data']
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error occurred: {e.response.status_code} - {e.response.reason}")
        if e.response.status_code == 401:
            logging.error("Unauthorized access - possible issues with session token.")
        raise
    except Exception as e:
        logging.error(f"Error during glucose data retrieval: {e}")
        raise

def update_glucose_data():
    global glucose_data
    logging.info("Starting glucose data update")
    try:
        session_token = get_librelinkup_session()
        connections = get_patient_connections(session_token)
        if connections:
            patient_id = connections[0]['patientId']
            new_data = get_glucose_data(session_token, patient_id)
            if new_data:
                glucose_data = new_data
                logging.info(f"Glucose data updated successfully: {glucose_data}")
            else:
                logging.warning("No new glucose data retrieved.")
        else:
            logging.warning("No patient connections found.")
    except Exception as e:
        logging.error(f"Error during glucose data update: {e}")

@app.route('/get_glucose', methods=['GET'])
def get_glucose():
    global glucose_data
    if glucose_data and 'glucoseMeasurement' in glucose_data['connection']:
        glucose_value = glucose_data['connection']['glucoseMeasurement']['Value']
        return jsonify({"glucose_value": glucose_value}), 200
    return jsonify({"error": "No glucose data available"}), 404

@app.route('/update_glucose', methods=['POST'])
def trigger_update():
    update_glucose_data()
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    logging.info("Starting the Flask app.")
    app.run(host='0.0.0.0', port=5000)
