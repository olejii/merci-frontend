import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';

import LoginPage from './LoginPage';
import { api } from 'src/api/client';

describe('LoginPage Interactive Controls', () => {
  it('navigates to /tip/1 when clicking the navigation button', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/tip/1" element={<div>Tip Page 1</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: 'click to navigate /tip/1' }));
    expect(screen.getByText('Tip Page 1')).toBeInTheDocument();
  });

  it('calls api.v1AuthLoginCreate with test credentials when clicking the API button', async () => {
    const user = userEvent.setup();
    const loginSpy = vi
      .spyOn(api, 'v1AuthLoginCreate')
      .mockResolvedValue({ data: undefined, error: undefined } as never);

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole('button', { name: 'click to toggle API' }));

    expect(loginSpy).toHaveBeenCalledTimes(1);
    expect(loginSpy).toHaveBeenCalledWith({ email: 'a@a.com', password: '123' });

    loginSpy.mockRestore();
  });
});
