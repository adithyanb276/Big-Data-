import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIcon as Activity, ArrowClockwiseIcon as ArrowClockwise,
  ArrowDownIcon as ArrowDown, ArrowUpIcon as ArrowUp,
  ChartLineUpIcon as ChartLineUp, CheckCircleIcon as CheckCircle,
  FilmSlateIcon as FilmSlate, GaugeIcon as Gauge, HouseIcon as House,
  ListBulletsIcon as ListBullets, PlayCircleIcon as PlayCircle,
  UsersThreeIcon as UsersThree, WarningCircleIcon as WarningCircle,
  WaveformIcon as Waveform,
} from '@phosphor-icons/react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api } from './api.js';

const PAGES = [
  { id: 'overview', label: 'Overview', icon: House },
  { id: 'qos', label: 'QoS analytics', icon: Gauge },
  { id: 'content', label: 'Content', icon: FilmSlate },
  { id: 'users', label: 'User activity', icon: UsersThree },
  { id: 'recommendations', label: 'Recommendations', icon: PlayCircle },
];
const DEVICE_COLORS = ['#dd634f', '#517a70', '#c69a4c', '#657f9a', '#8c79a3', '#b57b61'];
const fmt = (value) => new Intl.NumberFormat('en-US').format(Number(value) || 0);
const pct = (value, digits = 0) => `${((Number(value) || 0) * 100).toFixed(digits)}%`;
const formatDate = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value || '') : date.toLocaleDateString('en', { month: 'short', day: 'numeric' });
};

function useDashboard(filters, reloadKey) {
  const [state, setState] = useState({ loading: true, errors: {}, data: {} });
  useEffect(() => {
    const controller = new AbortController();
    setState((old) => ({ ...old, loading: true, errors: {} }));
    const requests = {
      health: () => api.health(controller.signal),
      overview: () => api.overview(controller.signal),
      qos: () => api.qos(filters, controller.signal),
      content: () => api.content(controller.signal),
      devices: () => api.devices(filters, controller.signal),
      activity: () => api.usersActivity(controller.signal),
      users: () => api.users(controller.signal),
    };
    Promise.all(Object.entries(requests).map(async ([key, request]) => {
      try { return [key, await request(), null]; }
      catch (error) {
        if (error.name === 'AbortError') throw error;
        return [key, null, error.message || 'Could not load this dataset.'];
      }
    })).then((results) => {
      const data = {};
      const errors = {};
      for (const [key, value, error] of results) {
        if (error) errors[key] = error;
        else data[key] = value;
      }
      setState({ loading: false, errors, data });
    }).catch((error) => {
      if (error.name !== 'AbortError') setState({ loading: false, errors: { dashboard: error.message }, data: {} });
    });
    return () => controller.abort();
  }, [filters.device, filters.startDate, filters.endDate, reloadKey]);
  return state;
}

function useRecommendations(userId, reloadKey) {
  const [state, setState] = useState({ loading: false, error: '', result: null });
  useEffect(() => {
    if (userId === '') {
      setState({ loading: false, error: '', result: null });
      return undefined;
    }
    const controller = new AbortController();
    setState({ loading: true, error: '', result: null });
    api.recommendations(userId, controller.signal)
      .then((result) => setState({ loading: false, error: '', result }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ loading: false, error: error.message || 'Unable to load recommendations.', result: null });
      });
    return () => controller.abort();
  }, [userId, reloadKey]);
  return state;
}

