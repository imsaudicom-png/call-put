"use client";
import { useEffect, useRef } from "react";
import {
  createChart, ColorType, IChartApi, ISeriesApi, LineStyle, UTCTimestamp,
} from "lightweight-charts";
import { AnalysisResult } from "@/lib/types";

export default function ChartView({ result }: { result: AnalysisResult }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: "#0a0d12" }, textColor: "#7d8494" },
      grid: { vertLines: { color: "#151a22" }, horzLines: { color: "#151a22" } },
      width: containerRef.current.clientWidth,
      height: 480,
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#1f2530" },
      rightPriceScale: { borderColor: "#1f2530" },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#089981", downColor: "#f23645",
      borderUpColor: "#089981", borderDownColor: "#f23645",
      wickUpColor: "#089981", wickDownColor: "#f23645",
    });
    candleSeries.setData(
      result.candles.map((c) => ({
        time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close,
      }))
    );

    const tenkanSeries = chart.addLineSeries({ color: "#2962ff", lineWidth: 1, title: "Tenkan" });
    tenkanSeries.setData(result.ema50.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));

    const kijunSeries = chart.addLineSeries({ color: "#e91e63", lineWidth: 1, title: "Kijun" });
    kijunSeries.setData(result.ema200.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));

    if (result.resistanceLine.length === 2) {
      const s = chart.addLineSeries({ color: "#f23645", lineWidth: 2 });
      s.setData(result.resistanceLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }
    if (result.supportLine.length === 2) {
      const s = chart.addLineSeries({ color: "#089981", lineWidth: 2 });
      s.setData(result.supportLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    const addHLine = (value: number | null, color: string, dashed = true) => {
      if (value === null) return;
      candleSeries.createPriceLine({
        price: value, color, lineWidth: 1,
        lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
        axisLabelVisible: true,
      });
    };
    addHLine(result.midpoint, "#e8b84b");
    result.bullishTargets?.forEach((t, i) => addHLine(t, "#089981", i === 0));
    result.bearishTargets?.forEach((t, i) => addHLine(t, "#f23645", i === 0));
    if (result.hiddenSignal) {
      addHLine(result.hiddenSignal.target, "#00ff88", true);
      addHLine(result.hiddenSignal.stop, "#ff3344", true);
    }

    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
    };
  }, [result]);

  return <div ref={containerRef} className="rounded-xl overflow-hidden border border-panelBorder" />;
}
