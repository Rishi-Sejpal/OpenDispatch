import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from './lib/api';
import { useTheme } from './lib/theme';
import { useSupabaseSession } from './lib/useSupabaseSession';
import { cn } from './lib/cn';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const FlightPlans = lazy(() => import('./pages/FlightPlans'));
const NewFlightPlan = lazy(() => import('./pages/NewFlightPlan'));
const FlightPlanDetail = lazy(() => import('./pages/FlightPlanDetail'));
const Airports = lazy(() => import('./pages/Airports'));
const RoutesPage = lazy(() => import('./pages/Routes'));
const Aircraft = lazy(() => import('./pages/Aircraft'));
const Documents = lazy(() => import('./pages/Documents'));
const Settings = lazy(() => import('./pages/Settings'));

const LoadingPage = () => (
  <div className="min-h-screen flex items-center justify-center bg-bg-base text-slate-400">
    Loading…
  </div>
);

function Page({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingPage />}>{children}</Suspense>;
}

function NavItem({ to, label }: { to: string; label: string }) {
  const loc = useLocation();
  const active = loc.pathname === to || (to !== '/' && loc.pathname.startsWith(to));
  return (
    <Link
      to={to}
      className={cn(
        'block px-3 py-1.5 rounded-md text-sm transition',
        active
          ? 'bg-accent/15 text-accent border-l-2 border-accent'
          : 'text-slate-300 hover:bg-bg-card hover:text-white',
      )}
    >
      {label}
    </Link>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  const [, toggleTheme] = useTheme();
  const { hasToken } = useSupabaseSession();
  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get('/auth/me')).data,
    enabled: hasToken,
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
            <Link
              to="/login"
              className="btn-ghost flex-1 text-[10px]"
              onClick={() => localStorage.clear()}
            >
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
  const { hasToken, loading } = useSupabaseSession();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-base text-slate-400">
        Loading…
      </div>
    );
  }
  if (!hasToken) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <Page>
            <Login />
          </Page>
        }
      />
      <Route
        path="/register"
        element={
          <Page>
            <Register />
          </Page>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedShell>
            <Page>
              <Dashboard />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/flight-plans"
        element={
          <ProtectedShell>
            <Page>
              <FlightPlans />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/flight-plans/new"
        element={
          <ProtectedShell>
            <Page>
              <NewFlightPlan />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/flight-plans/:id"
        element={
          <ProtectedShell>
            <Page>
              <FlightPlanDetail />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/airports"
        element={
          <ProtectedShell>
            <Page>
              <Airports />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/routes"
        element={
          <ProtectedShell>
            <Page>
              <RoutesPage />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/aircraft"
        element={
          <ProtectedShell>
            <Page>
              <Aircraft />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedShell>
            <Page>
              <Documents />
            </Page>
          </ProtectedShell>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedShell>
            <Page>
              <Settings />
            </Page>
          </ProtectedShell>
        }
      />
    </Routes>
  );
}
