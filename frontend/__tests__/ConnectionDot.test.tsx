import { render, screen } from '@testing-library/react';
import ConnectionDot from '@/components/ConnectionDot';

describe('ConnectionDot', () => {
  it('renders connected state (green)', () => {
    render(<ConnectionDot status="connected" />);
    const el = screen.getByTestId('connection-status');
    expect(el).toHaveAttribute('data-status', 'connected');
    expect(el).toHaveTextContent('Connected');
    expect(el.querySelector('.bg-up')).toBeTruthy();
  });

  it('renders reconnecting state (yellow)', () => {
    render(<ConnectionDot status="reconnecting" />);
    const el = screen.getByTestId('connection-status');
    expect(el).toHaveAttribute('data-status', 'reconnecting');
    expect(el).toHaveTextContent('Reconnecting');
    expect(el.querySelector('.bg-accent')).toBeTruthy();
  });

  it('renders disconnected state (red)', () => {
    render(<ConnectionDot status="disconnected" />);
    const el = screen.getByTestId('connection-status');
    expect(el).toHaveAttribute('data-status', 'disconnected');
    expect(el).toHaveTextContent('Disconnected');
    expect(el.querySelector('.bg-down')).toBeTruthy();
  });
});
