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
  qos: (signal) => request('/api/analytics/qos?limit=1000', signal),
  content: (signal) => request('/api/analytics/content?limit=500', signal),
  devices: (signal) => request('/api/analytics/devices?limit=500', signal),
  usersActivity: (signal) => request('/api/analytics/users?limit=1000', signal),
  users: (signal) => request('/api/users?limit=1000', signal),
  recommendations: (userId, signal) => request(`/api/recommendations/${userId}`, signal),
};