import { useEffect } from 'react';
import { useSignal, miniApp } from '@tma.js/sdk-react';

/**
 * Hook to sync Telegram's dark mode with antd-mobile theme
 * Sets data-prefers-color-scheme attribute on html element
 * @param forceLight - If true, always use light mode regardless of Telegram theme
 */
export function useAntdMobileTheme(forceLight = false) {
  const isDark = useSignal(miniApp.isDark);
  const effectiveDark = forceLight ? false : isDark;

  useEffect(() => {
    const htmlElement = document.documentElement;
    htmlElement.setAttribute('data-prefers-color-scheme', effectiveDark ? 'dark' : 'light');
  }, [effectiveDark]);

  return effectiveDark;
}
