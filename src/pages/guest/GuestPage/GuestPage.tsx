import { useState, useRef, useEffect } from 'react';

import { Page } from 'src/components/layouts';
import { Button, Loader, WaitersGoal } from 'src/components';
import { PaymentModal } from 'src/components/modals';

import { EyeIcon, PrivacyIcon, ReceiptIcon, ShopIcon, StarIon } from 'src/assets/icons';

import Background from 'src/assets/Background.png';
import WaiterImg from 'src/assets/waiter.png';

import './GuestPage.css';
import { api } from 'src/api/client.ts';
import type { QRResponse } from 'src/api/api.ts';

const test_sum = Math.floor(Math.random() * 401) * 10 + 1000;
const test_table = Math.floor(Math.random() * 10) + 1;

function GuestPage() {
  const [tipsValue, setTipsValue] = useState<number>(0);
  const [tipsError, setTipsError] = useState<boolean>(false);
  const tipsInputRef = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState<boolean>(false);
  const [rating, setRating] = useState(3);
  const [restReview, setRestReview] = useState<string>('');
  const [waiterReview, setWaiterReview] = useState<string>('');
  const [selectedCompliments, setSelectedCompliments] = useState<string[]>([]);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const [paymentInfo, setPaymentInfo] = useState<QRResponse | null>(null);

  const suggested_tips = [300, 500, 700, 1000];
  const suggested_compliments = ['Внимательный', 'Быстро', 'Отличные советы', 'Улыбка', 'Как дома'];
  const payment_methods = ['СБП', 'SberPay', 'Карта'];

  const initTipInfo = () => {
    setLoading(true);
    console.log('loading true');
    const qrId = window.location.href.split('/')[4];
    console.log(qrId);

    try {
      api.v1QrDetail(qrId).then((res) => {
        setLoading(false);
        console.log(res);
        setPaymentInfo(res.data);
      });
    } catch (error) {
      setLoading(false);
      console.error(error);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    initTipInfo();
  }, []);

  return (
    <Page>
      {!loading ? (
        <>
          <div>
            <img alt={''} src={Background} className={'background-img'} />
          </div>

          <div className={'guest-header'}>
            <div className={'guest-title'}>
              <ShopIcon /> Вкус-Сервис · {paymentInfo?.merchant_name.split('Вкус-Сервис')[1]}
            </div>

            <div className={'guest-title'}>RU</div>
          </div>

          <div className={'waiter-info'}>
            <img src={WaiterImg} alt={''} />
            <div className={'waiter-info__name'}>{paymentInfo?.employee_name}</div>
            <div className={'waiter-info__desc'}>
              {paymentInfo?.employee_role_label} · стол {test_table}
            </div>
            {expanded ? (
              <div className={'waiters-message'}>
                «Спасибо, что пришли к нам! Буду рад видеть вас снова»
              </div>
            ) : null}
          </div>

          <div className={'tips'}>
            <div className={'tips-header'}>Сумма чаевых</div>
            <div
              className={`tips-input-wrapper ${tipsError ? 'error' : ''}`}
              onClick={() => tipsInputRef.current?.focus()}
            >
              <div className="tips-input__value">
                <input
                  className="tips-input"
                  type="text"
                  inputMode="numeric"
                  placeholder="0"
                  value={tipsValue || ''}
                  maxLength={6}
                  style={{ width: `${Math.max(String(tipsValue || '').length, 1)}ch` }}
                  onChange={(event) => {
                    const digits = event.target.value.replace(/\D/g, '');
                    setTipsValue(digits ? Number(digits) : 0);
                    setTipsError(false);
                  }}
                  onBlur={() => {
                    if (tipsValue > 0 && tipsValue < 100) {
                      setTipsError(true);
                      setExpanded(false);
                      return;
                    }

                    setTipsError(false);
                    setExpanded(tipsValue >= 100);
                  }}
                  aria-label="Сумма чаевых в рублях"
                  ref={tipsInputRef}
                />
                <span className="tips-input__currency" aria-hidden="true">
                  ₽
                </span>
              </div>
            </div>
            {tipsError ? <div className="tips-error">Минимальная сумма чаевых — 100 ₽</div> : null}
            <div className={'suggested-tips'}>
              {suggested_tips.map((el, index) => {
                return (
                  <div
                    className={`tip ${tipsValue === el ? 'selected' : ''}`}
                    key={index}
                    onClick={() => {
                      setTipsValue(el);
                      setTipsError(false);
                      setExpanded(true);
                    }}
                  >
                    {el} ₽
                  </div>
                );
              })}
            </div>

            {expanded ? (
              <div className={'receipt-info'}>
                <ReceiptIcon /> Счет {test_sum} ₽ · это {Math.floor((tipsValue / test_sum) * 100)}%
              </div>
            ) : null}

            <WaitersGoal
              className={'waiters-goal-guest'}
              goal={paymentInfo?.active_goals[0].title ?? ''}
              name={paymentInfo?.employee_name ?? ''}
              need={Number(paymentInfo?.active_goals[0].target_amount)}
              sum={Number(paymentInfo?.active_goals[0].collected_amount)}
              mode={expanded ? 'expanded' : 'default'}
            />
          </div>

          {expanded ? (
            <>
              <div className={'waiter-rate'}>
                <span>Как вам визит?</span>
                <div className="waiter-rate__stars">
                  {Array.from({ length: 5 }, (_, index) => (
                    <span
                      key={index}
                      onClick={() => setRating(index + 1)}
                      className={index < rating ? 'active' : ''}
                    >
                      <StarIon />
                    </span>
                  ))}
                </div>
              </div>
              <div className={'rest-review-header'}>
                <span>Отзыв ресторану</span>
                <div className={'rest-review-badge'}>
                  <EyeIcon /> видит администратор
                </div>
              </div>
              <textarea
                rows={4}
                className={'rest-review-input'}
                placeholder={'Оставьте отзыв о посещении ресторана...'}
                maxLength={150}
                value={restReview}
                onChange={(event) => setRestReview(event.target.value)}
              />
              <div className={'waiter-review-header'}>
                <span>Комплимент Артему</span>
                <div className={'waiter-review-badge'}>
                  <PrivacyIcon /> видит только Артем
                </div>
              </div>
              <div className={'suggested-compliments'}>
                {suggested_compliments.map((el, index) => {
                  return (
                    <div
                      className={`suggested-compliment ${selectedCompliments.includes(el) ? 'selected' : ''}`}
                      key={index}
                      onClick={() => {
                        setSelectedCompliments((current) =>
                          current.includes(el)
                            ? current.filter((item) => item !== el)
                            : [...current, el],
                        );
                      }}
                    >
                      {el}
                    </div>
                  );
                })}
              </div>
              <textarea
                rows={4}
                className={'waiter-review-input'}
                placeholder={'Напишите пару ласковых слов...'}
                maxLength={150}
                value={waiterReview}
                onChange={(event) => setWaiterReview(event.target.value)}
              />
            </>
          ) : null}

          <div className={'pay-button'}>
            <Button disabled={tipsValue < 100} onClick={() => setIsPaymentModalOpen(true)}>
              {tipsValue ? `Оплатить ${tipsValue} ₽` : 'Выберите сумму'}
            </Button>
          </div>

          {expanded ? (
            <>
              <div className={'payment-methods'}>
                {payment_methods.map((el, index) => {
                  return (
                    <div key={index} className={'payment-method'}>
                      {el}
                    </div>
                  );
                })}
              </div>
              <div className={'payment-info'}>
                Оплата через защищённый сервис. Нажимая кнопку, вы принимаете <a>условия</a>
              </div>
            </>
          ) : null}

          {isPaymentModalOpen && (
            <PaymentModal
              info={{
                waiterName: paymentInfo?.employee_name ?? '',
                waiterPhoto: WaiterImg,
                spot: `Вкус-Сервис · ${paymentInfo?.merchant_name.split('Вкус-Сервис')[1]}`,
                complimentLeft: waiterReview.length > 0 || selectedCompliments.length > 0,
                restaurantComplimentLeft: restReview.length > 0,
                goal: {
                  name: paymentInfo?.active_goals[0].title ?? '',
                  collectedAmount: Number(paymentInfo?.active_goals[0].collected_amount),
                  targetAmount: Number(paymentInfo?.active_goals[0].target_amount),
                },
              }}
              amount={tipsValue}
              onClose={() => setIsPaymentModalOpen(false)}
            />
          )}
        </>
      ) : (
        <Loader />
      )}
    </Page>
  );
}

export default GuestPage;
