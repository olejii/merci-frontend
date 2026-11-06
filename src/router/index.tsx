import { createBrowserRouter } from 'react-router-dom';

import { LoginPage } from 'src/pages/auth';
import { GuestPage } from 'src/pages/guest';
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
    element: <GuestPage />,
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
