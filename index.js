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
        'accept-encoding': 'gzip',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'product': 'llu.ios',
        'version': '4.2.1',
      },
      maxRedirects: 0, // Empêche Axios de suivre automatiquement les redirections
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
          'accept-encoding': 'gzip',
          'cache-control': 'no-cache',
          'connection': 'Keep-Alive',
          'content-type': 'application/json',
          'product': 'llu.ios',
          'version': '4.2.1',
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

    // Étape 2 : Récupération des connexions
    const connectionsResponse = await axios.get('https://api.libreview.io/llu/connections', {
      headers: {
        Authorization: `Bearer ${authToken}`,
        'accept-encoding': 'gzip',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'product': 'llu.ios',
        'version': '4.2.1',
      },
    });

    const connectionsData = connectionsResponse.data;
    const connections = connectionsData.data;
    console.log('Connections:', connections);

    if (connections.length > 0) {
      const patientId = connections[0].patientId;

      // Étape 3 : Récupération des données de glycémie
      const glucoseResponse = await axios.get(`https://api.libreview.io/llu/connections/${patientId}/graph`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          'accept-encoding': 'gzip',
          'cache-control': 'no-cache',
          'connection': 'Keep-Alive',
          'content-type': 'application/json',
          'product': 'llu.ios',
          'version': '4.2.1',
        },
      });

      const glucoseData = glucoseResponse.data;
      latestGlucoseData = glucoseData.data.connection.glucoseMeasurement;
      console.log('Latest Glucose Data:', latestGlucoseData);
    } else {
      console.log('Aucune connexion trouvée.');
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
