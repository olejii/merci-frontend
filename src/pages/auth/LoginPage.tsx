import { useAuthStore } from 'src/stores';

function LoginPage() {
  const login = useAuthStore((state) => state.login);

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
  };

  return (
    <div>
      <button onClick={handleAdminLogin}>Войти как администратор</button>
      <button onClick={handleWaiterLogin}>Войти как официант</button>
    </div>
  );
}

export default LoginPage;