function Sidebar({ page, onNavigate, health }) {
  return <aside className="sidebar">
    <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); onNavigate('overview'); }} aria-label="StreamPulse overview">
      <span className="brand-symbol"><PlayCircle size={21} weight="fill" /></span>
      <span className="brand-name">stream<span>pulse</span><small>VIDEO INTELLIGENCE</small></span>
    </a>
    <div className="workspace-label">WORKSPACE</div>
    <nav className="side-nav" aria-label="Analytics sections">
      {PAGES.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'selected' : ''}`} aria-current={page === id ? 'page' : undefined} onClick={() => onNavigate(id)}>
        <Icon size={19} weight={page === id ? 'fill' : 'regular'} /><span>{label}</span>{page === id && <i />}
      </button>)}
    </nav>
    <div className="sidebar-bottom">
      <div className="pipeline-status">
        <div className="pipeline-label"><span className={`signal-dot ${health?.data_available ? 'ready' : ''}`} /> DATA PIPELINE</div>
        <strong>{health?.data_available ? 'Gold data available' : 'Awaiting Gold data'}</strong>
        <span>{health?.data_mode || 'local'} environment</span>
      </div>
      <div className="workspace-profile"><div className="profile-monogram">SP</div><div><strong>StreamPulse</strong><span>Capstone workspace</span></div><ListBullets size={17} /></div>
    </div>
  </aside>;
}

function Header({ health, onRefresh, loading, filter, setFilter, devices, page }) {
  const title = PAGES.find((item) => item.id === page)?.label || 'Overview';
  return <header className="topbar">
    <div className="breadcrumbs"><span>Analytics</span><i>/</i><strong>{title}</strong></div>
    <div className="topbar-tools"><span className="connection-state"><i className={`signal-dot ${health?.status === 'ok' ? 'ready' : ''}`} />{health?.status === 'ok' ? 'Connected' : 'Data pending'}</span><button className="icon-button refresh-button" onClick={onRefresh} disabled={loading} title="Refresh data" aria-label="Refresh data"><ArrowClockwise size={17} /></button><span className="profile-monogram top-monogram">SP</span></div>
    {['overview', 'qos'].includes(page) && <div className="toolbar-filters" aria-label="QoS and device filters">
      <label className="filter-control"><span>FROM</span><input type="date" value={filter.startDate} max={filter.endDate || undefined} onChange={(event) => setFilter((old) => ({ ...old, startDate: event.target.value }))} /></label>
      <label className="filter-control"><span>TO</span><input type="date" value={filter.endDate} min={filter.startDate || undefined} onChange={(event) => setFilter((old) => ({ ...old, endDate: event.target.value }))} /></label>
      <label className="filter-control device-filter"><span>DEVICE</span><select value={filter.device} onChange={(event) => setFilter((old) => ({ ...old, device: event.target.value }))}><option value="all">All devices</option>{devices.map((device) => <option key={device} value={device}>{device}</option>)}</select></label>
      {(filter.startDate || filter.endDate || filter.device !== 'all') && <button className="clear-filters" onClick={() => setFilter({ startDate: '', endDate: '', device: 'all' })}>Clear</button>}
    </div>}
  </header>;
}

function PageIntro({ eyebrow, title, description, action }) {
  return <div className="page-intro"><div><span className="page-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function Panel({ title, subtitle, action, className = '', children }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}

function EmptyState({ icon: Icon = Activity, title, message, compact = false }) {
  return <div className={`empty-state ${compact ? 'compact' : ''}`}><span className="empty-icon"><Icon size={21} /></span><strong>{title}</strong><p>{message}</p></div>;
}

function DataError({ message, retry }) {
  return <div className="error-state" role="alert"><WarningCircle size={19} /><span><strong>Data request failed.</strong> {message}</span>{retry && <button onClick={retry}>Retry</button>}</div>;
}

function Skeleton({ className = '' }) { return <div className={`skeleton ${className}`} aria-label="Loading data" />; }

function Metric({ icon: Icon, label, value, note, loading, accent }) {
  return <article className="metric"><div className="metric-label">{label}<span className={`metric-icon ${accent}`}><Icon size={18} weight="duotone" /></span></div>{loading ? <Skeleton className="metric-value-skeleton" /> : <strong className="metric-value">{value}</strong>}<span className="metric-note">{note}</span></article>;
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><span>{label}</span>{payload.map((entry) => <strong key={entry.dataKey} style={{ color: entry.color }}>{entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : entry.value}</strong>)}</div>;
}

function ActivityChart({ rows, loading }) {
  if (loading) return <Skeleton className="chart-placeholder" />;
  if (!rows.length) return <EmptyState title="No activity in this period" message="Daily active users will appear after the processing batch writes Gold data." />;
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={rows} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
    <defs><linearGradient id="audienceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#da604c" stopOpacity={0.22} /><stop offset="100%" stopColor="#da604c" stopOpacity={0} /></linearGradient></defs>
    <CartesianGrid vertical={false} stroke="#e8e9e8" strokeDasharray="3 5" /><XAxis dataKey="date" tickFormatter={formatDate} tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} /><YAxis tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} /><Tooltip content={<ChartTooltip />} />
    <Area type="monotone" dataKey="daily_active_users" name="Daily active users" stroke="#d65d49" strokeWidth={2.4} fill="url(#audienceFill)" activeDot={{ r: 4, stroke: '#fff', strokeWidth: 2 }} />
  </AreaChart></ResponsiveContainer>;
}

function QosChart({ rows, loading, metric = 'bitrate' }) {
  if (loading) return <Skeleton className="chart-placeholder" />;
  if (!rows.length) return <EmptyState icon={Waveform} title="No quality samples" message="QoS windows will show after Spark processing writes Gold data." />;
  const buckets = Object.values(rows.reduce((acc, row) => {
    const key = row.window_start;
    const value = acc[key] || { window_start: key, avg_bitrate: 0, rebuffer_ratio: 0, completion_rate: 0, count: 0 };
    value.avg_bitrate += Number(row.avg_bitrate || 0);
    value.rebuffer_ratio += Number(row.rebuffer_ratio || 0);
    value.completion_rate += Number(row.completion_rate || 0);
    value.count += 1;
    acc[key] = value;
    return acc;
  }, {})).map((row) => ({ ...row, avg_bitrate: row.avg_bitrate / row.count, rebuffer_ratio: row.rebuffer_ratio / row.count, completion_rate: row.completion_rate / row.count, time: new Date(row.window_start).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }) }));
  const isCompletion = metric === 'completion';
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={buckets} margin={{ top: 12, right: 13, left: -13, bottom: 0 }}>
    <CartesianGrid vertical={false} stroke="#e8e9e8" strokeDasharray="3 5" /><XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} /><YAxis yAxisId="left" domain={isCompletion ? [0, 1] : ['auto', 'auto']} tickFormatter={isCompletion ? pct : undefined} tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} />
    {!isCompletion && <YAxis yAxisId="right" orientation="right" tickFormatter={pct} tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} />}
    <Tooltip content={<ChartTooltip />} />
    {isCompletion ? <Line yAxisId="left" type="monotone" dataKey="completion_rate" name="Completion rate" stroke="#517a70" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} /> : <><Line yAxisId="left" type="monotone" dataKey="avg_bitrate" name="Bitrate (Kbps)" stroke="#d65d49" strokeWidth={2.4} dot={false} activeDot={{ r: 4 }} /><Line yAxisId="right" type="monotone" dataKey="rebuffer_ratio" name="Rebuffer ratio" stroke="#617e98" strokeWidth={2.2} dot={false} activeDot={{ r: 4 }} /></>}
  </LineChart></ResponsiveContainer>;
}

function DeviceChart({ rows, loading }) {
  if (loading) return <Skeleton className="device-placeholder" />;
  if (!rows.length) return <EmptyState icon={UsersThree} title="No device breakdown" message="Session distribution will appear after processing." compact />;
  const totals = Object.values(rows.reduce((acc, row) => {
    const current = acc[row.device] || { device: row.device, sessions: 0 };
    current.sessions += Number(row.sessions || 0);
    acc[row.device] = current;
    return acc;
  }, {}));
  return <div className="device-visual"><ResponsiveContainer width="58%" height={190}><PieChart><Pie data={totals} dataKey="sessions" nameKey="device" innerRadius={57} outerRadius={83} paddingAngle={3} stroke="none">{totals.map((row, index) => <Cell key={row.device} fill={DEVICE_COLORS[index % DEVICE_COLORS.length]} />)}</Pie><Tooltip content={<ChartTooltip />} /></PieChart></ResponsiveContainer><div className="device-legend">{totals.map((row, index) => <div key={row.device}><i style={{ backgroundColor: DEVICE_COLORS[index % DEVICE_COLORS.length] }} /><span>{row.device}</span><strong>{fmt(row.sessions)}</strong></div>)}</div></div>;
}

function KpiGroup({ overview, loading }) {
  return <div className="metrics-grid"><Metric icon={Activity} label="Total events" value={fmt(overview.total_events)} note="Processed telemetry" loading={loading} accent="accent-red" /><Metric icon={UsersThree} label="Daily active users" value={fmt(overview.daily_active_users)} note="Most recent available date" loading={loading} accent="accent-green" /><Metric icon={PlayCircle} label="Completed views" value={fmt(overview.completed_views)} note={`${pct(overview.completion_rate, 1)} session completion`} loading={loading} accent="accent-gold" /><Metric icon={Waveform} label="Average buffering" value={`${fmt(Math.round(overview.average_buffer_ms))} ms`} note="Mean buffer duration per event" loading={loading} accent="accent-blue" /></div>;
}

function ContentTable({ rows, loading, pageSize = 8 }) {
  const [sort, setSort] = useState({ field: 'views', direction: 'desc' });
  const sorted = useMemo(() => [...rows].sort((a, b) => {
    const result = Number(a[sort.field] || 0) - Number(b[sort.field] || 0);
    return sort.direction === 'desc' ? -result : result;
  }).slice(0, pageSize), [rows, sort, pageSize]);
  const toggleSort = (field) => setSort((old) => ({ field, direction: old.field === field && old.direction === 'desc' ? 'asc' : 'desc' }));
  if (loading) return <div className="table-skeleton">{Array.from({ length: 6 }, (_, index) => <Skeleton key={index} />)}</div>;
  if (!rows.length) return <EmptyState icon={FilmSlate} title="No content data yet" message="The table will fill with actual views, completion, and drop-off when Gold output is available." />;
  const SortMark = ({ field }) => sort.field === field ? (sort.direction === 'desc' ? <ArrowDown size={12} /> : <ArrowUp size={12} />) : null;
  return <div className="table-scroll"><table className="content-table"><thead><tr><th>CONTENT</th><th><button onClick={() => toggleSort('views')}>VIEWS <SortMark field="views" /></button></th><th><button onClick={() => toggleSort('avg_completion')}>COMPLETION <SortMark field="avg_completion" /></button></th><th>DROP-OFF</th></tr></thead><tbody>{sorted.map((row, index) => <tr key={row.movie_id}><td><span className="content-cell"><span className="content-index">{String(index + 1).padStart(2, '0')}</span><span className="content-poster"><FilmSlate size={18} /></span><span><strong>{row.title || `Title ${row.movie_id}`}</strong><small>{row.genre || `Movie ${row.movie_id}`}</small></span></span></td><td>{fmt(row.views)}</td><td><span className="completion-data"><span className="mini-bar"><i style={{ width: `${Math.max(0, Math.min(100, Number(row.avg_completion || 0) * 100))}%` }} /></span>{pct(row.avg_completion)}</span></td><td>{pct(row.drop_off_point)}</td></tr>)}</tbody></table></div>;
}

function OverviewView({ data, errors, loading, retry }) {
  const overview = data.overview || {};
  const activity = data.activity?.data || [];
  const qos = data.qos?.data || [];
  const devices = data.devices?.data || [];
  const content = data.content?.data || [];
  return <>
    <PageIntro eyebrow="OVERVIEW / STREAMING INTELLIGENCE" title="Audience overview" description="A clear view of viewing activity, playback quality, and content engagement." />
    {errors.overview && <DataError message={errors.overview} retry={retry} />}
    {!loading && !overview.data_available && <div className="data-notice"><span className="notice-point" /><span><strong>Gold data is not available.</strong> Generate and process a batch to populate these analytics. Nothing here is simulated.</span></div>}
    {data.health?.sample_data && <div className="sample-note">Sample data · This dataset is labeled by the backend.</div>}
    <KpiGroup overview={overview} loading={loading} />
    <div className="overview-grid"><Panel title="Audience activity" subtitle="Daily active users" action={<span className="period-chip">DAILY</span>}><div className="chart-area"><ActivityChart rows={activity} loading={loading} /></div></Panel><Panel title="Device mix" subtitle="Session share by playback device"><DeviceChart rows={devices} loading={loading} /></Panel></div>
    <div className="overview-grid lower-overview"><Panel title="Completion rate" subtitle="Completed events divided by play events" action={<span className="period-chip">5-MIN WINDOWS</span>}><div className="chart-area compact-chart"><QosChart rows={qos} metric="completion" loading={loading} /></div></Panel><Panel title="Content leaders" subtitle="Ranked by observed views" action={<span className="text-action">TOP TITLES</span>}><ContentTable rows={content} loading={loading} pageSize={5} /></Panel></div>
  </>;
}

function QosTable({ rows, loading }) {
  if (loading) return <div className="table-skeleton">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} />)}</div>;
  if (!rows.length) return <EmptyState icon={Gauge} title="No QoS windows" message="Adjust the supported filters or wait for Gold output." compact />;
  return <div className="table-scroll"><table><thead><tr><th>WINDOW</th><th>DEVICE</th><th>RATE</th><th>BUFFER</th><th>BITRATE</th></tr></thead><tbody>{rows.slice(0, 12).map((row, index) => <tr key={`${row.window_start}-${row.device}-${index}`}><td>{new Date(row.window_start).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td><td className="capitalize">{row.device}</td><td>{pct(row.completion_rate)}</td><td>{pct(row.rebuffer_ratio, 2)}</td><td>{fmt(row.avg_bitrate)} Kbps</td></tr>)}</tbody></table></div>;
}

function QosView({ rows, loading, error, retry, devices }) {
  const avgBitrate = rows.length ? rows.reduce((sum, row) => sum + Number(row.avg_bitrate || 0), 0) / rows.length : null;
  const avgRebuffer = rows.length ? rows.reduce((sum, row) => sum + Number(row.rebuffer_ratio || 0), 0) / rows.length : null;
  const avgCompletion = rows.length ? rows.reduce((sum, row) => sum + Number(row.completion_rate || 0), 0) / rows.length : null;
  return <><PageIntro eyebrow="PLAYBACK / QUALITY OF SERVICE" title="Stream quality" description="Inspect bitrate, rebuffer ratio, and completion over processed five-minute windows." /><div className="metric-strip"><div><span>AVG. BITRATE</span><strong>{avgBitrate === null ? '—' : <>{Math.round(avgBitrate).toLocaleString()} <small>Kbps</small></>}</strong></div><div><span>REBUFFER RATIO</span><strong>{avgRebuffer === null ? '—' : pct(avgRebuffer, 2)}</strong></div><div><span>COMPLETION RATE</span><strong>{avgCompletion === null ? '—' : pct(avgCompletion, 1)}</strong></div><div><span>WINDOWS</span><strong>{loading ? '…' : fmt(rows.length)}</strong></div></div>
    {error && <DataError message={error} retry={retry} />}
    <div className="single-view-grid"><Panel title="Bitrate & rebuffering" subtitle="Window means across returned devices"><div className="chart-area tall-chart"><QosChart rows={rows} loading={loading} /></div><div className="chart-key"><span><i className="key-red" /> Bitrate (Kbps)</span><span><i className="key-blue" /> Rebuffer ratio</span></div></Panel><Panel title="QoS window detail" subtitle="Metrics are computed in the Spark batch pipeline"><QosTable rows={rows} loading={loading} /></Panel></div>
    <p className="metric-definition"><strong>Metric note.</strong> Rebuffer ratio = summed buffer milliseconds ÷ summed duration milliseconds. Completion rate = complete events ÷ play events. Bitrate is in Kbps. Device and date filters are sent only to the supported QoS endpoint.</p><div className="available-devices"><span>DEVICES IN RESULT</span>{devices.map((device) => <span key={device} className="device-tag">{device}</span>)}{!devices.length && <small>None in the selected result.</small>}</div>
  </>;
}

function ContentView({ rows, loading, error, retry }) {
  const totalViews = rows.reduce((sum, row) => sum + Number(row.views || 0), 0);
  const completion = rows.length ? rows.reduce((sum, row) => sum + Number(row.avg_completion || 0), 0) / rows.length : null;
  const top = [...rows].sort((a, b) => Number(b.views || 0) - Number(a.views || 0)).slice(0, 6);
  return <><PageIntro eyebrow="CATALOGUE / ENGAGEMENT" title="Content performance" description="Compare observed views, session completion, and average drop-off by title." />{error && <DataError message={error} retry={retry} />}
    <div className="metric-strip content-strip"><div><span>TITLES WITH ACTIVITY</span><strong>{loading ? '…' : fmt(rows.length)}</strong></div><div><span>TOTAL OBSERVED VIEWS</span><strong>{loading ? '…' : fmt(totalViews)}</strong></div><div><span>MEAN TITLE COMPLETION</span><strong>{completion === null ? '—' : pct(completion, 1)}</strong></div></div>
    <Panel title="Most-viewed titles" subtitle="Title names use catalogue metadata when available; otherwise the movie ID is shown." action={<span className="period-chip">VIEWS / COMPLETION</span>}><ContentTable rows={rows} loading={loading} pageSize={30} /></Panel>
    <Panel title="Relative view volume" subtitle="Top six titles by observed view count" className="content-chart-panel">{loading ? <Skeleton className="chart-placeholder" /> : top.length ? <ResponsiveContainer width="100%" height={230}><BarChart data={top} layout="vertical" margin={{ left: 10, right: 18, top: 4, bottom: 4 }}><CartesianGrid horizontal={false} stroke="#e8e9e8" strokeDasharray="3 5" /><XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: '#87908f', fontSize: 11 }} /><YAxis type="category" dataKey={(row) => row.title || `Title ${row.movie_id}`} width={150} tickLine={false} axisLine={false} tick={{ fill: '#586360', fontSize: 11 }} /><Tooltip content={<ChartTooltip />} /><Bar dataKey="views" name="Views" fill="#d65d49" radius={[0, 4, 4, 0]} maxBarSize={19} /></BarChart></ResponsiveContainer> : <EmptyState icon={FilmSlate} title="No title rows" message="The content table will populate from Gold output." />}</Panel>
  </>;
}

function DailyActivityTable({ rows, loading }) {
  if (loading) return <div className="table-skeleton">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} />)}</div>;
  if (!rows.length) return <EmptyState icon={UsersThree} title="No user activity" message="The DAU series will appear after Gold analytics are written." compact />;
  return <div className="table-scroll"><table><thead><tr><th>DATE</th><th>DAILY ACTIVE USERS</th></tr></thead><tbody>{rows.map((row) => <tr key={row.date}><td>{new Date(row.date).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })}</td><td>{fmt(row.daily_active_users)}</td></tr>)}</tbody></table></div>;
}

function UsersView({ rows, loading, error, retry }) {
  const sorted = [...rows].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const activeTotal = rows.reduce((sum, row) => sum + Number(row.daily_active_users || 0), 0);
  const peak = rows.reduce((best, row) => Math.max(best, Number(row.daily_active_users || 0)), 0);
  return <><PageIntro eyebrow="AUDIENCE / DAILY ACTIVITY" title="User activity" description="Explore daily active-user counts from the published Gold activity series." />
    <div className="scope-note"><UsersThree size={18} /><span>The current API exposes daily active users, not individual user histories or session-level profiles. This view stays within that contract.</span></div>
    {error && <DataError message={error} retry={retry} />}
    <div className="metric-strip"><div><span>DATES AVAILABLE</span><strong>{loading ? '…' : fmt(rows.length)}</strong></div><div><span>SUM OF DAILY ACTIVE COUNTS</span><strong>{loading ? '…' : fmt(activeTotal)}</strong></div><div><span>PEAK DAILY USERS</span><strong>{loading ? '…' : rows.length ? fmt(peak) : '—'}</strong></div></div>
    <Panel title="Daily active users" subtitle="Distinct active users by event date"><div className="chart-area tall-chart"><ActivityChart rows={sorted} loading={loading} /></div></Panel>
    <Panel title="Daily activity records" subtitle="Rows returned by `/api/analytics/users`"><DailyActivityTable rows={sorted} loading={loading} /></Panel>
  </>;
}

function RecommendationsView({ users, loadingUsers, errorUsers, userId, setUserId, recState, retry }) {
  const result = recState.result;
  const recommendations = result?.data || [];
  const fallback = result?.status === 'popularity_fallback';
  return <><PageIntro eyebrow="PERSONALIZATION / PRECOMPUTED SLATES" title="Recommendations" description="Inspect the saved ranking for a selected viewer. Model training remains an offline batch task." />
    <div className="recommendation-controls"><label htmlFor="viewer-select">VIEWER</label><select id="viewer-select" value={userId} onChange={(event) => setUserId(event.target.value)} disabled={loadingUsers || !users.length}><option value="">Select a user</option>{users.map((user) => <option key={user.user_id} value={user.user_id}>Viewer {user.user_id}</option>)}</select><span className="control-hint">User IDs come from `/api/users`.</span></div>
    {errorUsers && <DataError message={errorUsers} retry={retry} />}{recState.error && <DataError message={recState.error} retry={retry} />}
    {fallback && <div className="fallback-note"><CheckCircle size={18} /><span><strong>Popularity fallback.</strong> No viewer-specific slate was found; these titles are ranked from observed Gold view counts.</span></div>}
    {recState.loading && <div className="recommendation-grid">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} className="recommendation-skeleton" />)}</div>}
    {!recState.loading && !recState.error && recommendations.length > 0 && <div className="recommendation-grid">{recommendations.map((row, index) => <article className="recommendation-card" key={`${row.movie_id}-${row.rank}`}><div className={`rec-art art-${index % 5}`}><span className="rec-rank">{String(row.rank).padStart(2, '0')}</span><FilmSlate size={30} weight="light" /><span className="rec-art-id">CONTENT {String(row.movie_id).padStart(4, '0')}</span></div><div className="rec-card-body"><div className="rec-card-top"><span>{row.recommendation_source === 'popularity' ? 'POPULARITY' : 'ALS RANKING'}</span><strong>{Number(row.score || 0).toFixed(3)}</strong></div><h3>{row.title || `Title ${row.movie_id}`}</h3><p>{row.genre || `Movie ${row.movie_id}`}</p></div></article>)}</div>}
    {!recState.loading && !recState.error && result && recommendations.length === 0 && <Panel title="No recommendations available"><EmptyState icon={PlayCircle} title="No slate for this viewer" message="There is no saved recommendation row or content view data to construct a popularity fallback." /></Panel>}
    {!loadingUsers && !users.length && !errorUsers && !recState.loading && !result && <Panel title="Waiting for user data"><EmptyState icon={UsersThree} title="No users available" message="The recommendation selector populates from processed Gold user IDs." /></Panel>}
    <p className="recommendation-disclaimer">Scores are ranking strengths, not probabilities. Popularity and ALS scores use different scales.</p>
  </>;
}

function App() {
  const [page, setPage] = useState('overview');
  const [filter, setFilter] = useState({ startDate: '', endDate: '', device: 'all' });
  const [reloadKey, setReloadKey] = useState(0);
  const [userId, setUserId] = useState('');
  const { loading, errors, data } = useDashboard(filter, reloadKey);
  const userRows = data.users?.data || [];
  const activityRows = data.activity?.data || [];
  const deviceOptions = [...new Set((data.devices?.data || []).map((row) => row.device).filter(Boolean))].sort();
  const recommendation = useRecommendations(userId, reloadKey);
  const retry = () => setReloadKey((value) => value + 1);

  useEffect(() => {
    if (!userRows.length) { setUserId(''); return; }
    setUserId((current) => current && userRows.some((row) => String(row.user_id) === current) ? current : String(userRows[0].user_id));
  }, [userRows]);

  return <div className="dashboard-shell">
    <Sidebar page={page} onNavigate={setPage} health={data.health} />
    <main className="main-area">
      <Header health={data.health} onRefresh={retry} loading={loading} filter={filter} setFilter={setFilter} devices={deviceOptions} page={page} />
      <div className="content-wrap">
        {page === 'overview' && <OverviewView data={data} errors={errors} loading={loading} retry={retry} />}
        {page === 'qos' && <QosView rows={data.qos?.data || []} loading={loading} error={errors.qos} retry={retry} devices={deviceOptions} />}
        {page === 'content' && <ContentView rows={data.content?.data || []} loading={loading} error={errors.content} retry={retry} />}
        {page === 'users' && <UsersView rows={activityRows} loading={loading} error={errors.activity} retry={retry} />}
        {page === 'recommendations' && <RecommendationsView users={userRows} loadingUsers={loading} errorUsers={errors.users} userId={userId} setUserId={setUserId} recState={recommendation} retry={retry} />}
        <footer className="page-footer"><span><strong>StreamPulse</strong> · Local-first video analytics</span><span>{data.health?.data_mode || 'local'} <i /> {data.health?.available_tables?.length || 0} Gold tables online</span></footer>
      </div>
    </main>
  </div>;
}

export default App;