
import { Routes, Route, Navigate } from "react-router-dom";

import Home from "../pages/citizen/home/home";
import Login from "../pages/citizen/Login";

import AppLayout from "../components/common/AppLayout";

import {
  Register,
  Dashboard,
  Report,
  Complaints,
  Projects,
  CityMap,
  Safety,
  SettingsPage
} from "../pages/citizen/portal/CitizenPages";

import {
  OfficialLayout,
  OfficialDashboard,
  OfficialComplaints,
  OfficialDepartments,
  OfficialDirectory,
  OfficialAnalytics,
  OfficialAlerts,
  OfficialSettings,
  OfficialProjectsFeedback
} from "../pages/official/OfficialPages";

export default function AppRoutes() {
  return (
    <Routes>
      {/* PUBLIC WEBSITE */}
      <Route path="/" element={<Home />} />

      {/* LOGIN */}
      <Route path="/login" element={<Login />} />
      <Route path="/citizen-login" element={<Login />} />
      <Route path="/official-login" element={<Login />} />

      {/* CITIZEN REGISTRATION */}
      <Route path="/register" element={<Register />} />

      {/* CITIZEN PORTAL */}
      <Route path="/citizen" element={<AppLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="report" element={<Report />} />
        <Route path="complaints" element={<Complaints />} />
        <Route path="projects" element={<Projects />} />
        <Route path="map" element={<CityMap />} />
        <Route path="safety" element={<Safety />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* OFFICIAL PORTAL */}
      <Route path="/official" element={<OfficialLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<OfficialDashboard />} />
        <Route path="complaints" element={<OfficialComplaints />} />
        <Route path="departments" element={<OfficialDepartments />} />
        <Route path="officials" element={<OfficialDirectory />} />
        <Route path="projects" element={<OfficialProjectsFeedback />} />
        <Route path="analytics" element={<OfficialAnalytics />} />
        <Route path="alerts" element={<OfficialAlerts />} />
        <Route path="settings" element={<OfficialSettings />} />
      </Route>

      {/* FALLBACK */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
