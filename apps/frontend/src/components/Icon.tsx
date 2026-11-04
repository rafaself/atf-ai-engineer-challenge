import type { ReactNode } from "react";

type IconName = "music" | "plus" | "send" | "arrowDown" | "history" | "close" | "trash";

type IconProps = {
  name: IconName;
  size?: number;
};

const paths: Record<IconName, ReactNode> = {
  music: (
    <>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </>
  ),
  plus: (
    <>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </>
  ),
  send: (
    <>
      <path d="m4 4 17 8-17 8 3.5-8L4 4Z" />
      <path d="M7.5 12H21" />
    </>
  ),
  arrowDown: <path d="M12 4v16m-7-7 7 7 7-7" />,
  history: (
    <>
      <path d="M3 12a9 9 0 1 0 2.64-6.36L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  trash: (
    <>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2m3 0-1 14H6L5 6" />
      <path d="M10 11v5m4-5v5" />
    </>
  ),
};

export function Icon({ name, size = 20 }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
    >
      {paths[name]}
    </svg>
  );
}
