const express = require('express');
const cors = require('cors');
const ngrok = require('ngrok');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');


const app = express();
const expressPort = 3000;

app.use('/flask', (req, res, next) => {
  console.log('Proxying requests to Flask server at http://127.0.0.1:5000');
  next();
}, createProxyMiddleware({
  target: 'http://127.0.0.1:5000',
  changeOrigin: false,
  pathRewrite: {
    '^/flask': '', // remove the '/flask' prefix when forwarding to the Flask server
  },
}));

app.use(express.json());
app.use(express.static(path.join(__dirname, '../../dist')));
console.log(path.join(__dirname, '../../dist'));

// Allow requests from specific origins
app.use(cors());

app.use((req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

const { exec } = require('child_process');
const fs = require('fs');

const os = require('os');
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


// Check if ngrok.yml file exists
if (fs.existsSync(ngrokConfigPath)) {
  // Read the ngrok.yml file
  const ngrokConfig = fs.readFileSync(ngrokConfigPath, 'utf8');

  // Extract the authtoken value from ngrokConfig using regular expression
  const authtokenRegex = /authtoken:\s(.+)/;
  const authtokenMatch = ngrokConfig.match(authtokenRegex);

  if (authtokenMatch && authtokenMatch[1]) {
    authtoken = authtokenMatch[1];
    console.log(`ngrok authtoken found: ${authtoken}`);
    startNgrok().catch(error => { // Catch the error here
      console.error('Failed to start ngrok:', error);
    });
  }
}


async function startNgrok() {
  console.log('Starting ngrok tunnel setup...');
  ngrokUrl = await ngrok.connect({
    addr: expressPort,
    });
  console.log(`ngrok tunnel started: ${ngrokUrl}`);
}

app.post('/api/setNgrokauthtoken', async (req, res) => {
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


app.get('/api/get-ngrok-url', (req, res) => {
  res.json({ ngrokUrl: ngrokUrl });
});




app.listen(expressPort, () => {
  console.log(`Express app listening at http://localhost:${expressPort}`);
});
