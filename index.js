const express = require('express');
const axios = require('axios');
const cron = require('node-cron');
const zlib = require('zlib');

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
    }, {
      headers: {
        'accept-encoding': 'gzip',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'product': 'llu.android',
        'version': '4.2.1',
      },
      decompress: false,
    });

    const token = loginResponse.data.token;
    console.log('Access Token:', token);

    // Étape 2 : Récupération des connexions
    const connectionsResponse = await axios.get('https://api.libreview.io/llu/connections', {
      headers: {
        Authorization: `Bearer ${token}`,
        'accept-encoding': 'gzip',
        'cache-control': 'no-cache',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'product': 'llu.android',
        'version': '4.2.1',
      },
      decompress: false,
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

    const connections = connectionsData.connections;
    console.log('Connections:', connections);

    if (connections.length > 0) {
      const patientId = connections[0].patientId;

      // Étape 3 : Récupération des données de glycémie
      const glucoseResponse = await axios.get(`https://api.libreview.io/llu/connections/${patientId}/graph`, {
        headers: {
          Authorization: `Bearer ${token}`,
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

      latestGlucoseData = glucoseData;
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
