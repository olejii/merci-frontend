import { create } from 'zustand';

export interface PaymentResult {
  waiterName: string;
  waiterPhoto: string;
  amount: number;

  goal: {
    name: string;
    collectedAmount: number;
    targetAmount: number;
  } | null;

  complimentLeft: boolean;
  restaurantReviewLeft: boolean;
}

interface PaymentStore {
  paymentResult: PaymentResult | null;
  setPaymentResult: (result: PaymentResult) => void;
  clearPaymentResult: () => void;
}

const usePaymentStore = create<PaymentStore>((set) => ({
  paymentResult: null,

  setPaymentResult: (result) => set({ paymentResult: result }),

  clearPaymentResult: () => set({ paymentResult: null }),
}));

export default usePaymentStore;
