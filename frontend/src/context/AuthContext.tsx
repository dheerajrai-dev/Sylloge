import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { loginUser } from '../api/services';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  demoLogin: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('sat_sa_jwt_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('sat_sa_user');
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('sat_sa_user');
      }
    }
    setIsLoading(false);
  }, [token]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await loginUser(username, password);
      setToken(resp.access_token);
      setUser(resp.user);
      localStorage.setItem('sat_sa_jwt_token', resp.access_token);
      localStorage.setItem('sat_sa_user', JSON.stringify(resp.user));
    } finally {
      setIsLoading(false);
    }
  };

  const demoLogin = async () => {
    await login('supervisor', 'superpass123!');
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('sat_sa_jwt_token');
    localStorage.removeItem('sat_sa_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        demoLogin,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
