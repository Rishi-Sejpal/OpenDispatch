import { Navigate, Route, Routes, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, getAccessToken } from './lib/api';
import { useTheme } from './lib/theme';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import FlightPlans from './pages/FlightPlans';
import NewFlightPlan from './pages/NewFlightPlan';
import FlightPlanDetail from './pages/FlightPlanDetail';
import Airports from './pages/Airports';
import RoutesPage from './pages/Routes';
import Aircraft from './pages/Aircraft';
import Documents from './pages/Documents';
import Settings from './pages/Settings';
import { cn } from './lib/cn';

function NavItem({ to, label }: { to: string; label: string }) {
  const loc = useLocation();
  const active = loc.pathname === to || (to !== '/' && loc.pathname.startsWith(to));
  return (
    <Link
      to={to}
      className={cn(
        'block px-3 py-1.5 rounded-md text-sm transition',
        active ? 'bg-accent/15 text-accent border-l-2 border-accent' : 'text-slate-300 hover:bg-bg-card hover:text-white'
      )}
    >
      {label}
    </Link>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  const [, toggleTheme] = useTheme();
  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get('/auth/me')).data,
    enabled: !!getAccessToken(),
    retry: false,
  });

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-bg-panel border-r border-bg-line flex flex-col">
        <div className="p-4 border-b border-bg-line">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-accent/20 border border-accent/40 flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-accent rounded-sm rotate-45" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-wide">OpenDispatch</div>
              <div className="text-[10px] text-slate-500 uppercase">Flight planning</div>
            </div>
          </Link>
        </div>
        <nav className="p-2 space-y-0.5 flex-1">
          <NavItem to="/" label="Dashboard" />
          <NavItem to="/flight-plans/new" label="New Flight Plan" />
          <NavItem to="/flight-plans" label="Flight Plans" />
          <NavItem to="/airports" label="Airports" />
          <NavItem to="/routes" label="Routes" />
          <NavItem to="/aircraft" label="Aircraft" />
          <NavItem to="/documents" label="Documents" />
          <NavItem to="/settings" label="Settings" />
        </nav>
        <div className="p-3 border-t border-bg-line text-xs text-slate-400">
          {me.data && (
            <div className="mb-2">
              <div className="text-slate-200 font-medium truncate">{me.data.full_name}</div>
              <div className="truncate text-[10px]">{me.data.email}</div>
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={toggleTheme} className="btn-ghost flex-1 text-[10px]">
              Theme
            </button>
            <Link to="/login" className="btn-ghost flex-1 text-[10px]" onClick={() => localStorage.clear()}>
              Sign out
            </Link>
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

function ProtectedShell({ children }: { children: React.ReactNode }) {
  if (!getAccessToken()) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<ProtectedShell><Dashboard /></ProtectedShell>} />
      <Route path="/flight-plans" element={<ProtectedShell><FlightPlans /></ProtectedShell>} />
      <Route path="/flight-plans/new" element={<ProtectedShell><NewFlightPlan /></ProtectedShell>} />
      <Route path="/flight-plans/:id" element={<ProtectedShell><FlightPlanDetail /></ProtectedShell>} />
      <Route path="/airports" element={<ProtectedShell><Airports /></ProtectedShell>} />
      <Route path="/routes" element={<ProtectedShell><RoutesPage /></ProtectedShell>} />
      <Route path="/aircraft" element={<ProtectedShell><Aircraft /></ProtectedShell>} />
      <Route path="/documents" element={<ProtectedShell><Documents /></ProtectedShell>} />
      <Route path="/settings" element={<ProtectedShell><Settings /></ProtectedShell>} />
    </Routes>
  );
}
