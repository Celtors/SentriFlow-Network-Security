export const sessionToken = () => {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const token = fragment.get("token");
  if (token) {
    sessionStorage.setItem("sentriflow-token", token);
    fragment.delete("token");
    history.replaceState(
      null,
      "",
      location.pathname +
        location.search +
        (fragment.size ? `#${fragment}` : ""),
    );
  }
  return sessionStorage.getItem("sentriflow-token") || "";
};

export const getSessionToken = sessionToken;
export function setSessionToken(token: string) {
  if (token) sessionStorage.setItem("sentriflow-token", token);
  else sessionStorage.removeItem("sentriflow-token");
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (!path.startsWith("/") || path.startsWith("//"))
    throw new Error("Use a local API path");
  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${sessionToken()}`);
  if (init?.body) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: "omit",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${response.status})`,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const apiRequest = api;
