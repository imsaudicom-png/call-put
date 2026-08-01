"use client";
import { useEffect, useState } from "react";
import { fetchWatchlist } from "@/lib/api";
import { WatchlistEntry, Timeframe } from "@/lib/types";

const trendColor: Record<string, string> = {
  UP: "#089981", DOWN: "#f23645", FLAT: "#7d8494", UNKNOWN: "#3a3f4a",
};
const trendBg: Record<string, string> = {
  UP: "rgba(8,153,129,0.10)", DOWN: "rgba(242,54,69,0.10)",
  FLAT: "rgba(125,132,148,0.06)", UNKNOWN: "rgba(58,63,74,0.06)",
};

export default function WatchlistGrid({
  onSelect,
}: {
  onSelect: (symbol: string, timeframe: Timeframe) => void;
}) {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const res = await fetchWatchlist();
      setEntries(res.entries);
      setError(null);
    } catch (e: any) {
      setError(e.message || "تعذر تحميل قائمة المتابعة");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 60000); // تحديث كل دقيقة
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="mt-8 text-center text-muted text-sm">جارٍ تحميل قائمة المتابعة…</div>;
  }
  if (error) {
    return <div className="mt-8 text-center text-bear text-sm">{error}</div>;
  }

  return (
    <div className="mt-8">
      <div className="text-sm text-muted mb-3">
        قائمة متابعة سريعة — اضغط على أي رمز لعرض تحليله الكامل على فريم 5 دقائق
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
        {entries.map((e) => (
          <button
            key={e.symbol}
            onClick={() => onSelect(e.symbol, "5m")}
            className="rounded-lg border border-panelBorder px-3 py-2.5 text-left hover:brightness-125 transition"
            style={{ backgroundColor: trendBg[e.trend] }}
          >
            <div className="text-xs font-bold font-num">{e.symbol}</div>
            <div className="text-xs font-num mt-0.5" style={{ color: trendColor[e.trend] }}>
              {e.percentChange !== null
                ? `${e.percentChange > 0 ? "+" : ""}${e.percentChange.toFixed(2)}%`
                : "—"}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
