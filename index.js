const express = require('express');
const axios = require('axios');
const cron = require('node-cron');

require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

let latestGlucoseData = null;

async function fetchGlucoseData() {
  try {
    const response = await axios.post('https://api-eu.libreview.io/auth/login', {
      email: process.env.LIBRELINKUP_EMAIL,
      password: process.env.LIBRELINKUP_PASSWORD,
    });

    const token = response.data.access_token;

    const glucoseResponse = await axios.get('https://api-eu.libreview.io/glucose/latest', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    latestGlucoseData = glucoseResponse.data;
  } catch (error) {
    console.error('Erreur lors de la récupération des données de glycémie:', error);
  }
}

app.get('/glucose', (req, res) => {
  res.json(latestGlucoseData);
});

cron.schedule('* * * * *', fetchGlucoseData);

app.listen(port, () => {
  console.log(`Serveur en écoute sur le port ${port}`);
});
