// The colour-scheme choice, for code that runs before React does.
//
// Deliberately NOT a "use client" module. A value exported from a client module
// reaches a server component as a client reference rather than as the value, so
// building the pre-paint script from `THEME_KEY` in lib/theme.ts silently emitted
// `localStorage.getItem({})` and the stored choice was never read. Keeping the key and
// the script together here means the two cannot drift either.

/** Where the reader's explicit light/dark choice is stored. */
export const THEME_KEY = "cri-theme";

/**
 * Mirrors the stored choice onto <html data-theme> before the first paint, so a reader
 * who chose light or dark never sees a flash of the other one. One expression, and
 * tolerant of blocked storage: without it the device setting applies, which is the
 * default anyway.
 */
export const THEME_BOOT = `try{var m=localStorage.getItem(${JSON.stringify(
  THEME_KEY,
)});if(m==="light"||m==="dark")document.documentElement.setAttribute("data-theme",m)}catch(e){}`;
