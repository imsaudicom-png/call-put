export type Candle = { time: number; open: number; high: number; low: number; close: number; volume: number };
export type LinePoint = { time: number; value: number };
export type PivotPoint = { price: number; time: number };
export type HiddenSignal = {
  type: "HIDDEN_BULL" | "HIDDEN_BEAR";
  price: number; time: number; target: number; stop: number; midPrice: number;
};

export type AnalysisResult = {
  symbol: string;
  timeframe: string;
  generatedAt: number;
  candles: Candle[];
  ema50: LinePoint[];
  ema200: LinePoint[];
  trend: "BULLISH" | "BEARISH" | "NEUTRAL";
  trendStrength: "STRONG" | "MODERATE" | "WEAK";
  structureState: number;
  resistanceLine: LinePoint[];
  supportLine: LinePoint[];
  support: number | null;
  resistance: number | null;
  midpoint: number | null;
  lastPivotHigh: PivotPoint | null;
  lastPivotLow: PivotPoint | null;
  bullishTargets: number[] | null;
  bearishTargets: number[] | null;
  hiddenSignal: HiddenSignal | null;
  confidenceScore: number;
  reasoning: string[];
};

export type MTFEntry = { timeframe: string; state: number; label: string };
export type MTFRadarResult = { symbol: string; generatedAt: number; entries: MTFEntry[] };

export const TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "45m", "1h", "75m", "2h", "4h", "1D"] as const;
export type Timeframe = (typeof TIMEFRAMES)[number];
