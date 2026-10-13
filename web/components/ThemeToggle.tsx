"use client";

// Light / dark / follow-the-device, as one segmented control in the header.
//
// The site followed the device setting alone before. Owners demo this on a borrowed
// laptop or a projector, where the device setting is not theirs to change, so the
// choice is worth three buttons. "Auto" is the default and removes the override.
import { useThemeMode, type ThemeMode } from "@/lib/theme";

// Hand-authored marks (docs/CREDITS.md): a sun, a crescent, and a display for
// "whatever this device says".
const ICONS: Record<ThemeMode, React.ReactNode> = {
  light: (
    <>
      <circle cx="10" cy="10" r="3.6" />
      <path d="M10 2.2v1.9M10 15.9v1.9M2.2 10h1.9M15.9 10h1.9M4.5 4.5l1.3 1.3M14.2 14.2l1.3 1.3M15.5 4.5l-1.3 1.3M5.8 14.2l-1.3 1.3" />
    </>
  ),
  dark: <path d="M14.6 12.4A5.6 5.6 0 0 1 7.6 5.4a5.6 5.6 0 1 0 7 7Z" />,
  system: (
    <>
      <rect x="2.6" y="4" width="14.8" height="9.4" rx="1.4" />
      <path d="M7.4 16.4h5.2" />
    </>
  ),
};

const LABELS: Record<ThemeMode, string> = {
  light: "Light",
  dark: "Dark",
  system: "Match this device",
};

const ORDER: ThemeMode[] = ["system", "light", "dark"];

export default function ThemeToggle() {
  const { mode, setMode } = useThemeMode();
  return (
    // A radiogroup, not a set of buttons: the three are one choice, and arrow keys
    // move between them the way a radio group should.
    <div className="theme-toggle" role="radiogroup" aria-label="Colour scheme">
      {ORDER.map((m) => {
        const on = mode === m;
        return (
          <button
            key={m}
            type="button"
            role="radio"
            aria-checked={on}
            // Only the selected button takes tab focus; arrows move within the group.
            tabIndex={on ? 0 : -1}
            className={on ? "theme-btn on" : "theme-btn"}
            title={LABELS[m]}
            onClick={() => setMode(m)}
            onKeyDown={(e) => {
              const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
              if (!step) return;
              e.preventDefault();
              const next = ORDER[(ORDER.indexOf(mode) + step + ORDER.length) % ORDER.length];
              setMode(next);
              // Keep focus with the selection, as a radio group does.
              (e.currentTarget.parentElement?.children[ORDER.indexOf(next)] as HTMLElement)?.focus();
            }}
          >
            <svg viewBox="0 0 20 20" aria-hidden focusable="false">
              {ICONS[m]}
            </svg>
            <span className="visually-hidden">{LABELS[m]}</span>
          </button>
        );
      })}
    </div>
  );
}
