const ACCESS_KEY = "shopsphere.access";
const REFRESH_KEY = "shopsphere.refresh";

function safe<T>(fn: () => T, fallback: T): T {
  try {
    if (typeof window === "undefined") return fallback;
    return fn();
  } catch {
    return fallback;
  }
}

export const tokenStore = {
  getAccess: () => safe(() => localStorage.getItem(ACCESS_KEY), null),
  getRefresh: () => safe(() => localStorage.getItem(REFRESH_KEY), null),
  setAccess: (t: string) => safe(() => localStorage.setItem(ACCESS_KEY, t), undefined),
  setRefresh: (t: string) => safe(() => localStorage.setItem(REFRESH_KEY, t), undefined),
  set: (access: string, refresh: string) =>
    safe(() => {
      localStorage.setItem(ACCESS_KEY, access);
      localStorage.setItem(REFRESH_KEY, refresh);
    }, undefined),
  clear: () =>
    safe(() => {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }, undefined),
};
