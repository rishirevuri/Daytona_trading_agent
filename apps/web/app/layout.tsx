import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "SignalOps - Stock Market Prediction Research Platform",
  description:
    "Reproducible backtesting platform for quantitative trading strategies with isolated sandbox execution.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <div className="min-h-screen bg-background">
          <header className="border-b border-border">
            <div className="container mx-auto px-4 py-4">
              <nav className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <a href="/" className="text-xl font-bold">
                    SignalOps
                  </a>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <a
                      href="/"
                      className="hover:text-foreground transition-colors"
                    >
                      Dashboard
                    </a>
                    <a
                      href="/earnings"
                      className="hover:text-foreground transition-colors"
                    >
                      Earnings Lens
                    </a>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                    Paper Trading Only
                  </span>
                </div>
              </nav>
            </div>
          </header>
          <main className="container mx-auto px-4 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
