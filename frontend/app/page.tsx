"use client";
import { useState } from "react";
import SearchBar from "@/components/SearchBar";
import TrendBadge from "@/components/TrendBadge";
import ConfidenceMeter from "@/components/ConfidenceMeter";
import LevelsPanel from "@/components/LevelsPanel";
import ReasoningBox from "@/components/ReasoningBox";
import MTFRadar from "@/components/MTFRadar";
import ChartView from "@/components/ChartView";
import { fetchAnalysis, fetchMTFRadar } from "@/lib/api";
import { AnalysisResult, MTFEntry, Timeframe } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [mtf, setMtf] = useState<MTFEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [mtfLoading, setMtfLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(symbolRaw: string, timeframe: Timeframe) {
    const symbol = symbolRaw.trim().toUpperCase();
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAnalysis(symbol, timeframe);
      setResult(data);
    } catch (e: any) {
      setError(e.message || "حدث خطأ أثناء التحليل");
      setResult(null);
    } finally {
      setLoading(false);
    }

    setMtfLoading(true);
    try {
      const radar = await fetchMTFRadar(symbol);
      setMtf(radar.entries);
    } catch {
      setMtf([]);
    } finally {
      setMtfLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg px-4 py-6 sm:px-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-accentGold">بوصلة السوق</h1>
          <p className="text-xs text-muted">تحليل فوري بمنطق هيكلة السعر والمثلث الديناميكي</p>
        </div>
      </header>

      <SearchBar onAnalyze={handleAnalyze} loading={loading} />

      {error && (
        <div className="mt-4 rounded-lg border border-bear/40 bg-bear/10 text-bear text-sm px-4 py-3">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <ChartView result={result} />
          </div>
          <div className="space-y-4">
            <TrendBadge result={result} />
            <ConfidenceMeter score={result.confidenceScore} />
            <LevelsPanel result={result} />
            <ReasoningBox reasoning={result.reasoning} />
            <MTFRadar entries={mtf} loading={mtfLoading} />
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <div className="mt-16 text-center text-muted text-sm">
          اكتب رمز أي سهم أو أصل واختر الفريم الزمني، ثم اضغط "تحليل" لعرض النتائج.
        </div>
      )}
    </main>
  );
}
