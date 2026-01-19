import type { ComponentType, JSX } from 'react';

import { IndexPage } from '@/pages/IndexPage/IndexPage';
import { VehiclesPage } from '@/pages/VehiclesPage/VehiclesPage';
import { CameraPage } from '@/pages/CameraPage/CameraPage';
import { ExitEntryPage } from '@/pages/ExitEntryPage/ExitEntryPage';
import { ExitByIdPage } from '@/pages/ExitByIdPage/ExitByIdPage';
import { CheckInPage } from '@/pages/CheckInPage/CheckInPage';
import { WorkOrdersPage } from '@/pages/WorkOrdersPage/WorkOrdersPage';

interface Route {
  path: string;
  Component: ComponentType;
  title?: string;
  icon?: JSX.Element;
}

export const routes: Route[] = [
  { path: '/', Component: IndexPage },
  { path: '/vehicles', Component: VehiclesPage, title: 'Vehicles' },
  { path: '/vehicles/add-entry', Component: CameraPage, title: 'Add Vehicle Entry' },
  { path: '/vehicles/exit-entry', Component: ExitEntryPage, title: 'Exit Vehicle' },
  { path: '/vehicles/exit-entry/:id', Component: ExitByIdPage, title: 'Exit Vehicle By ID' },
  { path: '/vehicles/accept-entry/:id', Component: CheckInPage, title: 'Check In Vehicle' },
  { path: '/work-orders', Component: WorkOrdersPage, title: 'Вазифалар' },
];
