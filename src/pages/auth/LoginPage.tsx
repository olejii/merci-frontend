import { useNavigate } from 'react-router-dom';
import { Page } from 'src/components/layouts';
import { api } from 'src/api/client.ts';

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

  const toggleAPI = () => {
    try {
      api
        .v1AuthLoginCreate({ email: 'a@a.com', password: '123' })
        .then((data) => console.log(data));
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <Page>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <button onClick={() => navigate('/tip/1', { replace: true })}>
          click to navigate /tip/1
        </button>
        <button onClick={toggleAPI}>click to toggle API</button>
      </div>
    </Page>
  );
}

export default LoginPage;
