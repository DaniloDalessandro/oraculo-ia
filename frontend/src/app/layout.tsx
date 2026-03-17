import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oraculo IA",
  description: "Plataforma de chatbot corporativo",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#0f0f0f] text-white antialiased">
        {children}
      </body>
    </html>
  );
}
