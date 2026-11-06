import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { User } from 'src/types';

interface AuthStore {
  user: User | null;

  login: (user: User) => void;
  logout: () => void;
}

const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,

      login: (user) => set({ user }),

      logout: () => set({ user: null }),
    }),
    {
      name: 'auth-storage',
    },
  ),
);

export default useAuthStore;
