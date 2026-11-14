import { createContext, useContext, useEffect, useState } from "react";
import authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const [loading, setLoading] = useState(true);

  // Restore authenticated session on initial mount or token change
  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setLoading(false);
        }
        return;
      }

      try {
        const profile = await authService.getProfile();
        if (isMounted) {
          setUser(profile);
          setToken(storedToken);
        }
      } catch (err) {
        console.warn("Session restore failed, clearing invalid/expired token:", err.message);
        authService.logout();
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  /**
   * Log in user with credentials and store access token.
   */
  const login = async (email, password) => {
    const data = await authService.login(email, password);
    const accessToken = data.session?.access_token || data.access_token;
    const profile = data.profile;

    if (!accessToken) {
      throw new Error("Authentication response did not contain a valid access token.");
    }

    localStorage.setItem("access_token", accessToken);
    setToken(accessToken);

    if (profile) {
      setUser(profile);
    } else {
      const fetchedProfile = await authService.getProfile();
      setUser(fetchedProfile);
    }
    return data;
  };

  /**
   * Register a new citizen account.
   * Handles registration responses with or without an active session.
   */
  const register = async (userData) => {
    const data = await authService.register(userData);
    const accessToken = data.session?.access_token || data.access_token;
    const profile = data.profile;

    if (accessToken && profile) {
      localStorage.setItem("access_token", accessToken);
      setToken(accessToken);
      setUser(profile);
    } else {
      // Registration succeeded without an active session (e.g. email verification required).
      // Keep frontend state unauthenticated.
      localStorage.removeItem("access_token");
      setToken(null);
      setUser(null);
    }
    return data;
  };

  /**
   * Log out user and clear state.
   */
  const logout = () => {
    authService.logout();
    setToken(null);
    setUser(null);
  };

  // Authoritative role helpers derived strictly from backend profile
  const isCitizen = user?.role === "citizen";
  const isOfficial = user?.role === "official";
  const isWorker = user?.role === "worker";
  const isSafetyOfficer = Boolean(user?.role === "official" && user?.is_safety_officer === true);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: Boolean(token && user),
        isCitizen,
        isOfficial,
        isWorker,
        isSafetyOfficer,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
