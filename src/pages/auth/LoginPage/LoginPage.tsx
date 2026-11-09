import { Page } from 'src/components/layouts';

import './LoginPage.css';
import { Button, Loader } from 'src/components';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from 'src/api/client.ts';
import { useAuthStore } from 'src/stores';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isEmailValid = emailRegex.test(email);
  const disabled = !isEmailValid || password.trim().length === 0;
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

  // const navigate = useNavigate();
  //
  // const toggleAPI = () => {
  //   try {
  //     api
  //       .v1AuthLoginCreate({ email: 'a@a.com', password: '123' })
  //       .then((data) => console.log(data));
  //   } catch (error) {
  //     console.error(error);
  //   }
  // };

  const handleLogin = async () => {
    setLoading(true);
    setLoginError('');

    try {
      const res = await api.v1AuthLoginCreate({ email, password });

      if (res.data.status === 'ok' && res.data.user_id) {
        login({ id: res.data.user_id, name: '', role: 'waiter' });
        navigate('/waiter', { replace: true });
      }
    } catch (error: unknown) {
      console.error(error);

      const err: Record<string, unknown> =
        typeof error === 'object' && error !== null ? (error as Record<string, unknown>) : {};

      const response =
        typeof err.response === 'object' && err.response !== null
          ? (err.response as Record<string, unknown>)
          : {};

      const apiErrorCandidate =
        err.error ?? err.data ?? err.body ?? response.data ?? response.body ?? err;

      const apiError: Record<string, unknown> =
        typeof apiErrorCandidate === 'object' && apiErrorCandidate !== null
          ? (apiErrorCandidate as Record<string, unknown>)
          : {};

      const errorMessages: Record<string, string> = {
        INVALID_CREDENTIALS: 'Неверный email или пароль.',
        USER_NOT_FOUND: 'Пользователь с таким email не найден.',
        ACCOUNT_DISABLED: 'Аккаунт заблокирован. Обратитесь к администратору.',
        VALIDATION_ERROR: 'Проверьте правильность введённых данных.',
      };

      console.log('Login API error payload:', apiError);

      const errorCode = typeof apiError.error_code === 'string' ? apiError.error_code : undefined;
      const errorMessage = typeof apiError.message === 'string' ? apiError.message : undefined;
      const fallbackMessage = typeof err.message === 'string' ? err.message : undefined;

      setLoginError(
        (errorCode && errorMessages[errorCode]) ||
          errorMessage ||
          fallbackMessage ||
          'Не удалось войти. Проверьте подключение к интернету и попробуйте ещё раз.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page>
      {loading ? <Loader /> : null}
      <div className={'auth-header'}>Авторизация</div>

      <div className={'auth-container'}>
        <div>
          <span>Введите email</span>
          <input
            className={'auth-input'}
            placeholder={'ivanov@mail.ru'}
            onChange={(e) => {
              setEmail(e.target.value);
              setEmailError(false);
              setLoginError('');
            }}
            onBlur={() => {
              setEmailError(email.length > 0 && !isEmailValid);
            }}
            value={email}
          />
          {emailError && <span className={'auth-error'}>Введите корректный email</span>}
        </div>
        <div>
          <span>Введите пароль</span>
          <input
            type={'password'}
            className={'auth-input'}
            placeholder={'****'}
            maxLength={16}
            onChange={(e) => {
              setPassword(e.target.value);
              setLoginError('');
            }}
            value={password}
          />
        </div>
        {loginError && (
          <div className={'auth-error auth-error--server'} role={'alert'}>
            {loginError}
          </div>
        )}
      </div>

      <Button onClick={handleLogin} disabled={disabled || loading}>
        Войти
      </Button>
    </Page>
  );
}

export default LoginPage;
