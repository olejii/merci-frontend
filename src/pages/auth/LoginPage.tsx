import { useNavigate } from 'react-router-dom';
import { Page } from 'src/components/layouts';

function LoginPage() {
  /*const login = useAuthStore((state) => state.login);

  const handleAdminLogin = () => {
    login({
      id: '1',
      name: 'Администратор',
      role: 'admin',
    });
  };

  const handleWaiterLogin = () => {
    login({
      id: '2',
      name: 'Официант',
      role: 'waiter',
    });
  };*/

  const navigate = useNavigate();

  return (
    <Page>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <button onClick={() => navigate('/tip/1', { replace: true })}>
          click to navigate /tip/1
        </button>
      </div>
    </Page>
  );
}

export default LoginPage;
