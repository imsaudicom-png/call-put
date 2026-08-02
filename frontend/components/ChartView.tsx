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
      upColor: "#0a0d12", downColor: "#f23645",
      borderUpColor: "#089981", borderDownColor: "#f23645",
      wickUpColor: "#089981", wickDownColor: "#f23645",
      borderVisible: true,
    });
    candleSeries.setData(
      result.candles.map((c) => ({
        time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close,
      }))
    );

    const tenkanSeries = chart.addLineSeries({
      color: "#2962ff", lineWidth: 1, title: "Tenkan",
      priceLineVisible: false, lastValueVisible: false,
    });
    tenkanSeries.setData(result.ema50.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));

    const kijunSeries = chart.addLineSeries({
      color: "#e91e63", lineWidth: 1, title: "Kijun",
      priceLineVisible: false, lastValueVisible: false,
    });
    kijunSeries.setData(result.ema200.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));

    // سحابة الإيشيموكو — Span A (أخضر) / Span B (أحمر)، مزاحة للمستقبل زي الأصل بالضبط.
    // ملاحظة: التظليل الشفاف بين الخطين (fill) غير مدعوم بمكتبة الرسم الحالية، فعوضناه
    // بخطين ملوّنين متقطعين — يعطونك نفس معنى السحابة (تقاطع/انفصال الأخضر والأحمر)
    if (result.spanA.length) {
      const s = chart.addLineSeries({
        color: "rgba(38,166,154,0.9)", lineWidth: 1, lineStyle: LineStyle.Dotted, title: "Span A",
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.spanA.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }
    if (result.spanB.length) {
      const s = chart.addLineSeries({
        color: "rgba(239,83,80,0.9)", lineWidth: 1, lineStyle: LineStyle.Dotted, title: "Span B",
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.spanB.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    // VWAP
    if (result.vwapLine.length) {
      const s = chart.addLineSeries({
        color: "#ff9800", lineWidth: 1, title: "VWAP",
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.vwapLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    if (result.resistanceLine.length === 2) {
      const s = chart.addLineSeries({
        color: "#f23645", lineWidth: 2,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.resistanceLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }
    if (result.supportLine.length === 2) {
      const s = chart.addLineSeries({
        color: "#089981", lineWidth: 2,
        priceLineVisible: false, lastValueVisible: false,
      });
      s.setData(result.supportLine.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    }

    const addHLine = (value: number | null | undefined, color: string, title: string, dashed = true) => {
      if (value === null || value === undefined) return;
      candleSeries.createPriceLine({
        price: value, color, lineWidth: 1,
        lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
        axisLabelVisible: true, title,
      });
    };
    addHLine(result.resistance, "#f23645", "🟥 مقاومة رئيسية", false);
    addHLine(result.support, "#089981", "🟩 دعم رئيسي", false);
    addHLine(result.midpoint, "#e8b84b", "المنتصف");
    addHLine(result.target1, "#2962ff", "🎯 هدف 1 (Tenkan)");
    addHLine(result.target2, "#e91e63", "🎯 هدف 2 (Kijun)");
    addHLine(result.target3, "#9c27b0", "🎯 هدف الموجة 3");
    addHLine(result.stopLoss, "#ff3344", "🛑 وقف الخسارة");

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
