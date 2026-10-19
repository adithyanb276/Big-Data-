import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App.jsx';

const emptyTable = () => ({ data: [], count: 0, data_available: false, sample_data: false });
const initialRoutes = {
  '/api/health': { status: 'degraded', data_available: false, data_mode: 'local', sample_data: false, available_tables: [] },
  '/api/overview': { total_events: 0, total_sessions: 0, daily_active_users: 0, completed_views: 0, completion_rate: 0, average_buffer_ms: 0, data_available: false, sample_data: false },
  '/api/analytics/qos?limit=1000': emptyTable(),
  '/api/analytics/content?limit=500': emptyTable(),
  '/api/analytics/devices?limit=500': emptyTable(),
  '/api/analytics/users?limit=1000': emptyTable(),
  '/api/users?limit=1000': emptyTable(),
};

function mockFetch(routeOverrides = {}) {
  const routes = { ...initialRoutes, ...routeOverrides };
  global.fetch = vi.fn(async (url) => {
    const parsed = new URL(url, 'http://localhost');
    const path = parsed.pathname + parsed.search;
    const basePath = parsed.pathname;
    const payload = routes[path] ?? routes[basePath] ?? (basePath.startsWith('/api/recommendations/') ? { user_id: 0, status: 'unavailable', ...emptyTable() } : undefined);
    if (!payload) return new Response('Not found', { status: 404 });
    return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  return global.fetch;
}

describe('StreamPulse analytics dashboard', () => {
  beforeEach(() => mockFetch());
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it('shows truthful empty-data overview and renders every analytics view', async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('Gold data is not available.')).toBeInTheDocument();
    expect(screen.getByText('No activity in this period')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'QoS analytics' }));
    expect(screen.getByRole('heading', { name: 'Stream quality' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Content' }));
    expect(screen.getByRole('heading', { name: 'Content performance' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'User activity' }));
    expect(screen.getByText(/not individual user histories/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Recommendations' }));
    expect(screen.getByText('No users available')).toBeInTheDocument();
  });

  it('sends supported date and device filters to QoS and device endpoints', async () => {
    const fetchMock = mockFetch({
      '/api/analytics/devices': { data: [{ date: '2026-01-03', device: 'web', sessions: 5, distribution: 1 }], count: 1, data_available: true, sample_data: false },
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('Gold data is not available.');
    const fromInput = screen.getByLabelText('FROM');
    const toInput = screen.getByLabelText('TO');
    await user.type(fromInput, '2026-01-02');
    await user.type(toInput, '2026-01-08');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('start_date=2026-01-02'), expect.anything()));
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('end_date=2026-01-08'), expect.anything());
    const deviceSelect = screen.getByLabelText('DEVICE');
    await user.selectOptions(deviceSelect, 'web');
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('device=web'), expect.anything()));
  });

  it('labels popularity fallback and displays actual recommendation fields', async () => {
    mockFetch({
      '/api/users?limit=1000': { data: [{ user_id: 8 }], count: 1, data_available: true, sample_data: false },
      '/api/recommendations/8': { user_id: 8, status: 'popularity_fallback', data: [{ user_id: 8, rank: 1, movie_id: 25, title: 'Northern Lights', genre: 'Drama', score: 1, recommendation_source: 'popularity' }], count: 1, data_available: true, sample_data: false },
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: 'Recommendations' }));
    expect(await screen.findByText('Popularity fallback.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Northern Lights' })).toBeInTheDocument();
    expect(screen.getByText('POPULARITY')).toBeInTheDocument();
  });

  it('shows retryable error state when backend is unavailable', async () => {
    global.fetch = vi.fn(async () => new Response('offline', { status: 503 }));
    render(<App />);
    expect(await screen.findByText('Data request failed.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});