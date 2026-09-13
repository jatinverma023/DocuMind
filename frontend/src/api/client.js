import axios from "axios";

// Deliberately NOT using localStorage for the token — it's readable by any
// JS on the page (XSS risk). Token lives only in React state (AuthContext)
// and is injected here per-request. Trade-off: refreshing the page logs
// you out. Fine for this project's scale; a real app would use an
// httpOnly cookie instead, which needs backend cookie support to add.
let currentToken = null;

export function setAuthToken(token) {
  currentToken = token;
}

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

api.interceptors.request.use((config) => {
  if (currentToken) {
    config.headers.Authorization = `Bearer ${currentToken}`;
  }
  return config;
});

export default api;