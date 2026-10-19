const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function request(path, signal) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json' },
    signal,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }
  return response.json();
}

export const api = {
  health: (signal) => request('/api/health', signal),
  overview: (signal) => request('/api/overview', signal),
  qos: ({ device, startDate, endDate } = {}, signal) => {
    const params = new URLSearchParams({ limit: '1000' });
    if (device && device !== 'all') params.set('device', device);
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return request(`/api/analytics/qos?${params}`, signal);
  },
  content: (signal) => request('/api/analytics/content?limit=500', signal),
  devices: ({ startDate, endDate } = {}, signal) => {
    const params = new URLSearchParams({ limit: '500' });
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return request(`/api/analytics/devices?${params}`, signal);
  },
  usersActivity: (signal) => request('/api/analytics/users?limit=1000', signal),
  users: (signal) => request('/api/users?limit=1000', signal),
  recommendations: (userId, signal) => request(`/api/recommendations/${userId}`, signal),
};