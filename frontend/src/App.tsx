import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { HomePage } from "./pages/HomePage";
import { ListingDetailPage } from "./pages/ListingDetailPage";
import { ListingsPage } from "./pages/ListingsPage";
import { LoginPage } from "./pages/LoginPage";
import { ComingSoonPage, NotFoundPage } from "./pages/NotFoundPage";
import { SignupPage } from "./pages/SignupPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="listings" element={<ListingsPage />} />
        <Route path="listings/:id" element={<ListingDetailPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />

        <Route
          path="my-bookings"
          element={
            <ProtectedRoute role="buyer">
              <ComingSoonPage title="My bookings" />
            </ProtectedRoute>
          }
        />
        <Route
          path="agent/dashboard"
          element={
            <ProtectedRoute role="agent">
              <ComingSoonPage title="Agent dashboard" />
            </ProtectedRoute>
          }
        />
        <Route
          path="agent/listings/*"
          element={
            <ProtectedRoute role="agent">
              <ComingSoonPage title="My listings" />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
