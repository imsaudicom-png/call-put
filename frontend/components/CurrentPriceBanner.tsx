"use client";
import { AnalysisResult } from "@/lib/types";

export default function CurrentPriceBanner({ result }: { result: AnalysisResult }) {
  const candles = result.candles;
  if (!candles.length) return null;

  const last = candles[candles.length - 1];
  const prev = candles.length > 1 ? candles[candles.length - 2] : last;
  const change = last.close - prev.close;
  const changePct = prev.close !== 0 ? (change / prev.close) * 100 : 0;
  const isUp = change >= 0;

  const updatedTime = new Date(last.time * 1000).toLocaleTimeString("ar-SA", {
    hour: "2-digit", minute: "2-digit",
  });

  const targets = result.trend === "BULLISH" ? result.bullishTargets : result.bearishTargets;
  const targetColor = result.trend === "BULLISH" ? "#089981" : "#f23645";
  const targetLabel = result.trend === "BULLISH" ? "هدف صاعد" : "هدف هابط";

  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-xs text-muted mb-1">{result.symbol} · {result.timeframe}</div>
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-white">
              {last.close.toLocaleString("en-US", { maximumFractionDigits: 4 })}
            </span>
            <span
              className="text-sm font-semibold"
              style={{ color: isUp ? "#089981" : "#f23645" }}
            >
              {isUp ? "▲" : "▼"} {Math.abs(change).toLocaleString("en-US", { maximumFractionDigits: 4 })}
              {" "}({isUp ? "+" : ""}{changePct.toFixed(2)}%)
            </span>
          </div>
        </div>
        <div className="text-xs text-muted">آخر تحديث: {updatedTime}</div>
      </div>

      {targets && targets.length > 0 && (
        <div className="flex items-center gap-4 pt-2 border-t border-panelBorder/60">
          {targets.map((t, i) => (
            <div key={i} className="flex items-baseline gap-1.5">
              <span className="text-xs text-muted">{targetLabel} {i + 1}</span>
              <span className="text-sm font-semibold font-num" style={{ color: targetColor }}>
                {t.toLocaleString("en-US", { maximumFractionDigits: 4 })}
              </span>
            </div>
          ))}
        </div>
      )}

      {result.advice && (
        <div className="text-xs text-muted">{result.advice}</div>
      )}
    </div>
  );
}
