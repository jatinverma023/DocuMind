import { createContext, useContext, useState } from "react";
import api, { setAuthToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function login(email, password) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/auth/login", { email, password });
      setAuthToken(res.data.access_token);
      setUser(res.data.user);
      return true;
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
      return false;
    } finally {
      setLoading(false);
    }
  }

  async function register(name, email, password) {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/auth/register", { name, email, password });
      setAuthToken(res.data.access_token);
      setUser(res.data.user);
      return true;
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
      return false;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setAuthToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}