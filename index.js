const express = require('express');
const axios = require('axios');
const cron = require('node-cron');

require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

let latestGlucoseData = null;

async function fetchGlucoseData() {
  try {
    // Étape 1 : Authentification
    const loginResponse = await axios.post('https://api.libreview.io/llu/auth/login', {
      email: process.env.LIBRELINKUP_EMAIL,
      password: process.env.LIBRELINKUP_PASSWORD,
    });

    const token = loginResponse.data.token;
    console.log('Access Token:', token);

    // Étape 2 : Récupération des connexions
    const connectionsResponse = await axios.get('https://api.libreview.io/llu/connections', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const connections = connectionsResponse.data;
    console.log('Connections:', connections);

    if (connections.length > 0) {
      const patientId = connections[0].patientId;

      // Étape 3 : Récupération des données de glycémie
      const glucoseResponse = await axios.get(`https://api.libreview.io/llu/connections/${patientId}/graph`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      latestGlucoseData = glucoseResponse.data;
      console.log('Latest Glucose Data:', latestGlucoseData);
    } else {
      console.log('Aucune connexion trouvée.');
    }
  } catch (error) {
    console.error('Erreur lors de la récupération des données de glycémie:', error.response.data);
  }
}

app.get('/glucose', (req, res) => {
  res.json(latestGlucoseData);
});

cron.schedule('* * * * *', fetchGlucoseData);

app.listen(port, () => {
  console.log(`Serveur en écoute sur le port ${port}`);
});
