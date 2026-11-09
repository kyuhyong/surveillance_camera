import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the sign-in page', () => {
  localStorage.clear();
  render(<App />);
  expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
});
