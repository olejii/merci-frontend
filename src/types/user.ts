export type UserRole = 'admin' | 'waiter';

export interface User {
  id: number;
  name: string;
  role: UserRole;
}
