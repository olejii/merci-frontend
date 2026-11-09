import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';

import PaymentModal from './PaymentModal';
import { usePaymentStore } from 'src/stores';

const mockInfo = {
  waiterName: 'Артем',
  spot: 'Вкус-Сервис · Покровка',
  waiterPhoto: 'waiter.png',
  goal: {
    name: 'Курсы бариста в Милане',
    collectedAmount: 32000,
    targetAmount: 50000,
  },
  complimentLeft: true,
  restaurantComplimentLeft: false,
};

describe('PaymentModal Inputs & Interactions', () => {
  const renderModal = (amount = 500, onClose = vi.fn(), route = '/tip/hash123') => {
    const user = userEvent.setup();
    const utils = render(
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route
            path="/tip/:hash"
            element={<PaymentModal amount={amount} onClose={onClose} info={mockInfo} />}
          />
          <Route
            path="/no-hash"
            element={<PaymentModal amount={amount} onClose={onClose} info={mockInfo} />}
          />
          <Route path="/tip/:hash/success" element={<div>Success Route</div>} />
        </Routes>
      </MemoryRouter>,
    );
    return { user, onClose, ...utils };
  };

  describe('1. Payment Method Radio Inputs', () => {
    it('renders all 3 payment method radio inputs with "СБП" checked by default', () => {
      renderModal();

      const radios = screen.getAllByRole('radio');
      expect(radios).toHaveLength(3);

      const sbpRadio = screen.getByDisplayValue('СБП');
      const cardRadio = screen.getByDisplayValue('Банковская карта');
      const sberRadio = screen.getByDisplayValue('SberPay');

      expect(sbpRadio).toBeChecked();
      expect(cardRadio).not.toBeChecked();
      expect(sberRadio).not.toBeChecked();
    });

    it('switches the active radio selection when clicking another payment method label or radio', async () => {
      const { user } = await renderModal();

      const sbpRadio = screen.getByDisplayValue('СБП');
      const cardRadio = screen.getByDisplayValue('Банковская карта');
      const sberRadio = screen.getByDisplayValue('SberPay');

      await user.click(screen.getByText('Банковская карта'));
      expect(cardRadio).toBeChecked();
      expect(sbpRadio).not.toBeChecked();

      await user.click(screen.getByText('SberPay'));
      expect(sberRadio).toBeChecked();
      expect(cardRadio).not.toBeChecked();
    });
  });

  describe('2. Commission & Total Calculation', () => {
    it.each([
      { amount: 500, expectedFee: 25, expectedTotal: 525 },
      { amount: 333, expectedFee: 16, expectedTotal: 349 },
      { amount: 100, expectedFee: 5, expectedTotal: 105 },
    ])(
      'calculates 5% floor commission ($expectedFee ₽) and total ($expectedTotal ₽) for $amount ₽',
      ({ amount, expectedFee, expectedTotal }) => {
        renderModal(amount);

        expect(screen.getByText(`${expectedFee} ₽`)).toBeInTheDocument();
        expect(
          screen.getByRole('button', { name: `Оплатить ${expectedTotal} ₽` }),
        ).toBeInTheDocument();
      },
    );
  });

  describe('3. Modal Dismissal Inputs (Escape, Overlay, Pointer Drag Gesture)', () => {
    it('starts closing on Escape keydown and triggers onClose after animationEnd', () => {
      const { onClose, container } = renderModal();
      const overlay = container.querySelector('.modal-overlay')!;

      fireEvent.keyDown(document, { key: 'Escape' });
      expect(overlay).toHaveClass('modal-overlay--closing');

      fireEvent.animationEnd(overlay);
      fireEvent(overlay, new Event('webkitAnimationEnd', { bubbles: true }));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('snaps back if pointer drag offset is <= 100px, and closes if dragged > 100px', () => {
      const { container } = renderModal();
      const dragHandle = container.querySelector('.modal-drag-handle')!;
      const dialog = screen.getByRole('dialog');
      const overlay = container.querySelector('.modal-overlay')!;

      // Drag 60px (<= 100px threshold) -> should snap back
      fireEvent.pointerDown(dragHandle, { clientY: 100, pointerId: 1 });
      fireEvent.pointerMove(dragHandle, { clientY: 160 });
      expect(dialog.style.transform).toBe('translateY(60px)');

      fireEvent.pointerUp(dragHandle);
      expect(dialog.style.transform).toBe('');
      expect(overlay).not.toHaveClass('modal-overlay--closing');

      // Drag 150px (> 100px threshold) -> should close
      fireEvent.pointerDown(dragHandle, { clientY: 100, pointerId: 1 });
      fireEvent.pointerMove(dragHandle, { clientY: 250 });
      fireEvent.pointerUp(dragHandle);
      expect(overlay).toHaveClass('modal-overlay--closing');
    });
  });

  describe('4. Payment Submission & Route Hash Guard', () => {
    it('does not submit or update store if route :hash param is missing', async () => {
      const { user, onClose } = renderModal(500, vi.fn(), '/no-hash');

      await user.click(screen.getByRole('button', { name: 'Оплатить 525 ₽' }));

      expect(usePaymentStore.getState().paymentResult).toBeNull();
      expect(onClose).not.toHaveBeenCalled();
    });
  });
});
