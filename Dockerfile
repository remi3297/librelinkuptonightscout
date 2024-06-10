FROM python:3.9-slim

RUN apt-get update && apt-get install -y cron curl

# Installer les dépendances Python
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copier le script cronjob
COPY cronjob.sh /cronjob.sh
RUN chmod +x /cronjob.sh

# Ajouter la tâche cron
RUN echo "* * * * * /cronjob.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/update_glucose
RUN chmod 0644 /etc/cron.d/update_glucose

# Appliquer la tâche cron
RUN crontab /etc/cron.d/update_glucose

# Copier le code de l'application
COPY . .

# Exposer le port de l'application
EXPOSE 5000

# Démarrer cron et l'application Flask avec Gunicorn
CMD cron && gunicorn --bind 0.0.0.0:5000 app:app
