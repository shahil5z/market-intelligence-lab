// Small fetch helpers. The backend URL comes from NEXT_PUBLIC_API_URL (see .env.example).
"use client";

import { useEffect, useState } from "react";

// Only fall back to the local API during `next dev`; a production build must be given NEXT_PUBLIC_API_URL.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

/** Error shown to users: a short message, never a stack trace. `status` 0 means the API was unreachable. */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  if (!API_URL) throw new ApiError("The API address is not configured", 0);
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new ApiError("The analysis API could not be reached", 0);
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    throw new ApiError(typeof detail === "string" ? detail : `Request failed (${res.status})`, res.status);
  }
  return data as T;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Row = Record<string, any>;

export async function getJson<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(path, API_URL || "http://invalid.local");
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v) url.searchParams.set(k, v);
  });
  return request<T>(url.toString());
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(new URL(path, API_URL || "http://invalid.local").toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** Fetch `path` whenever the params change. Returns data, error and loading state. */
export function useApi<T>(path: string, params?: Record<string, string | undefined>) {
  const key = JSON.stringify(params ?? {});
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({
    data: null,
    error: null,
    loading: true,
  });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    getJson<T>(path, JSON.parse(key))
      .then((data) => active && setState({ data, error: null, loading: false }))
      .catch((e: Error) => active && setState({ data: null, error: e.message, loading: false }));
    return () => {
      active = false;
    };
  }, [path, key, attempt]);
  return { ...state, reload: () => setAttempt((n) => n + 1) };
}

/** User-facing message for a failed action: input problems (4xx) are shown as-is, everything else is generic. */
export function friendlyError(e: unknown, what: string): string {
  if (e instanceof ApiError && e.status >= 400 && e.status < 500) return e.message;
  return `Unable to ${what}. Please try again.`;
}
