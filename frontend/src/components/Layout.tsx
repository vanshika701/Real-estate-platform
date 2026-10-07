import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

interface NavItem {
  to: string;
  label: string;
}

function navFor(role: "buyer" | "agent" | null): NavItem[] {
  const browse = { to: "/listings", label: "Browse homes" };
  if (role === "agent") {
    return [
      browse,
      { to: "/agent/dashboard", label: "Dashboard" },
      { to: "/agent/listings", label: "My listings" },
    ];
  }
  if (role === "buyer") return [browse, { to: "/my-bookings", label: "My bookings" }];
  return [browse];
}

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
  }`;

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = navFor(user?.role ?? null);

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    navigate("/");
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-[1100] border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
            <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white">
              P
            </span>
            PropVisit
          </Link>

          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            {user ? (
              <>
                <span className="text-sm text-slate-600">
                  {user.full_name}
                  <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium capitalize text-slate-600">
                    {user.role}
                  </span>
                </span>
                <button type="button" onClick={handleLogout} className="btn-secondary py-2">
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-secondary py-2">
                  Log in
                </Link>
                <Link to="/signup" className="btn-primary py-2">
                  Sign up
                </Link>
              </>
            )}
          </div>

          <button
            type="button"
            className="rounded-md p-2 text-slate-700 hover:bg-slate-100 md:hidden"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth={2}>
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>

        {menuOpen && (
          <div id="mobile-menu" className="border-t border-slate-200 px-4 py-3 md:hidden">
            <nav aria-label="Mobile" className="flex flex-col gap-1">
              {items.map((item) => (
                <NavLink key={item.to} to={item.to} className={linkClass} onClick={() => setMenuOpen(false)}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="mt-3 flex flex-col gap-2 border-t border-slate-200 pt-3">
              {user ? (
                <>
                  <p className="px-1 text-sm text-slate-600">
                    Signed in as <strong>{user.full_name}</strong> ({user.role})
                  </p>
                  <button type="button" onClick={handleLogout} className="btn-secondary">
                    Log out
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="btn-secondary" onClick={() => setMenuOpen(false)}>
                    Log in
                  </Link>
                  <Link to="/signup" className="btn-primary" onClick={() => setMenuOpen(false)}>
                    Sign up
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 text-sm text-slate-500 sm:px-6">
          PropVisit · A portfolio project · Map data © OpenStreetMap contributors
        </div>
      </footer>
    </div>
  );
}
