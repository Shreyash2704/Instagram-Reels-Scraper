import { useState } from "react";
import { FindMediaPage } from "./pages/FindMediaPage";
import { HistoryPage } from "./pages/HistoryPage";

type AppTab = "find" | "history";

export default function App() {
  const [tab, setTab] = useState<AppTab>("find");

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/95 px-4 py-3 shadow-sm backdrop-blur-sm">
        <nav
          className="mx-auto flex max-w-6xl justify-center gap-1 rounded-xl bg-slate-100 p-1 sm:justify-start"
          aria-label="Main"
        >
          <button
            type="button"
            onClick={() => setTab("find")}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${
              tab === "find"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Find media
          </button>
          <button
            type="button"
            onClick={() => setTab("history")}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${
              tab === "history"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            History
          </button>
        </nav>
      </header>
      {tab === "find" ? <FindMediaPage /> : <HistoryPage />}
    </div>
  );
}
