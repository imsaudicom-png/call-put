import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "بوصلة السوق — تحليل فوري بمنطق هيكلة السعر",
  description: "منصة تحليل تعتمد على منطق مؤشر بوصلة المثلث الذهبية: اتجاه، دعم، مقاومة، وأهداف سعرية فورية.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
