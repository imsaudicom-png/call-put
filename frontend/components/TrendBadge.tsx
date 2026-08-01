import { AnalysisResult } from "@/lib/types";

const strengthLabelAr: Record<string, string> = {
  STRONG: "قوي", MODERATE: "متوسط", WEAK: "ضعيف",
};

export default function TrendBadge({ result }: { result: AnalysisResult }) {
  const isBull = result.trend === "BULLISH";
  const isBear = result.trend === "BEARISH";

  const color = isBull ? "text-bull border-bull/40 bg-bull/10" : isBear ? "text-bear border-bear/40 bg-bear/10" : "text-muted border-panelBorder bg-white/5";
  const icon = isBull ? "▲" : isBear ? "▼" : "◆";
  const label = isBull ? "صاعد — Call" : isBear ? "هابط — Put" : "محايد";

  return (
    <div className={`rounded-xl border ${color} p-5 flex items-center justify-between`}>
      <div>
        <div className="text-sm text-muted mb-1">الاتجاه الحالي</div>
        <div className="text-2xl font-bold flex items-center gap-2">
          <span>{icon}</span>
          <span>{label}</span>
        </div>
      </div>
      <div className="text-left">
        <div className="text-sm text-muted mb-1">قوة الاتجاه</div>
        <div className="text-lg font-semibold font-num">{strengthLabelAr[result.trendStrength]}</div>
      </div>
    </div>
  );
}
