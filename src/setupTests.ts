import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { useAuthStore, usePaymentStore } from 'src/stores';

if (typeof HTMLElement !== 'undefined' && !HTMLElement.prototype.setPointerCapture) {
  HTMLElement.prototype.setPointerCapture = vi.fn();
}

afterEach(() => {
  cleanup();
  usePaymentStore.getState().clearPaymentResult();
  useAuthStore.getState().logout();
});
