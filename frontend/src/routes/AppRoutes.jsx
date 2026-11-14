import { Routes, Route, Navigate } from "react-router-dom";

import Home from "../pages/citizen/home/home";
import Login from "../pages/citizen/Login";

import AppLayout from "../components/common/AppLayout";
import ProtectedRoute from "../components/common/ProtectedRoute";

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
  OfficialProjectsFeedback,
  OfficialSafetyRegister
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

      {/* PROTECTED CITIZEN PORTAL (Requires role='citizen') */}
      <Route
        path="/citizen"
        element={
          <ProtectedRoute allowedRoles={["citizen"]}>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="report" element={<Report />} />
        <Route path="complaints" element={<Complaints />} />
        <Route path="projects" element={<Projects />} />
        <Route path="map" element={<CityMap />} />
        <Route path="safety" element={<Safety />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* PROTECTED OFFICIAL & WORKER PORTAL */}
      <Route
        path="/official"
        element={
          <ProtectedRoute allowedRoles={["official", "worker"]}>
            <OfficialLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<OfficialDashboard />} />
        <Route
          path="complaints"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialComplaints />
            </ProtectedRoute>
          }
        />
        <Route
          path="departments"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialDepartments />
            </ProtectedRoute>
          }
        />
        <Route
          path="officials"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialDirectory />
            </ProtectedRoute>
          }
        />
        <Route
          path="projects"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialProjectsFeedback />
            </ProtectedRoute>
          }
        />
        <Route
          path="analytics"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialAnalytics />
            </ProtectedRoute>
          }
        />
        <Route
          path="alerts"
          element={
            <ProtectedRoute allowedRoles={["official"]}>
              <OfficialAlerts />
            </ProtectedRoute>
          }
        />
        <Route
          path="safety"
          element={
            <ProtectedRoute allowedRoles={["official"]} requireSafetyOfficer={true}>
              <OfficialSafetyRegister />
            </ProtectedRoute>
          }
        />
        <Route path="settings" element={<OfficialSettings />} />
      </Route>

      {/* FALLBACK */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
