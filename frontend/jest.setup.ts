import '@testing-library/jest-dom';

// jsdom does not implement ResizeObserver, which Recharts' ResponsiveContainer
// relies on. Provide a no-op stub.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(global as { ResizeObserver?: unknown }).ResizeObserver =
  (global as { ResizeObserver?: unknown }).ResizeObserver || ResizeObserverStub;
