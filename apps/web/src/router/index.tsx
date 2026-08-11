import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/AppLayout";
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
import { DashboardsPage } from "../pages/DashboardsPage";
import { RoadmapModulePage } from "../pages/RoadmapModulePage";
import { CitizenReportPage } from "../pages/CitizenReportPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/report-hazard", element: <CitizenReportPage /> },
  {
    element: <AppLayout />,
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
      { path: "/dashboards", element: <DashboardsPage /> },
      { path: "/processing", element: <RoadmapModulePage module="processing" /> },
      { path: "/heat", element: <RoadmapModulePage module="heat" /> },
      { path: "/flood", element: <RoadmapModulePage module="flood" /> },
      { path: "/trees", element: <RoadmapModulePage module="trees" /> },
      { path: "/vulnerability", element: <RoadmapModulePage module="vulnerability" /> },
      { path: "/citizen-reports", element: <RoadmapModulePage module="citizen" /> },
      { path: "/notifications", element: <RoadmapModulePage module="notifications" /> },
      { path: "/reports", element: <RoadmapModulePage module="reports" /> },
      { path: "/knowledge", element: <RoadmapModulePage module="knowledge" /> },
      { path: "/administration", element: <RoadmapModulePage module="administration" /> },
      { path: "/analytics", element: <RoadmapModulePage module="analytics" /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
