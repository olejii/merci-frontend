export type UserRole = 'admin' | 'waiter';

export interface User {
  id: string;
  name: string;
  role: UserRole;
}
