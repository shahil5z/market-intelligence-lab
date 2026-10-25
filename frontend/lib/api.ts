// Small fetch helpers. The backend URL comes from NEXT_PUBLIC_API_URL (see .env.example).
"use client";

import { useEffect, useState } from "react";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Row = Record<string, any>;

export async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, API_URL);
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v) url.searchParams.set(k, v);
  });
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail ?? `Request failed (${res.status})`);
  return res.json();
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(new URL(path, API_URL).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data as T;
}

/** Fetch `path` whenever the params change. Returns data, error and loading state. */
export function useApi<T>(path: string, params?: Record<string, string | undefined>) {
  const key = JSON.stringify(params ?? {});
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({
    data: null,
    error: null,
    loading: true,
  });
  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    getJson<T>(path, JSON.parse(key))
      .then((data) => active && setState({ data, error: null, loading: false }))
      .catch((e: Error) => active && setState({ data: null, error: e.message, loading: false }));
    return () => {
      active = false;
    };
  }, [path, key]);
  return state;
}
