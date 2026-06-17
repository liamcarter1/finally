import { render, screen } from '@testing-library/react';
import PriceFlash from '@/components/PriceFlash';

describe('PriceFlash', () => {
  it('renders the formatted price', () => {
    render(<PriceFlash price={195.5} />);
    expect(screen.getByTestId('price-flash')).toHaveTextContent('195.50');
  });

  it('applies flash-up class when price increases', () => {
    const { rerender } = render(<PriceFlash price={100} />);
    const el = screen.getByTestId('price-flash');
    expect(el.className).not.toMatch(/flash-(up|down)/);

    rerender(<PriceFlash price={101} />);
    expect(screen.getByTestId('price-flash').className).toContain('flash-up');
  });

  it('applies flash-down class when price decreases', () => {
    const { rerender } = render(<PriceFlash price={100} />);
    rerender(<PriceFlash price={99} />);
    expect(screen.getByTestId('price-flash').className).toContain('flash-down');
  });

  it('does not flash when price is unchanged', () => {
    const { rerender } = render(<PriceFlash price={100} />);
    rerender(<PriceFlash price={100} />);
    expect(screen.getByTestId('price-flash').className).not.toMatch(
      /flash-(up|down)/,
    );
  });

  it('renders -- for null price', () => {
    render(<PriceFlash price={null} />);
    expect(screen.getByTestId('price-flash')).toHaveTextContent('--');
  });
});
