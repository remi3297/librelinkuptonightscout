const express = require('express');
const axios = require('axios');
const cron = require('node-cron');

require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

let latestGlucoseData = null;
let authToken = null;

async function authenticate() {
  try {
    const loginResponse = await axios.post('https://api.libreview.io/llu/auth/login', {
      email: process.env.LIBRELINKUP_EMAIL,
      password: process.env.LIBRELINKUP_PASSWORD,
    }, {
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios',
      },
      maxRedirects: 0,
    });

    const loginData = loginResponse.data;
    console.log('Login Response:', loginData);

    if (loginData.status === 0 && loginData.data && loginData.data.redirect) {
      const redirectUrl = `https://api-${loginData.data.region}.libreview.io/llu/auth/login`;
      console.log('Redirection vers:', redirectUrl);

      const redirectResponse = await axios.post(redirectUrl, {
        email: process.env.LIBRELINKUP_EMAIL,
        password: process.env.LIBRELINKUP_PASSWORD,
      }, {
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
          'version': '4.7.0',
          'product': 'llu.ios',
        },
      });

      const redirectData = redirectResponse.data;
      console.log('Redirect Response:', redirectData);

      if (redirectData.data && redirectData.data.authTicket && redirectData.data.authTicket.token) {
        authToken = redirectData.data.authTicket.token;
        console.log('Access Token:', authToken);
      } else {
        throw new Error('Réponse d\'authentification inattendue après redirection');
      }
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

    const patientId = 'YOUR_PATIENT_ID'; // Remplacez par l'identifiant du patient

    const glucoseResponse = await axios.get(`https://api.libreview.io/llu/connections/${patientId}/graph`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
        'User-Agent': 'FreeStyle LibreLink Up/4.7.0 (iOS; 15.2; iPhone; en_US)',
        'version': '4.7.0',
        'product': 'llu.ios',
      },
    });

    const glucoseData = glucoseResponse.data;
    console.log('Glucose Data:', glucoseData);

    if (glucoseData.data && glucoseData.data.connection && glucoseData.data.connection.glucoseMeasurement) {
      latestGlucoseData = glucoseData.data.connection.glucoseMeasurement;
      console.log(`Date: ${latestGlucoseData.Timestamp}, Glucose Value: ${latestGlucoseData.Value}`);
    } else {
      console.log('No glucose measurement data available.');
    }
  } catch (error) {
    console.error('Erreur lors de la récupération des données de glycémie:', error.response ? error.response.data : error);
  }
}

app.get('/glucose', (req, res) => {
  res.json(latestGlucoseData);
});

cron.schedule('* * * * *', fetchGlucoseData);

app.listen(port, () => {
  console.log(`Serveur en écoute sur le port ${port}`);
});
