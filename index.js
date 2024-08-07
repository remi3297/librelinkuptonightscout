const express = require('express');
const axios = require('axios');
const cron = require('node-cron');
const HttpsProxyAgent = require('https-proxy-agent');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

let latestGlucoseData = null;
let authToken = null;

// Configuration du proxy
const proxyUrl = `http://${process.env.PROXY_USERNAME}:${process.env.PROXY_PASSWORD}@${process.env.PROXY_URL}`;
const agent = new HttpsProxyAgent(proxyUrl);

async function authenticate() {
  try {
    const loginResponse = await axios.post('https://api-fr.libreview.io/llu/auth/login', {
      email: process.env.LIBRELINKUP_EMAIL,
      password: process.env.LIBRELINKUP_PASSWORD,
    }, {
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios',
      },
      httpsAgent: agent // Utilisation de l'agent proxy
    });

    const loginData = loginResponse.data;
    console.log('Login Response:', loginData);

    if (loginData.data && loginData.data.authTicket && loginData.data.authTicket.token) {
      authToken = loginData.data.authTicket.token;
      console.log('Access Token:', authToken);
    } else {
      throw new Error('Réponse d\'authentification inattendue');
    }
  } catch (error) {
    console.error('Erreur lors de l\'authentification:', error.response ? error.response.data : error);
    throw error;
  }
}

async function fetchGlucoseData() {
  try {
    if (!authToken) {
      await authenticate();
    }

    const connectionsResponse = await axios.get('https://api-fr.libreview.io/llu/connections', {
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios',
      },
      httpsAgent: agent // Utilisation de l'agent proxy
    });

    console.log('Connections Response:', connectionsResponse.data);  // Log complet des données reçues

    const connectionsData = connectionsResponse.data;
    const connections = connectionsData.data;
    console.log('Connections:', connections);

    if (connections.length === 0) {
      console.log('Aucune connexion trouvée. Vérifiez les paramètres de partage de données dans votre compte LibreLinkUp.');
      return;
    }

    for (const connection of connections) {
      console.log(`Connection ID: ${connection.id}`);

      if (connection.glucoseMeasurement) {
        latestGlucoseData = connection.glucoseMeasurement;
        console.log(`Date: ${latestGlucoseData.Timestamp}, Glucose Value: ${latestGlucoseData.Value}`);
      } else {
        console.log('No glucose measurement data available.');
      }
    }
  } catch (error) {
    console.error('Erreur lors de la récupération des données de glycémie:', error.response ? error.response.data : error);
  }
}

app.get('/glucose', (req, res) => {
  if (latestGlucoseData && latestGlucoseData.Value) {
    let modifiedValue = latestGlucoseData.Value;
    if (modifiedValue >= 70 && modifiedValue <= 100) {
      modifiedValue -= 20;
    } else if (modifiedValue >= 120 && modifiedValue <= 160) {
      modifiedValue += 20;
    }
    res.json({ value: modifiedValue,
             delayMin: process.env.DELAY_MIN,
             delayMax: process.env.DELAY_MAX,
             spasmMin: process.env.SPASM_MIN,
             spasmMax: process.env.SPASM_MAX,
             amplitudeMin: process.env.AMPLITUDE_MIN,
             glucoseMax: process.env.GLUCOSE_MAX,
             glucoseMin: process.env.GLUCOSE_MIN,
             });
  } else {
    res.status(404).json({ error: 'No glucose data available' });
  }
});

cron.schedule('* * * * *', fetchGlucoseData);

app.listen(port, () => {
  console.log(`Serveur en écoute sur le port ${port}`);
});
