import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi } from "@/lib/api/auth";
import { tokenStore } from "./tokenStore";
import type { User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (data: {
    full_name: string;
    email: string;
    password: string;
    role?: "customer" | "seller";
  }) => Promise<User>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const qc = useQueryClient();

  useEffect(() => {
    let active = true;
    (async () => {
      if (!tokenStore.getAccess()) {
        setLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (active) setUser(me);
      } catch {
        tokenStore.clear();
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login: AuthContextValue["login"] = async (email, password) => {
    const res = await authApi.login({ email, password });
    tokenStore.set(res.access_token, res.refresh_token);
    setUser(res.user);
    qc.clear();
    return res.user;
  };

  const register: AuthContextValue["register"] = async (data) => {
    const res = await authApi.register(data);
    tokenStore.set(res.access_token, res.refresh_token);
    setUser(res.user);
    qc.clear();
    return res.user;
  };

  const logout = () => {
    // Notify the server while the access token is still available (the client
    // discards its tokens either way — JWTs are stateless).
    authApi.logout().catch(() => {});
    tokenStore.clear();
    setUser(null);
    qc.clear();
  };

  const refresh = async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      logout();
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
