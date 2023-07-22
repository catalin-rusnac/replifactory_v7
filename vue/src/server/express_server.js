const express = require('express');
const cors = require('cors');
const ngrok = require('ngrok');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');
const sheetUtil = require('./url_into_sheet.js');
const axios = require('axios');
const fs = require('fs');
const os = require('os');

const currentDirrectory = `${path.dirname(require.main.filename)}`
const app = express();
const expressPort = process.env.PORT || 3000;
const proxyTarget = process.env.PROXY_TARGET || 'http://127.0.0.1:5000';
const staticDir = process.env.STATIC_DIR || path.join(__dirname, '../../dist');
const ngrokApiUrl = process.env.NGROK_API_URL || 'http://127.0.0.1:4040';
const gcpSheetsConfig = process.env.GCP_SHEETS_CONFIG || `${currentDirrectory}/../../../secrets/googlesheet.json`;
const checkNgrokStatusDelay = parseInt(process.env.CHECK_NGROK_STATUS_DELAY || 1000);
const checkNgrokStatusInterval = parseInt(process.env.CHECK_NGROK_STATUS_INTERVAL || 60 * 1000);
const gcpSheetName = process.env.GCP_SHEET_NAME || os.hostname();

// Added console log before creating the middleware
console.log('Initializing middleware');

// Wrap the middleware creation inside a variable for easier logging
const proxyMiddleware = createProxyMiddleware({
  target: proxyTarget,
  changeOrigin: true,
  pathRewrite: {
    '^/api': '', // remove the '/api' prefix when forwarding to the Flask server
  },
});
console.log(`Proxying requests to Flask server at ${proxyTarget}`);

app.use('/api', (req, res, next) => {
  next();
}, proxyMiddleware);

// Added console log after adding the middleware
console.log('Middleware added to app');


app.use(express.json());
app.use(express.static(staticDir));
console.log(`Static location: ${staticDir}`);

// Allow requests from specific origins
app.use(cors());

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

const ngrokConfigPath = getNgrokConfigPath();
const util = require('util');
const execAsync = util.promisify(require('child_process').exec);

function getNgrokConfigPath() {
  switch (os.platform()) {
    case 'win32':
      return `${process.env.LOCALAPPDATA}\\ngrok\\ngrok.yml`;
    case 'darwin':
      return `${os.homedir()}/Library/Application Support/ngrok/ngrok.yml`;
    case 'linux':
      return `${os.homedir()}/.config/ngrok/ngrok.yml`;
    default:
      throw new Error('Unsupported platform');
  }
}

let authtoken = null;
let ngrokUrl = null;
let sshUrl = null;

async function uploadNgrokUrlToSpreadsheets(ngrokUrl) {
  const jsonString = fs.readFileSync(gcpSheetsConfig, 'utf8');
  console.debug(`read ${gcpSheetsConfig}: ${jsonString}`)
  const spreadsheetId = JSON.parse(jsonString).id;
  console.debug(`spreadsheetId: ${spreadsheetId}`)
  await sheetUtil.writeUrlToGoogleSheet(spreadsheetId, gcpSheetName, ngrokUrl)
  console.log(`ngrok tunnel URL published to: https://docs.google.com/spreadsheets/d/${spreadsheetId}`);

} 


async function startNgrok() {
  console.log('Starting ngrok tunnel setup...');
  //if not running
    if (!ngrokUrl) {
      ngrokUrl = await ngrok.connect({
        addr: expressPort,
      });
      console.log(`ngrok tunnel started: ${ngrokUrl}`);
      await uploadNgrokUrlToSpreadsheets(ngrokUrl)
    }
    else {
      console.log('ngrok tunnel already running at:', ngrokUrl);
    }
}

async function checkNgrokStatus() {
  console.log("Checking ngrok status...");

// Check if ngrok.yml file exists
if (fs.existsSync(ngrokConfigPath)) {
  // Read the ngrok.yml file
  const ngrokConfig = fs.readFileSync(ngrokConfigPath, 'utf8');

  // Extract the authtoken value from ngrokConfig using regular expression
  const authtokenRegex = /authtoken:\s(.+)/;
  const authtokenMatch = ngrokConfig.match(authtokenRegex);

  if (authtokenMatch && authtokenMatch[1]) {
    authtoken = authtokenMatch[1];
    console.log(`ngrok authtoken found.`);
    startNgrok().catch(error => { // Catch the error here
      console.error('Failed to start ngrok:', error);
    });
  }
} else {
  console.warn("Ngrok config doesn't exists:", ngrokConfigPath);
  console.debug(`Check ngrok API: ${ngrokApiUrl}/api/tunnels`)
  axios.get(`${ngrokApiUrl}/api/tunnels`)
  .then(response => {
    // console.debug(response);
    ngrokUrl = response.data.tunnels[0].public_url;
    console.info(`Ngrok tunnel address: ${ngrokUrl}`)
    uploadNgrokUrlToSpreadsheets(ngrokUrl)
  })
  .catch(error => {
    console.error(error);
  });
}
}

async function initializeNgrok() {
  try {
    // await new Promise(checkNgrokStatus => setTimeout(checkNgrokStatus, checkNgrokStatusDelay));
    await checkNgrokStatus()
    // Check ngrok status every 5 minutes
    setInterval(checkNgrokStatus, checkNgrokStatusInterval);
    console.log('Ngrok initialization complete.');
  } catch (error) {
    console.error('Error initializing ngrok:', error);
  }
}

//
initializeNgrok().catch(error => {
  console.error('Failed to initialize ngrok:', error);
});

app.post('/tunnels/set-ngrok-authtoken', async (req, res) => {
  const { authtoken } = req.body;
  try {
    console.log('Setting ngrok authtoken...')
    await execAsync(`ngrok config add-authtoken ${authtoken}`);
    console.log('ngrok authtoken set successfully.');
    await startNgrok();
    res.json({ message: 'ngrok authtoken set successfully.', ngrokUrl: ngrokUrl });
  } catch (error) {
    console.error('Error setting ngrok authtoken:', error);
    res.status(500).json({ error: 'Failed to set ngrok authtoken' });
  }
});


app.get('/tunnels/start-ssh', async (req, res) => {
  try {
    if (!sshUrl) {
      sshUrl = await ngrok.connect({
        proto: 'tcp',
        addr: 22,
      });
      res.json({ message: 'SSH ngrok tunnel started successfully.', sshUrl: sshUrl });
    } else {
      res.json({ message: 'SSH ngrok tunnel is already running.', sshUrl: sshUrl });
    }
  } catch (error) {
    console.error('Error starting SSH ngrok tunnel:', error);
    res.status(500).json({ error: 'Failed to start SSH ngrok tunnel' });
  }
});

app.get('/tunnels/stop-ssh', async (req, res) => {
  try {
    if (sshUrl) {
      await ngrok.disconnect(sshUrl);
      sshUrl = null;
      res.json({ message: 'SSH ngrok tunnel stopped successfully.' });
    } else {
      res.json({ message: 'No active SSH ngrok tunnel.' });
    }
  } catch (error) {
    console.error('Error stopping SSH ngrok tunnel:', error);
    res.status(500).json({ error: 'Failed to stop SSH ngrok tunnel' });
  }
});



app.get('/tunnels/get-ngrok-url', (req, res) => {
  console.log('Getting ngrok url:',req.path);
  res.json({ ngrokUrl: ngrokUrl });
});


app.listen(expressPort, () => {
  console.log(`Express app listening on port ${expressPort}`);
});
