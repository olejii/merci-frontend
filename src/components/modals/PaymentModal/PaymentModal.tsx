import { useEffect, useRef, useState } from 'react';
import './PaymentModal.css';
import { Button } from 'src/components';
import { CloseIcon, PrivacyIcon } from 'src/assets/icons';

import CardImg from 'src/assets/Card.png';
import SBPImg from 'src/assets/SBP.png';
import SberPayImg from 'src/assets/SberPay.png';

interface PaymentModalProps {
  amount: number;
  onClose: () => void;
  info: {
    waiterName: string;
    spot: string;
    waiterPhoto: string;
  };
}

function PaymentModal({ amount, onClose, info }: PaymentModalProps) {
  const [isClosing, setIsClosing] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const dragStartY = useRef<number | null>(null);
  const dragOffset = useRef(0);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsClosing(true);
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const closeModal = () => {
    if (isClosing) return;
    if (contentRef.current) {
      contentRef.current.style.transform = '';
    }
    setIsClosing(true);
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (isClosing) return;
    dragStartY.current = event.clientY;
    dragOffset.current = 0;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragStartY.current === null || !contentRef.current) return;

    const offset = Math.max(0, event.clientY - dragStartY.current);
    dragOffset.current = offset;
    contentRef.current.style.transform = `translateY(${offset}px)`;
  };

  const handlePointerUp = () => {
    if (dragStartY.current === null || !contentRef.current) return;

    dragStartY.current = null;

    if (dragOffset.current > 100) {
      closeModal();
      return;
    }

    dragOffset.current = 0;
    contentRef.current.style.transform = '';
  };

  const payments_methods = [
    { name: 'СБП', description: 'Через приложение банка', icon: SBPImg },
    { name: 'Банковская карта', description: 'Visa, Mastercard, МИР', icon: CardImg },
    { name: 'SberPay', description: 'Оплата в СберБанк Онлайн', icon: SberPayImg },
  ];

  return (
    <div
      className={`modal-overlay${isClosing ? ' modal-overlay--closing' : ''}`}
      onClick={closeModal}
      onAnimationEnd={(event) => {
        if (isClosing && event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={contentRef}
        className={`modal-content${isClosing ? ' modal-content--closing' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="payment-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div
          className="modal-drag-handle"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <span />
        </div>

        <div className={'payment-modal-header'}>
          <span>Способ оплаты</span>
          <div className={'payment-modal-header__icon'} onClick={closeModal}>
            <CloseIcon />
          </div>
        </div>

        <div className={'modal-waiter-info'}>
          <img src={info.waiterPhoto} alt="" />
          <div>
            <span>{info.waiterName}</span>
            <span>{info.spot}</span>
          </div>
        </div>

        <div className={'modal-payment-methods'}>
          {payments_methods.map((el, index) => (
            <label key={index} className={'modal-payment-method'}>
              <img src={el.icon} alt={''} />
              <div>
                <span>{el.name}</span>
                <span>{el.description}</span>
              </div>
              <input
                type="radio"
                name="payment-method"
                value={el.name}
                defaultChecked={index === 0}
              />
            </label>
          ))}
        </div>

        <div className={'payment-info-card'}>
          <div className={'payment-info__row'}>
            Чаевые <span>{amount} ₽</span>
          </div>
          <div className={'payment-info__row payment-info__row--commission'}>
            Комиссия сервиса <span>{Math.floor(amount * 0.05)} ₽</span>
          </div>

          <div className={'payment-info__row payment-info__row--total'}>
            Итого <span>{amount + Math.floor(amount * 0.05)} ₽</span>
          </div>
        </div>

        <Button>Оплатить {amount + Math.floor(amount * 0.05)} ₽</Button>
        <div className={'payment-info-security'}>
          <PrivacyIcon /> Данные карты не передаются ресторану
        </div>
      </div>
    </div>
  );
}

export default PaymentModal;
