import express from 'express';
import cors from 'cors';
import ngrok from 'ngrok';
import { createProxyMiddleware } from 'http-proxy-middleware';
import path from 'path';
import fs from 'fs';
import os from 'os';
import util from 'util';
import { exec } from 'child_process';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';

const execAsync = util.promisify(exec);

// __dirname workaround for ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

const ngrokConfigPath = getNgrokConfigPath();

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

async function startNgrok() {
  console.log('Starting ngrok tunnel setup...');
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
  } else {
    console.log('ngrok tunnel already running at:', ngrokUrl);
  }
}

async function checkNgrokStatus() {
  if (fs.existsSync(ngrokConfigPath)) {
    const ngrokConfig = fs.readFileSync(ngrokConfigPath, 'utf8');

    const authtokenRegex = /authtoken:\s(.+)/;
    const authtokenMatch = ngrokConfig.match(authtokenRegex);

    if (authtokenMatch && authtokenMatch[1]) {
      authtoken = authtokenMatch[1];
      console.log('ngrok authtoken found.');
      try {
        await startNgrok();
      } catch (error) {
        console.error('Failed to start ngrok:', error);
      }
    }
  }
}

async function initializeNgrok() {
  try {
    await checkNgrokStatus();
    setInterval(checkNgrokStatus, 60 * 1000);
    console.log('Ngrok initialization complete.');
  } catch (error) {
    console.error('Error initializing ngrok:', error);
  }
}

initializeNgrok().catch(error => {
  console.error('Failed to initialize ngrok:', error);
});

app.post('/tunnels/set-ngrok-authtoken', async (req, res) => {
  const { authtoken } = req.body;
  try {
    console.log('Setting ngrok authtoken...');
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
  console.log('Getting ngrok url:', req.path);
  res.json({ ngrokUrl: ngrokUrl });
});

app.listen(expressPort, () => {
  console.log(`Express app listening on port ${expressPort}`);
});
