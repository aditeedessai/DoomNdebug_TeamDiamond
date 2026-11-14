import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

/**
 * Route protection wrapper enforcing authentication and role authorization.
 *
 * @param {object} props
 * @param {string[]} [props.allowedRoles] - Authorized roles (e.g. ['citizen'], ['official', 'worker'])
 * @param {boolean} [props.requireSafetyOfficer] - Whether designated safety officer status is strictly required
 * @param {React.ReactNode} [props.children] - Optional child elements (defaults to <Outlet />)
 */
export default function ProtectedRoute({
  allowedRoles = [],
  requireSafetyOfficer = false,
  children,
}) {
  const { user, token, loading, isAuthenticated, isSafetyOfficer } = useAuth();
  const location = useLocation();

  // Display unobtrusive loading state while session validation is in progress
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "#0d131a",
          color: "#94a3b8",
          fontFamily: "Inter, Arial, sans-serif",
          gap: "16px",
        }}
      >
        <div
          style={{
            width: "36px",
            height: "36px",
            border: "3px solid rgba(56, 189, 248, 0.2)",
            borderTopColor: "#38bdf8",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <span style={{ fontSize: "13px", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Verifying session...
        </span>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Not authenticated: redirect to appropriate login portal
  if (!token || !isAuthenticated) {
    const isOfficialTarget = location.pathname.startsWith("/official");
    const targetLogin = isOfficialTarget ? "/official-login" : "/citizen-login";
    return <Navigate to={targetLogin} state={{ from: location }} replace />;
  }

  // Role authorization check
  if (allowedRoles.length > 0 && (!user || !allowedRoles.includes(user.role))) {
    // Redirect authenticated user to their designated portal
    if (user.role === "official" || user.role === "worker") {
      return <Navigate to="/official/dashboard" replace />;
    }
    return <Navigate to="/citizen/dashboard" replace />;
  }

  // Specific safety officer authorization requirement
  if (requireSafetyOfficer && !isSafetyOfficer) {
    return <Navigate to="/official/dashboard" replace />;
  }

  return children ? children : <Outlet />;
}

