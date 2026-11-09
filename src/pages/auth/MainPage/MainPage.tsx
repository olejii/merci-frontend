//import { useNavigate } from 'react-router-dom';
import { Page } from 'src/components/layouts';
//import { api } from 'src/api/client.ts';
import { AppIcon } from 'src/assets/icons';
import { Button } from 'src/components';

import './MainPage.css';

import BackgroundMainImg from 'src/assets/Background-main.png';
import { useNavigate } from 'react-router-dom';

function MainPage() {
  const navigate = useNavigate();
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

  const handleGoLogin = () => {
    navigate('/auth');
  };

  return (
    <Page>
      <div className={'img-wrapper'}>
        <img src={BackgroundMainImg} alt={''} className={'background-img-main'} />
      </div>

      <div className={'login-container'}>
        <div className={'login-app-name'}>
          <AppIcon /> мерси
        </div>
        <div className={'login-header'}>
          Чаевые, которые <span>согревают</span>
        </div>
        <div className={'login-text'}>
          Гости благодарят за секунды, а вы видите каждый комплимент
        </div>
        <Button onClick={handleGoLogin}>Вход для сотрудников</Button>
      </div>
    </Page>
  );
}

export default MainPage;
