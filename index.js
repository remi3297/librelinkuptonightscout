const express = require('express');
const axios = require('axios');
const cron = require('node-cron');
const zlib = require('zlib');

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
        'product': 'llu.android',
        'version': '4.2.1',
      },
      decompress: true,
    });

    const loginData = await new Promise((resolve, reject) => {
      zlib.gunzip(loginResponse.data, (err, decompressedData) => {
        if (err) {
          reject(err);
        } else {
          resolve(JSON.parse(decompressedData.toString()));
        }
      });
    });

    authToken = loginData.data.authTicket.token;
    console.log('Access Token:', authToken);
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
        'product': 'llu.android',
        'version': '4.2.1',
      },
      decompress: true,
    });

    const connectionsData = await new Promise((resolve, reject) => {
      zlib.gunzip(connectionsResponse.data, (err, decompressedData) => {
        if (err) {
          reject(err);
        } else {
          resolve(JSON.parse(decompressedData.toString()));
        }
      });
    });

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
          'product': 'llu.android',
          'version': '4.2.1',
        },
        decompress: false,
      });

      const glucoseData = await new Promise((resolve, reject) => {
        zlib.gunzip(glucoseResponse.data, (err, decompressedData) => {
          if (err) {
            reject(err);
          } else {
            resolve(JSON.parse(decompressedData.toString()));
          }
        });
      });

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
