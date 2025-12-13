import { Link, useLocation } from 'react-router-dom';
import { Terminal, Server, Home } from 'lucide-react';

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Fixed Header with Navigation */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-slate-900/80 backdrop-blur-sm border-b border-purple-500/20">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Navigation Menu */}
            <div className="flex items-center gap-6">
              <Link
                to="/"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                  isActive('/')
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                    : 'text-gray-300 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Terminal className="w-5 h-5" />
                <span className="font-medium">SSH Terminal</span>
              </Link>

              <Link
                to="/config-switch"
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                  isActive('/config-switch')
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/50'
                    : 'text-gray-300 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Server className="w-5 h-5" />
                <span className="font-medium">ConfigSwitch</span>
              </Link>
            </div>

            {/* Home Button */}
            <a
              href="/"
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors duration-200 shadow-lg hover:shadow-purple-500/50"
            >
              <Home className="w-5 h-5" />
              <span className="font-medium">Home</span>
            </a>
          </div>
        </div>
      </div>

      {/* Main Content with padding for fixed header */}
      <div className="pt-16">
        {children}
      </div>
    </div>
  );
}
