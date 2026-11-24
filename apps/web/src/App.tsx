import { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, primaryPortalPath, useAuth } from "./hooks/useAuth";
import { AdminPage } from "./pages/AdminPage";
import { AssessmentDetail } from "./pages/AssessmentDetail";
import { CandidateHome } from "./pages/CandidateHome";
import { ExamRunnerPage } from "./pages/ExamRunnerPage";
import { LandingPage } from "./pages/LandingPage";
import { OrganizerDashboard } from "./pages/OrganizerDashboard";
import { ResultsGradingPage } from "./pages/ResultsGradingPage";
import { TenantMembersPage } from "./pages/TenantMembersPage";

function LoadingScreen() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas text-sm text-ink-muted">
      Restoring session...
    </div>
  );
}

function RequireRole({
  check,
  children,
}: {
  check: (me: NonNullable<ReturnType<typeof useAuth>["me"]>) => boolean;
  children: ReactNode;
}) {
  const { me, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!me) return <Navigate to="/" replace />;
  if (!check(me)) return <Navigate to={primaryPortalPath(me)} replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />

          <Route
            path="/admin"
            element={
              <RequireRole check={(me) => me.user.is_platform_admin}>
                <AdminPage />
              </RequireRole>
            }
          />

          <Route
            path="/organizer"
            element={
              <RequireRole
                check={(me) =>
                  me.memberships.some(
                    (m) => m.role === "organizer" || m.role === "tenant_admin"
                  )
                }
              >
                <OrganizerDashboard />
              </RequireRole>
            }
          />

          <Route
            path="/organizer/members"
            element={
              <RequireRole
                check={(me) => me.memberships.some((m) => m.role === "tenant_admin")}
              >
                <TenantMembersPage />
              </RequireRole>
            }
          />

          <Route
            path="/organizer/assessments/:assessmentId"
            element={
              <RequireRole
                check={(me) =>
                  me.memberships.some(
                    (m) => m.role === "organizer" || m.role === "tenant_admin"
                  )
                }
              >
                <AssessmentDetail />
              </RequireRole>
            }
          />

          <Route
            path="/organizer/assessments/:assessmentId/results"
            element={
              <RequireRole
                check={(me) =>
                  me.memberships.some(
                    (m) => m.role === "organizer" || m.role === "tenant_admin"
                  )
                }
              >
                <ResultsGradingPage />
              </RequireRole>
            }
          />

          <Route
            path="/candidate"
            element={
              <RequireRole
                check={(me) => me.memberships.some((m) => m.role === "candidate")}
              >
                <CandidateHome />
              </RequireRole>
            }
          />

          <Route
            path="/exam/:attemptId"
            element={
              <RequireRole
                check={(me) => me.memberships.some((m) => m.role === "candidate")}
              >
                <ExamRunnerPage />
              </RequireRole>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
