import { createBrowserRouter } from "react-router-dom";
import { AboutPage } from "../pages/AboutPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { SystemStatusPage } from "../pages/SystemStatusPage";

export const router = createBrowserRouter([
  { path: "/", element: <SystemStatusPage /> },
  { path: "/about", element: <AboutPage /> },
  { path: "*", element: <NotFoundPage /> },
]);
