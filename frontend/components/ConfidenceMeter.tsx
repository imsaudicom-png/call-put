export default function ConfidenceMeter({ score }: { score: number }) {
  const color = score >= 70 ? "#089981" : score >= 45 ? "#e8b84b" : "#f23645";
  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-5">
      <div className="text-sm text-muted mb-2">نسبة نجاح الإشارة (Confidence)</div>
      <div className="flex items-center gap-4">
        <div className="text-3xl font-bold font-num" style={{ color }}>{score}%</div>
        <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
          <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: color }} />
        </div>
      </div>
    </div>
  );
}
