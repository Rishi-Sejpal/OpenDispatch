import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('../lib/auth', () => ({
  login: vi.fn(),
}));

import { login } from '../lib/auth';
import Login from './Login';

async function submitForm(): Promise<void> {
  const form = screen.getByRole('button', { name: /sign in/i }).closest('form');
  if (!form) throw new Error('login form not found');
  fireEvent.submit(form);
}

describe('Login', () => {
  it('renders the sign-in form', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );
    expect(screen.getByText('OpenDispatch')).toBeInTheDocument();
    expect(screen.getByText(/sign in to your dispatch account/i)).toBeInTheDocument();
  });

  it('shows a validation error for an invalid email', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('Email'), 'not-an-email');
    await user.type(screen.getByLabelText('Password'), 'secret');
    await submitForm();

    expect(await screen.findByText('Invalid email')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it('calls login and navigates home on success', async () => {
    vi.mocked(login).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText('Email'), 'a@b.com');
    await user.type(screen.getByLabelText('Password'), 'secret');
    await submitForm();

    await waitFor(() => expect(login).toHaveBeenCalledWith('a@b.com', 'secret'));
    expect(await screen.findByText('Home')).toBeInTheDocument();
  });
});
