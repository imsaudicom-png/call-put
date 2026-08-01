export default function ReasoningBox({ reasoning }: { reasoning: string[] }) {
  return (
    <div className="rounded-xl border border-panelBorder bg-panel p-5">
      <div className="text-sm text-muted mb-3 font-semibold">لماذا هذا التحليل؟</div>
      <ul className="space-y-2">
        {reasoning.map((r, i) => (
          <li key={i} className="text-sm leading-relaxed flex gap-2">
            <span className="text-accentGold shrink-0">•</span>
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
