import type { Metadata } from "next";
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";
import "@/app/globals.css";
import { ChatConsoleProvider } from "@/components/chat/ChatConsoleContext";
import { Sidebar } from "@/components/chat/Sidebar";
import { Header } from "@/components/chat/Header";
import { AnalyticsPanel } from "@/components/chat/AnalyticsPanel";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "Developer AI Chat Console",
  description: "MVP de consola de chat de IA conectada a Groq",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} min-h-screen bg-surface font-[var(--font-space-grotesk)] text-on-surface`}
      >
        <ChatConsoleProvider>
          <div className="mx-auto grid max-w-[1700px] gap-4 p-4 lg:grid-cols-[18rem_minmax(0,1fr)_20rem]">
            <Sidebar />

            <div>
              <Header />
              {children}
            </div>

            <div className="hidden lg:block">
              <AnalyticsPanel />
            </div>
          </div>
        </ChatConsoleProvider>
      </body>
    </html>
  );
}
