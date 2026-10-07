import type { ReactNode } from "react";
import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AgentDashboardPage } from "./pages/AgentDashboardPage";
import { AgentListingsPage } from "./pages/AgentListingsPage";
import { HomePage } from "./pages/HomePage";
import { ListingDetailPage } from "./pages/ListingDetailPage";
import { EditListingPage, NewListingPage } from "./pages/ListingEditorPage";
import { ListingsPage } from "./pages/ListingsPage";
import { LoginPage } from "./pages/LoginPage";
import { MyBookingsPage } from "./pages/MyBookingsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SignupPage } from "./pages/SignupPage";

const buyerOnly = (page: ReactNode) => <ProtectedRoute role="buyer">{page}</ProtectedRoute>;
const agentOnly = (page: ReactNode) => <ProtectedRoute role="agent">{page}</ProtectedRoute>;

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="listings" element={<ListingsPage />} />
        <Route path="listings/:id" element={<ListingDetailPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />

        <Route path="my-bookings" element={buyerOnly(<MyBookingsPage />)} />

        <Route path="agent/dashboard" element={agentOnly(<AgentDashboardPage />)} />
        <Route path="agent/listings" element={agentOnly(<AgentListingsPage />)} />
        <Route path="agent/listings/new" element={agentOnly(<NewListingPage />)} />
        <Route path="agent/listings/:id/edit" element={agentOnly(<EditListingPage />)} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
