// api.js
import axios from 'axios';

let baseURL = window.location.origin + '/flask';

if (process.env.NODE_ENV === 'development') {
  baseURL = 'http://localhost:5000';
}

const api = axios.create({
  baseURL: baseURL
});

export default api;