import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "home"
  | "data"
  | "map"
  | "heat"
  | "flood"
  | "trees"
  | "vulnerability"
  | "citizen"
  | "bell"
  | "chart"
  | "report"
  | "knowledge"
  | "settings"
  | "audit"
  | "organisation"
  | "user"
  | "processing"
  | "check"
  | "activity"
  | "search"
  | "menu"
  | "close"
  | "arrow";

const paths: Record<IconName, ReactNode> = {
  home: (
    <>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10.5V20h13v-9.5" />
      <path d="M9 20v-6h6v6" />
    </>
  ),
  data: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </>
  ),
  map: (
    <>
      <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
      <path d="M9 3v15M15 6v15" />
    </>
  ),
  heat: (
    <>
      <path d="M12 3v10" />
      <path d="M8.5 13.5a5 5 0 1 0 7 0" />
      <path d="M12 6a3 3 0 0 1 3 3v5.2" />
      <path d="M12 18h.01" />
    </>
  ),
  flood: (
    <>
      <path d="M3 7h18" />
      <path d="M5 11c1.5 0 1.5 1 3 1s1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1" />
      <path d="M4 16c1.5 0 1.5 1 3 1s1.5-1 3-1 1.5 1 3 1 1.5-1 3-1 1.5 1 3 1" />
    </>
  ),
  trees: (
    <>
      <path d="M12 21v-7" />
      <path d="M7 14h10" />
      <path d="M12 3c4 2 6 5 6 8a6 6 0 0 1-12 0c0-3 2-6 6-8Z" />
    </>
  ),
  vulnerability: (
    <>
      <path d="M12 3 4 7v5c0 5 3.4 8 8 9 4.6-1 8-4 8-9V7Z" />
      <path d="m9.5 12 1.7 1.7 3.6-4" />
    </>
  ),
  citizen: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.5 20a5.5 5.5 0 0 1 11 0" />
      <path d="M16 8h5M18.5 5.5V10.5" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </>
  ),
  chart: (
    <>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20V7" />
    </>
  ),
  report: (
    <>
      <path d="M6 3h9l4 4v14H6Z" />
      <path d="M14 3v5h5M9 12h6M9 16h6" />
    </>
  ),
  knowledge: (
    <>
      <path d="M4 5a4 4 0 0 1 4-2h10v16H8a4 4 0 0 0-4 2Z" />
      <path d="M4 5v16" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
    </>
  ),
  audit: (
    <>
      <path d="M5 3h14v18H5Z" />
      <path d="M9 7h6M9 11h6M9 15h3" />
    </>
  ),
  organisation: (
    <>
      <path d="M4 21V8l8-5 8 5v13" />
      <path d="M8 21v-5h8v5M8 10h.01M12 10h.01M16 10h.01" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  processing: (
    <>
      <path d="M4 7h12M4 12h8M4 17h10" />
      <circle cx="18" cy="17" r="3" />
      <path d="m20.2 19.2 1.8 1.8" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  activity: <path d="M3 12h4l2-6 4 12 2-6h6" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
};

export function Icon({ name, ...props }: { name: IconName } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name]}
    </svg>
  );
}
