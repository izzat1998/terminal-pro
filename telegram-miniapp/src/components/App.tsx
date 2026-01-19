import { Navigate, Route, Routes, HashRouter } from 'react-router-dom';
import { useLaunchParams } from '@tma.js/sdk-react';
import { AppRoot } from '@telegram-apps/telegram-ui';

import { routes } from '@/navigation/routes.tsx';
import { Layout } from '@/components/Layout.tsx';
import { PageProvider } from '@/contexts/PageContext.tsx';
import { CameraProvider } from '@/contexts/CameraContext.tsx';
import { useAntdMobileTheme } from '@/hooks/useAntdMobileTheme.ts';

export function App() {
  const lp = useLaunchParams();

  // Force light mode for work orders app (outdoor workers need high contrast)
  useAntdMobileTheme(true); // force light

  return (
    <AppRoot
      appearance="light"
      platform={['macos', 'ios'].includes(lp.tgWebAppPlatform) ? 'ios' : 'base'}
    >
      <CameraProvider>
        <PageProvider>
          <HashRouter>
            <Routes>
              <Route element={<Layout />}>
                {routes.map((route) => <Route key={route.path} {...route} />)}
              </Route>
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </HashRouter>
        </PageProvider>
      </CameraProvider>
    </AppRoot>
  );
}
