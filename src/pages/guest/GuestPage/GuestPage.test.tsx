import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import GuestPage from './GuestPage';
import { SuccessPage } from '../SuccessPage';
import { usePaymentStore } from 'src/stores';

describe('GuestPage Inputs & QA Test Suite', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  const renderGuestPage = async (initialRoute = '/tip/test-hash-123') => {
    const user = userEvent.setup({
      advanceTimers: (ms) => vi.advanceTimersByTime(ms),
    });

    const utils = render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/tip/:hash" element={<GuestPage />} />
          <Route path="/tip/:hash/success" element={<SuccessPage />} />
        </Routes>
      </MemoryRouter>,
    );

    // 500ms initial Loader timeout for GuestPage
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    return { user, ...utils };
  };

  describe('1. Initial State & Loader', () => {
    it('shows the Loader initially and renders the tip input after 500ms', async () => {
      render(
        <MemoryRouter>
          <GuestPage />
        </MemoryRouter>,
      );

      expect(screen.getByRole('status', { name: 'Загрузка' })).toBeInTheDocument();

      await act(async () => {
        vi.advanceTimersByTime(500);
      });

      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });
      expect(tipInput).toBeInTheDocument();
      expect(tipInput).toHaveValue('');
      expect(tipInput).toHaveAttribute('placeholder', '0');

      const payButton = screen.getByRole('button', { name: 'Выберите сумму' });
      expect(payButton).toBeDisabled();
    });
  });

  describe('2. Tip Amount Input - Sanitization, Formatting & Focus', () => {
    it('focuses the tip input when clicking anywhere on .tips-input-wrapper', async () => {
      const { container } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });
      const wrapper = container.querySelector('.tips-input-wrapper')!;

      expect(tipInput).not.toHaveFocus();
      fireEvent.click(wrapper);
      expect(tipInput).toHaveFocus();
    });

    it('strips non-numeric characters (letters, symbols, negative signs, spaces)', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      await user.type(tipInput, '-abc45$0.5₽!');
      expect(tipInput).toHaveValue('4505');
    });

    it('keeps input empty when only non-digits are typed', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      await user.type(tipInput, 'abcdef!@#');
      expect(tipInput).toHaveValue('');
      expect(screen.getByRole('button', { name: 'Выберите сумму' })).toBeDisabled();
    });

    it('enforces maxLength={6} and dynamically adjusts input width in ch units', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      expect(tipInput).toHaveStyle({ width: '1ch' });

      await user.type(tipInput, '123456789');
      // Truncated at 6 characters
      expect(tipInput).toHaveValue('123456');
      expect(tipInput).toHaveStyle({ width: '6ch' });
    });
  });

  describe('3. Tip Amount Input - Boundary Value Analysis (BVA) on Blur', () => {
    it('does NOT show an error when blurring an empty (0 ₽) input', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      await user.click(tipInput);
      await user.tab(); // Triggers onBlur

      expect(screen.queryByText('Минимальная сумма чаевых — 100 ₽')).not.toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
      ).not.toBeInTheDocument();
    });

    it.each(['1', '50', '99'])(
      'shows validation error and keeps form collapsed for invalid boundary %s ₽ (< 100 ₽)',
      async (invalidAmount) => {
        const { user, container } = await renderGuestPage();
        const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

        await user.type(tipInput, invalidAmount);
        await user.tab(); // Triggers onBlur

        expect(screen.getByText('Минимальная сумма чаевых — 100 ₽')).toBeInTheDocument();
        expect(container.querySelector('.tips-input-wrapper')).toHaveClass('error');
        expect(
          screen.queryByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
        ).not.toBeInTheDocument();

        const payButton = screen.getByRole('button', { name: `Оплатить ${invalidAmount} ₽` });
        expect(payButton).toBeDisabled();
      },
    );

    it.each(['100', '101', '5000'])(
      'accepts valid boundary %s ₽ (>= 100 ₽), expands review inputs, and enables Pay button',
      async (validAmount) => {
        const { user, container } = await renderGuestPage();
        const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

        await user.type(tipInput, validAmount);
        await user.tab(); // Triggers onBlur

        expect(screen.queryByText('Минимальная сумма чаевых — 100 ₽')).not.toBeInTheDocument();
        expect(container.querySelector('.tips-input-wrapper')).not.toHaveClass('error');

        // Expanded sections are now visible
        expect(
          screen.getByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
        ).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Напишите пару ласковых слов...')).toBeInTheDocument();

        const payButton = screen.getByRole('button', { name: `Оплатить ${validAmount} ₽` });
        expect(payButton).toBeEnabled();
      },
    );

    it('clears the error message immediately when the user starts typing again', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      await user.type(tipInput, '50');
      await user.tab();
      expect(screen.getByText('Минимальная сумма чаевых — 100 ₽')).toBeInTheDocument();

      // Typing one more digit ('0' -> '500') clears error immediately on change
      await user.type(tipInput, '0');
      expect(screen.queryByText('Минимальная сумма чаевых — 100 ₽')).not.toBeInTheDocument();
      expect(tipInput).toHaveValue('500');
    });

    it('collapses expanded sections if user edits a valid amount down to < 100 ₽ and blurs', async () => {
      const { user } = await renderGuestPage();
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

      await user.type(tipInput, '300');
      await user.tab();
      expect(
        screen.getByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
      ).toBeInTheDocument();

      await user.clear(tipInput);
      await user.type(tipInput, '40');
      await user.tab();

      expect(screen.getByText('Минимальная сумма чаевых — 100 ₽')).toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
      ).not.toBeInTheDocument();
    });
  });

  describe('4. Suggested Tip Preset Chips', () => {
    it.each([300, 500, 700, 1000])(
      'populates input with %i ₽, highlights chip, clears errors, and expands form on click',
      async (preset) => {
        const { user } = await renderGuestPage();
        const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });

        // Trigger error first to verify preset click clears it
        await user.type(tipInput, '20');
        await user.tab();
        expect(screen.getByText('Минимальная сумма чаевых — 100 ₽')).toBeInTheDocument();

        const presetChip = screen.getByText(`${preset} ₽`);
        await user.click(presetChip);

        expect(tipInput).toHaveValue(String(preset));
        expect(presetChip).toHaveClass('selected');
        expect(screen.queryByText('Минимальная сумма чаевых — 100 ₽')).not.toBeInTheDocument();
        expect(
          screen.getByPlaceholderText('Оставьте отзыв о посещении ресторана...'),
        ).toBeInTheDocument();
        expect(screen.getByRole('button', { name: `Оплатить ${preset} ₽` })).toBeEnabled();
      },
    );
  });

  describe('5. Revealed Inputs (Star Rating, Review Textareas & Compliment Chips)', () => {
    it('defaults to 3 active stars and updates active stars when clicking 1 through 5', async () => {
      const { user } = await renderGuestPage();
      await user.click(screen.getByText('500 ₽'));

      const stars = [1, 2, 3, 4, 5].map((n) => screen.getByRole('button', { name: `Оценка ${n}` }));

      // Default rating is 3
      expect(stars[0]).toHaveClass('active');
      expect(stars[1]).toHaveClass('active');
      expect(stars[2]).toHaveClass('active');
      expect(stars[3]).not.toHaveClass('active');
      expect(stars[4]).not.toHaveClass('active');

      // Select 5 stars
      await user.click(stars[4]);
      stars.forEach((star) => expect(star).toHaveClass('active'));

      // Select 1 star
      await user.click(stars[0]);
      expect(stars[0]).toHaveClass('active');
      expect(stars[1]).not.toHaveClass('active');
    });

    it('captures restaurant review text and enforces maxLength={150}', async () => {
      const { user } = await renderGuestPage();
      await user.click(screen.getByText('500 ₽'));

      const restTextarea = screen.getByPlaceholderText('Оставьте отзыв о посещении ресторана...');

      await user.type(restTextarea, 'Отличная кухня и приятная атмосфера!');
      expect(restTextarea).toHaveValue('Отличная кухня и приятная атмосфера!');

      await user.clear(restTextarea);
      const longReview = 'А'.repeat(175);
      await user.type(restTextarea, longReview);
      expect(restTextarea).toHaveValue('А'.repeat(150));
    });

    it('toggles multiple waiter compliment chips on and off', async () => {
      const { user } = await renderGuestPage();
      await user.click(screen.getByText('500 ₽'));

      const chipFast = screen.getByText('Быстро');
      const chipSmile = screen.getByText('Улыбка');

      expect(chipFast).not.toHaveClass('selected');
      expect(chipSmile).not.toHaveClass('selected');

      await user.click(chipFast);
      await user.click(chipSmile);
      expect(chipFast).toHaveClass('selected');
      expect(chipSmile).toHaveClass('selected');

      // Clicking again deselects
      await user.click(chipFast);
      expect(chipFast).not.toHaveClass('selected');
      expect(chipSmile).toHaveClass('selected');
    });

    it('captures waiter compliment textarea input and enforces maxLength={150}', async () => {
      const { user } = await renderGuestPage();
      await user.click(screen.getByText('500 ₽'));

      const waiterTextarea = screen.getByPlaceholderText('Напишите пару ласковых слов...');

      await user.type(waiterTextarea, 'Артем лучший официант!');
      expect(waiterTextarea).toHaveValue('Артем лучший официант!');

      await user.clear(waiterTextarea);
      await user.type(waiterTextarea, 'Б'.repeat(165));
      expect(waiterTextarea).toHaveValue('Б'.repeat(150));
    });
  });

  describe('6. End-to-End Integration: Inputs -> PaymentModal -> Store -> SuccessPage', () => {
    it('passes all entered input states to PaymentModal, updates Zustand store, and navigates to SuccessPage', async () => {
      const { user } = await renderGuestPage('/tip/table-12');

      // 1. Enter custom tip amount
      const tipInput = screen.getByRole('textbox', { name: 'Сумма чаевых в рублях' });
      await user.type(tipInput, '1000');
      await user.tab();

      // 2. Enter restaurant review + select a compliment chip
      const restTextarea = screen.getByPlaceholderText('Оставьте отзыв о посещении ресторана...');
      await user.type(restTextarea, 'Все супер');
      await user.click(screen.getByText('Внимательный'));

      // 3. Open PaymentModal
      await user.click(screen.getByRole('button', { name: 'Оплатить 1000 ₽' }));
      expect(screen.getByRole('dialog')).toBeInTheDocument();

      // 4. Confirm payment (1000 ₽ + 5% fee = 1050 ₽)
      await user.click(screen.getByRole('button', { name: 'Оплатить 1050 ₽' }));

      // 5. Verify Zustand store received accurate flags from our inputs
      const storedResult = usePaymentStore.getState().paymentResult;
      expect(storedResult).toEqual({
        waiterName: 'Артем',
        waiterPhoto: expect.any(String),
        amount: 1000,
        complimentLeft: true,
        restaurantReviewLeft: true,
        goal: {
          name: 'Курсы бариста в Милане',
          collectedAmount: 32000,
          targetAmount: 50000,
        },
      });

      // 6. Verify SuccessPage rendered the submitted data
      expect(screen.getByText('Спасибо!')).toBeInTheDocument();
      expect(screen.getByText('Ваш комплимент уже у него')).toBeInTheDocument();
      expect(screen.getByText('Отзыв ресторану')).toBeInTheDocument();
    });
  });
});
