
import { Outlet } from "react-router-dom";

export default function AppLayout() {
  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="app-brand">
          <h2>CityNex</h2>
          <span>Smart City Management</span>
        </div>
      </header>

      <main className="app-content">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>CityNex © 2026 | AI City Management Platform</p>
      </footer>
    </div>
  );
}
