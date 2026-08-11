import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { ApprovalQueuePage } from "../pages/ApprovalQueuePage";
import { AuditPage } from "../pages/AuditPage";
import { DatasetDetailPage } from "../pages/DatasetDetailPage";
import { DatasetsPage } from "../pages/DatasetsPage";
import { MapPage } from "../pages/MapPage";
import { AboutPage } from "../pages/AboutPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { OrganisationsPage } from "../pages/OrganisationsPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SystemStatusPage } from "../pages/SystemStatusPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <SystemStatusPage /> },
      { path: "/about", element: <AboutPage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/organisations", element: <OrganisationsPage /> },
      { path: "/audit", element: <AuditPage /> },
      { path: "/map", element: <MapPage /> },
      { path: "/datasets", element: <DatasetsPage /> },
      { path: "/datasets/:datasetId", element: <DatasetDetailPage /> },
      { path: "/approvals", element: <ApprovalQueuePage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
