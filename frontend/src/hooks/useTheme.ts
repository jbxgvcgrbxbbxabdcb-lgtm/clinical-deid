import { useCallback, useEffect, useState } from "react";
import { THEME_NAMES, THEME_STORAGE_KEY, THEMES } from "@/constants";
import type { ThemeName } from "@/types";

function readStoredTheme(): ThemeName {
  try {
    const raw = localStorage.getItem(THEME_STORAGE_KEY);
    if (raw && THEMES.includes(raw as ThemeName)) return raw as ThemeName;
  } catch {
    /* ignore */
  }
  return "mist";
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemeName>(() => readStoredTheme());

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const cycleTheme = useCallback(() => {
    setThemeState((cur) => {
      const idx = Math.max(0, THEMES.indexOf(cur));
      return THEMES[(idx + 1) % THEMES.length];
    });
  }, []);

  return {
    theme,
    themeLabel: THEME_NAMES[theme],
    cycleTheme,
  };
}
