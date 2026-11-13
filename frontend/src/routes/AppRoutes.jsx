
import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "../components/common/AppLayout";

function HomePage() {
  return (
    <div>
      <h1>AI City Management Platform</h1>
      <p>Welcome to the Citizen Portal</p>
    </div>
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/citizen"
          element={<Navigate to="/" replace />}
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
