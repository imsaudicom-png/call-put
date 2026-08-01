import { AnalysisResult } from "@/lib/types";

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-panelBorder/60 last:border-none">
      <span className="text-sm text-muted">{label}</span>
      <span className="font-num font-semibold" style={{ color }}>{value}</span>
    </div>
  );
}

function fmt(v: number | null | undefined) {
  if (v === null || v === undefined) return "—";
  return v.toFixed(4);
}
function fmtTime(t: number | null | undefined) {
  if (!t) return "—";
  return new Date(t * 1000).toLocaleString("ar-SA", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" });
}

export default function LevelsPanel({ result }: { result: AnalysisResult }) {
  const signalColor = result.signal === "CALL" ? "#089981" : result.signal === "PUT" ? "#f23645" : "#7d8494";
  const signalText = result.signal === "CALL" ? "▲ CALL" : result.signal === "PUT" ? "▼ PUT" : "انتظار";
  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-5">
      <div className="text-sm text-muted mb-2 font-semibold">الإشارة الحالية (إيشيموكو)</div>
      <Row label="الإشارة" value={signalText} color={signalColor} />
      <Row label="وقف الخسارة" value={fmt(result.stopLoss)} color="#f23645" />

      <div className="text-sm text-muted mt-4 mb-2 font-semibold">المستويات الرئيسية</div>
      <Row label="المقاومة" value={fmt(result.resistance)} color="#f23645" />
      <Row label="الدعم" value={fmt(result.support)} color="#089981" />
      <Row label="المنتصف السعري" value={fmt(result.midpoint)} color="#e8b84b" />
      <Row label="آخر قمة" value={`${fmt(result.lastPivotHigh?.price)} (${fmtTime(result.lastPivotHigh?.time)})`} />
      <Row label="آخر قاع" value={`${fmt(result.lastPivotLow?.price)} (${fmtTime(result.lastPivotLow?.time)})`} />

      <div className="text-sm text-muted mt-4 mb-2 font-semibold">أهداف الإيشيموكو (Tenkan / Kijun / السحابة)</div>
      <Row
        label="أهداف صاعدة"
        value={result.bullishTargets ? result.bullishTargets.map(fmt).join(" / ") : "لا يوجد حاليًا"}
        color="#089981"
      />
      <Row
        label="أهداف هابطة"
        value={result.bearishTargets ? result.bearishTargets.map(fmt).join(" / ") : "لا يوجد حاليًا"}
        color="#f23645"
      />
    </div>
  );
}
