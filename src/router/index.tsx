import { createBrowserRouter } from 'react-router-dom';

import { LoginPage } from 'src/pages/auth';
import { GuestPage, SuccessPage } from 'src/pages/guest';
import { WaiterPage } from 'src/pages/waiter';
import { AdminPage } from 'src/pages/admin';
import NotFoundPage from 'src/pages/NotFoundPage';
import { ProtectedRoute } from 'src/router/guards';

const router = createBrowserRouter([
  {
    path: '/',
    element: <LoginPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/tip/:hash',
    children: [
      { path: '/tip/:hash', element: <GuestPage /> },
      { path: '/tip/:hash/success', element: <SuccessPage /> },
    ],
  },
  {
    path: '/success',
    element: <SuccessPage />,
  },
  {
    path: '/waiter',
    element: <ProtectedRoute allowedRoles={['waiter']} />,
    children: [
      {
        path: '/waiter',
        element: <WaiterPage />,
      },
    ],
  },
  {
    path: '/admin',
    element: <ProtectedRoute allowedRoles={['admin']} />,
    children: [
      {
        path: '/admin',
        element: <AdminPage />,
      },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);

export default router;
