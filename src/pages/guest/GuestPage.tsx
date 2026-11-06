import { Page } from 'src/components/layouts';

import Background from 'src/assets/Background.png';
import WaiterImg from 'src/assets/waiter.png';

import './GuestPage.css';
import { Button, WaitersGoal } from 'src/components';
import { useState, useRef } from 'react';
import { ShopIcon } from 'src/assets/icons';

function GuestPage() {
  const [tipsValue, setTipsValue] = useState<number>(0);
  const tipsInputRef = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState<boolean>(false);

  const suggested_tips = [300, 500, 700, 1000];

  return (
    <Page>
      <div>
        <img alt={''} src={Background} className={'background-img'} />
      </div>

      <div className={'guest-header'}>
        <div className={'guest-title'}>
          <ShopIcon /> Вкус-Сервис · Покровка
        </div>

        <div className={'guest-title'}>RU</div>
      </div>

      <div className={'waiter-info'}>
        <img src={WaiterImg} alt={''} />
        <div className={'waiter-info__name'}>Артем</div>
        <div className={'waiter-info__desc'}>Официант · стол 12</div>
      </div>

      <div className={'tips'}>
        <div className={'tips-header'}>Сумма чаевых</div>
        <div className="tips-input-wrapper" onClick={() => tipsInputRef.current?.focus()}>
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
              }}
              onBlur={() => setExpanded(tipsValue > 0)}
              aria-label="Сумма чаевых в рублях"
              ref={tipsInputRef}
            />
            <span className="tips-input__currency" aria-hidden="true">
              ₽
            </span>
          </div>
        </div>
        <div className={'suggested-tips'}>
          {suggested_tips.map((el, index) => {
            return (
              <div
                className={`tip ${tipsValue === el ? 'selected' : ''}`}
                key={index}
                onClick={() => setTipsValue(el)}
              >
                {el} ₽
              </div>
            );
          })}
        </div>

        <WaitersGoal
          goal={'Курсы бариста в Милане'}
          name={'Артема'}
          need={50000}
          sum={32000}
          expanded={expanded}
        />
      </div>
      <div className={'pay-button'}>
        <Button disabled={!tipsValue}>{tipsValue ? 'Оплатить' : 'Выберите сумму'}</Button>
      </div>

      {expanded ? <>expanded</> : null}
    </Page>
  );
}

export default GuestPage;
