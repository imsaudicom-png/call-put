import { MTFEntry } from "@/lib/types";

const stateColor: Record<number, string> = { 1: "#00ff88", "-1": "#ff3344" as any, 0: "#e8b84b" };

export default function MTFRadar({ entries, loading }: { entries: MTFEntry[]; loading: boolean }) {
  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-5">
      <div className="text-sm text-muted mb-3 font-semibold">📡 رادار هيكلة الفريمات</div>
      {loading ? (
        <div className="text-sm text-muted">جارٍ تحميل الفريمات…</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {entries.map((e) => (
            <div key={e.timeframe} className="rounded-lg bg-white/5 px-3 py-2 flex items-center justify-between">
              <span className="text-xs text-muted font-num">{e.timeframe}</span>
              <span className="text-xs font-semibold" style={{ color: stateColor[e.state] }}>{e.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
