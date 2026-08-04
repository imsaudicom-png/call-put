"use client";
import { useState } from "react";
import { TIMEFRAMES, Timeframe } from "@/lib/types";

export default function SearchBar({
  onAnalyze, loading,
}: {
  onAnalyze: (symbol: string, timeframe: Timeframe) => void;
  loading: boolean;
}) {
  const [symbol, setSymbol] = useState("SPY");
  const [timeframe, setTimeframe] = useState<Timeframe>("5m");

  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-4 flex flex-col sm:flex-row gap-3">
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onAnalyze(symbol, timeframe)}
        placeholder="اكتب رمز السهم أو الأصل: TSLA, AAPL, NVDA, BTC/USD, EUR/USD"
        className="flex-1 bg-black/30 border border-panelBorder rounded-lg px-4 py-2.5 text-sm font-num placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-accentGold/50"
      />
      <select
        value={timeframe}
        onChange={(e) => setTimeframe(e.target.value as Timeframe)}
        className="bg-black/30 border border-panelBorder rounded-lg px-3 py-2.5 text-sm font-num focus:outline-none focus:ring-2 focus:ring-accentGold/50"
      >
        {TIMEFRAMES.map((tf) => (
          <option key={tf} value={tf}>{tf}</option>
        ))}
      </select>
      <button
        onClick={() => onAnalyze(symbol, timeframe)}
        disabled={loading || !symbol.trim()}
        className="bg-accentGold text-black font-semibold rounded-lg px-6 py-2.5 text-sm disabled:opacity-50 hover:brightness-110 transition"
      >
        {loading ? "جارٍ التحليل…" : "تحليل"}
      </button>
    </div>
  );
}
