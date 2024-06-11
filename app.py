from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import json
import os

# Chargement des variables d'environnement pour les identifiants
LIBRELINKUP_EMAIL = os.getenv('LIBRELINKUP_EMAIL')
LIBRELINKUP_PASSWORD = os.getenv('LIBRELINKUP_PASSWORD')

app = Flask(__name__)
scheduler = BackgroundScheduler()

def get_librelinkup_session():
    print("Tentative de connexion à LibreLinkUp...")
    login_url = 'https://api.libreview.io/llu/auth/login'
    payload = {'email': LIBRELINKUP_EMAIL, 'password': LIBRELINKUP_PASSWORD}
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.post(login_url, data=json.dumps(payload), headers=headers)
    if response.status_code == 200:
        print("Connexion réussie.")
    else:
        print(f"Échec de la connexion, statut: {response.status_code}")
    response.raise_for_status()
    return response.json()['data']['authTicket']

def fetch_glucose_data():
    print("Récupération du token de session...")
    session_token = get_librelinkup_session()
    print("Récupération des données de glycémie...")
    data_url = 'https://api.libreview.io/llu/connections'
    headers = {
        'authorization': f'Bearer {session_token["token"]}',
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios'
    }
    response = requests.get(data_url, headers=headers)
    if response.status_code == 200:
        print("Données récupérées avec succès.")
    else:
        print(f"Échec de la récupération des données, statut: {response.status_code}")
    response.raise_for_status()
    return response.json()['data']

latest_data = []

@app.route('/glucose')
def glucose():
    print("Demande de données de glycémie reçue...")
    return jsonify(latest_data)

@scheduler.scheduled_job('interval', minutes=1)
def timed_job():
    print("Exécution de la tâche planifiée...")
    global latest_data
    try:
        latest_data = fetch_glucose_data()
        print("Mise à jour des données réussie.")
    except Exception as e:
        print(f"Une erreur est survenue lors de la mise à jour des données: {e}")

if __name__ == '__main__':
    print("Démarrage du scheduler...")
    scheduler.start()
    print("Démarrage du serveur Flask...")
    app.run(host='0.0.0.0', port=5000)
