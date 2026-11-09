import './SuccessPage.css';
import { Page } from 'src/components/layouts';
import { usePaymentStore } from 'src/stores';
import { Button, WaitersGoal } from 'src/components';
import { useEffect, type CSSProperties } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckIcon, HeartIcon, HeartOutlineIcon, ReceiptIcon, ReviewIcon } from 'src/assets/icons';

function SuccessPage() {
  const paymentResult = usePaymentStore((state) => state.paymentResult);
  const navigate = useNavigate();

  useEffect(() => {
    if (!paymentResult) {
      navigate('/tip/1', { replace: true });
    }
  }, [paymentResult, navigate]);

  const goal = paymentResult?.goal;

  return (
    <Page>
      <div className={'success-thanks'}>
        <div className={'waiter-photo'}>
          <img src={paymentResult?.waiterPhoto} alt="" />
          <HeartIcon />
        </div>
        <div className={'success-confetti'} aria-hidden={'true'}>
          {Array.from({ length: 36 }, (_, index) => (
            <span
              key={index}
              style={
                {
                  left: '50%',
                  top: '200px',
                  animationDelay: `${(index % 6) * 0.001}s`,
                  animationDuration: '2s',
                  '--spread-x': `${Math.round(Math.cos((index / 36) * Math.PI * 2) * (90 + (index % 4) * 25))}px`,
                  '--spread-y': `${-Math.round(100 + (index % 5) * 24)}px`,
                  '--spin': `${(index % 2 ? 1 : -1) * (360 + (index % 3) * 180)}deg`,
                } as CSSProperties
              }
            />
          ))}
        </div>

        <div className={'success-thanks__header'}>Спасибо!</div>
        <div className={'success-thanks__subheader'}>
          {paymentResult?.waiterName} получит <span>{paymentResult?.amount} ₽</span> сегодня.
          {paymentResult?.complimentLeft ? (
            <>
              <br />
              Ваш комплимент уже у него
            </>
          ) : null}
        </div>
      </div>
      <div className={'success-body'}>
        <WaitersGoal
          name={paymentResult?.waiterName ?? ''}
          goal={goal?.name ?? ''}
          sum={(goal?.collectedAmount ?? 0) + (paymentResult?.amount ?? 0)}
          need={goal?.targetAmount ?? 0}
          mode={'success'}
          amount={paymentResult?.amount ?? 0}
        />

        <div className={'success-body-info'}>
          {paymentResult?.complimentLeft ? (
            <div className={'success-body-info__item'}>
              <HeartOutlineIcon /> <span>Комплимент {paymentResult.waiterName}</span>
              <div>
                <CheckIcon /> Отправлен
              </div>
            </div>
          ) : null}
          {paymentResult?.restaurantReviewLeft ? (
            <div className={'success-body-info__item'}>
              <ReviewIcon /> <span>Отзыв ресторану</span>
              <div>
                <CheckIcon /> Отправлен
              </div>
            </div>
          ) : null}
          <div className={'success-body-info__item'}>
            <ReceiptIcon /> <span>Чек об оплате</span> <div>Получить</div>
          </div>
        </div>
      </div>

      <div className={'success-bottom'}>
        <Button onClick={() => navigate('/', { replace: true })}>Готово</Button>
        <Button type={'outline'}>Оставить отзыв на картах</Button>
      </div>
    </Page>
  );
}

export default SuccessPage;
