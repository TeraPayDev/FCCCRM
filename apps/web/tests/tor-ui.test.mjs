import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), "utf8");

test("TOR-aligned UI includes analytical charts, heatmaps, GIS layers and user management", () => {
  const modulePage = read("src/pages/RoadmapModulePage.tsx");
  const mapPage = read("src/pages/MapPage.tsx");
  const dashboard = read("src/pages/DashboardsPage.tsx");
  const router = read("src/router/index.tsx");
  const users = read("src/pages/UserManagementPage.tsx");
  const userForm = read("src/pages/UserFormPage.tsx");
  const reports = read("src/pages/ReportsPage.tsx");
  const knowledge = read("src/pages/KnowledgeHubPage.tsx");
  const citizen = read("src/pages/CitizenReportPage.tsx");
  const layout = read("src/components/AppLayout.tsx");

  assert.match(modulePage, /Temperature trend/);
  assert.match(modulePage, /Rainfall intensity/);
  assert.match(modulePage, /Tree distribution map/);
  assert.match(mapPage, /type:\s*[\"\']heatmap[\"\']/);
  assert.match(mapPage, /Temperature surface/);
  assert.match(dashboard, /Executive Climate Dashboard/);
  assert.match(router, /\/users/);
  assert.match(users, /User & Access Management/);
  assert.match(userForm, /Create CRAM User/);
  assert.match(reports, /Report builder/);
  assert.match(knowledge, /World Bank Documents & Reports API/);
  assert.match(citizen, /Community climate intelligence/);
  assert.match(modulePage, /ForecastChart/);
  assert.match(layout, /profile-dropdown/);
});
