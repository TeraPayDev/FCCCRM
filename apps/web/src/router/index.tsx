import { createBrowserRouter } from "react-router-dom";
import { AboutPage } from "../pages/AboutPage";
import { LoginPage } from "../pages/LoginPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { OrganisationsPage } from "../pages/OrganisationsPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SystemStatusPage } from "../pages/SystemStatusPage";

export const router = createBrowserRouter([
  { path: "/", element: <SystemStatusPage /> },
  { path: "/about", element: <AboutPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/profile", element: <ProfilePage /> },
  { path: "/organisations", element: <OrganisationsPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
