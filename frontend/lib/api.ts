import { AnalysisResult, MTFRadarResult, WatchlistResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `فشل الطلب (${res.status})`);
  }
  return res.json();
}

export function fetchAnalysis(symbol: string, timeframe: string): Promise<AnalysisResult> {
  const params = new URLSearchParams({ symbol, timeframe });
  return getJSON(`${API_BASE}/api/analyze?${params.toString()}`);
}

export function fetchMTFRadar(symbol: string): Promise<MTFRadarResult> {
  const params = new URLSearchParams({ symbol });
  return getJSON(`${API_BASE}/api/mtf-radar?${params.toString()}`);
}

export function fetchWatchlist(): Promise<WatchlistResult> {
  return getJSON(`${API_BASE}/api/watchlist`);
}

export function searchSymbols(query: string): Promise<{ symbol: string; name: string }[]> {
  const params = new URLSearchParams({ query });
  return getJSON(`${API_BASE}/api/search?${params.toString()}`);
}
