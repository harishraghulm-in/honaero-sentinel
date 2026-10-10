import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';


const queryClient = new QueryClient();

describe('App', () => {
  it('renders the main UI components', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
    expect(screen.getByText('HONAERO SENTINEL')).toBeDefined();
  });
});
