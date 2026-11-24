import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  AuthMembership,
  fetchMe,
  getStoredToken,
  login as apiLogin,
  logout as apiLogout,
  MeResponse,
  registerUser,
  setStoredToken,
} from "../lib/api";

const ACTIVE_TENANT_KEY = "lancast-active-tenant";

export function primaryPortalPath(me: MeResponse | null): string {
  if (!me) return "/";
  if (me.user.is_platform_admin && me.memberships.length === 0) {
    return "/admin";
  }
  const hasOrganizer = me.memberships.some(
    (m) => m.role === "organizer" || m.role === "tenant_admin"
  );
  if (hasOrganizer) return "/organizer";
  if (me.memberships.some((m) => m.role === "candidate")) return "/candidate";
  if (me.user.is_platform_admin) return "/admin";
  return "/";
}

interface AuthContextValue {
  token: string | null;
  me: MeResponse | null;
  loading: boolean;
  activeTenantId: string | null;
  activeMembership: AuthMembership | null;
  setActiveTenantId: (tenantId: string) => void;
  signIn: (email: string, password: string) => Promise<MeResponse>;
  registerFirstAdmin: (email: string, fullName: string, password: string) => Promise<MeResponse>;
  signOut: () => Promise<void>;
  refreshMe: () => Promise<MeResponse | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [me, setMe] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(getStoredToken()));
  const [activeTenantId, setActiveTenantIdState] = useState<string | null>(() =>
    window.localStorage.getItem(ACTIVE_TENANT_KEY)
  );

  const syncTenantSelection = useCallback((profile: MeResponse | null) => {
    if (!profile || profile.memberships.length === 0) {
      setActiveTenantIdState(null);
      window.localStorage.removeItem(ACTIVE_TENANT_KEY);
      return;
    }
    const stored = window.localStorage.getItem(ACTIVE_TENANT_KEY);
    const valid = profile.memberships.some((m) => m.tenant_id === stored);
    const chosen = valid && stored ? stored : profile.memberships[0].tenant_id;
    setActiveTenantIdState(chosen);
    window.localStorage.setItem(ACTIVE_TENANT_KEY, chosen);
  }, []);

  const refreshMe = useCallback(async (): Promise<MeResponse | null> => {
    const current = getStoredToken();
    if (!current) {
      setToken(null);
      setMe(null);
      syncTenantSelection(null);
      setLoading(false);
      return null;
    }
    try {
      const profile = await fetchMe(current);
      setToken(current);
      setMe(profile);
      syncTenantSelection(profile);
      return profile;
    } catch {
      setStoredToken(null);
      setToken(null);
      setMe(null);
      syncTenantSelection(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [syncTenantSelection]);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const setActiveTenantId = useCallback((tenantId: string) => {
    setActiveTenantIdState(tenantId);
    window.localStorage.setItem(ACTIVE_TENANT_KEY, tenantId);
  }, []);

  const signIn = useCallback(
    async (email: string, password: string): Promise<MeResponse> => {
      const res = await apiLogin(email.trim(), password);
      setStoredToken(res.access_token);
      setToken(res.access_token);
      const profile = await fetchMe(res.access_token);
      setMe(profile);
      syncTenantSelection(profile);
      return profile;
    },
    [syncTenantSelection]
  );

  const registerFirstAdmin = useCallback(
    async (email: string, fullName: string, password: string): Promise<MeResponse> => {
      await registerUser({ email: email.trim(), full_name: fullName.trim(), password });
      return signIn(email.trim(), password);
    },
    [signIn]
  );

  const signOut = useCallback(async () => {
    const current = getStoredToken();
    if (current) {
      await apiLogout(current);
    }
    setStoredToken(null);
    setToken(null);
    setMe(null);
    syncTenantSelection(null);
  }, [syncTenantSelection]);

  const activeMembership = useMemo(() => {
    if (!me || me.memberships.length === 0) return null;
    return me.memberships.find((m) => m.tenant_id === activeTenantId) ?? me.memberships[0];
  }, [me, activeTenantId]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      me,
      loading,
      activeTenantId: activeMembership?.tenant_id ?? activeTenantId,
      activeMembership,
      setActiveTenantId,
      signIn,
      registerFirstAdmin,
      signOut,
      refreshMe,
    }),
    [
      token,
      me,
      loading,
      activeMembership,
      activeTenantId,
      setActiveTenantId,
      signIn,
      registerFirstAdmin,
      signOut,
      refreshMe,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
