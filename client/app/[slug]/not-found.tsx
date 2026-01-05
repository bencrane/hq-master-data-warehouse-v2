import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-7xl font-bold text-white mb-2">404</h1>
        <p className="text-slate-400 text-lg mb-8">Dashboard not found</p>
        <p className="text-slate-500 text-sm">
          Check the URL or contact your account manager.
        </p>
      </div>
    </div>
  );
}

