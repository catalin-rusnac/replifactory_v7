// api.js
import axios from 'axios';

let baseURL = window.location.origin + '/api';

if (process.env.NODE_ENV === 'development') {
  baseURL = 'http://192.168.56.113:5000';
}

const api = axios.create({
  baseURL: baseURL
});

export default api;