import type { ReactNode } from "react";

type IconName = "music" | "plus" | "send" | "arrowDown";

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
