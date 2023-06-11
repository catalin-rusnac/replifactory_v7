const express = require('express');
const cors = require('cors');
const ngrok = require('ngrok');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');


const app = express();
const expressPort = 3000;

// Added console log before creating the middleware
console.log('Initializing middleware');

// Wrap the middleware creation inside a variable for easier logging
const proxyMiddleware = createProxyMiddleware({
  target: 'http://127.0.0.1:5000',
  changeOrigin: true,
  pathRewrite: {
    '^/api': '', // remove the '/api' prefix when forwarding to the Flask server
  },
});
console.log('Proxying requests to Flask server at http://127.0.0.1:5000');

app.use('/api', (req, res, next) => {
  next();
}, proxyMiddleware);

// Added console log after adding the middleware
console.log('Middleware added to app');


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

const { spawn } = require('child_process');


async function startNgrok() {
  console.log('Starting ngrok tunnel setup...');
  //if not running
    if (!ngrokUrl) {
      ngrokUrl = await ngrok.connect({
        addr: expressPort,
      });
        const pythonScriptPath = path.join(__dirname, 'url_into_sheet.py');
        const pythonScript = spawn('python', [pythonScriptPath]);
      pythonScript.stdout.on('data', (data) => {
      console.log(`Python script output: ${data}`);
        });

      console.log(`ngrok tunnel started: ${ngrokUrl}`);
    }
    else {
      console.log('ngrok tunnel already running at:', ngrokUrl);
    }
}

async function checkNgrokStatus() {


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
}

async function initializeNgrok() {
  try {
    await checkNgrokStatus();
    // Check ngrok status every 5 minutes
    setInterval(checkNgrokStatus, 60 * 1000);
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

app.get('/tunnels/get-ngrok-url', (req, res) => {
  console.log('Getting ngrok url:',req.path);
  res.json({ ngrokUrl: ngrokUrl });
});


app.listen(expressPort, () => {
  console.log(`Express app listening on port ${expressPort}`);
});
