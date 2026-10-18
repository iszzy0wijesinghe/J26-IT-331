import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from '../layouts/AppLayout';
import { OverviewPage } from '../features/overview/pages/OverviewPage';
import { C1Page } from '../features/c1/pages/C1Page';
import { C2Page } from '../features/c2/pages/C2Page';
import { C3Page } from '../features/c3/pages/C3Page';
import { C4Page } from '../features/c4/pages/C4Page';

export function App() {
  return <Routes><Route element={<AppLayout />}>
    <Route index element={<OverviewPage />} />
    <Route path="c1/*" element={<C1Page />} />
    <Route path="c2/*" element={<C2Page />} />
    <Route path="c3/*" element={<C3Page />} />
    <Route path="c4/*" element={<C4Page />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes>;
}
