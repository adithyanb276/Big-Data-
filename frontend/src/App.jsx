import { useEffect, useState } from 'react';
import {
  ActivityIcon as Activity, ChartLineIcon as ChartLine, CircleNotchIcon as CircleNotch,
  ClockCounterClockwiseIcon as ClockCounterClockwise, FilmSlateIcon as FilmSlate,
  GaugeIcon as Gauge, HouseIcon as House, ListBulletsIcon as ListBullets,
  PlayCircleIcon as PlayCircle, SealCheckIcon as SealCheck, WaveformIcon as Waveform,
  UsersThreeIcon as UsersThree, WarningCircleIcon as WarningCircle,
} from '@phosphor-icons/react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { api } from './api.js';

const chartColors = ['#d86650', '#708f82', '#d2a34a', '#607d9c'];
const number = (value) => new Intl.NumberFormat('en-US').format(value || 0);
const dateLabel = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString('en', { month: 'short', day: 'numeric' });
};

function useDashboard() {
  const [state, setState] = useState({ loading: true, error: '', data: null });
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState((current) => ({ ...current, loading: true, error: '' }));
    Promise.all([
      api.health(controller.signal), api.overview(controller.signal), api.qos(controller.signal),
      api.content(controller.signal), api.devices(controller.signal), api.usersActivity(controller.signal),
      api.users(controller.signal),
    ]).then(([health, overview, qos, content, devices, activity, users]) => {
      setState({ loading: false, error: '', data: { health, overview, qos, content, devices, activity, users } });
    }).catch((error) => {
      if (error.name !== 'AbortError') setState({ loading: false, error: error.message, data: null });
    });
    return () => controller.abort();
  }, [refresh]);
  return { ...state, reload: () => setRefresh((value) => value + 1) };
}

function Sidebar({ active, onChange, health }) {
  const items = [
    { id: 'overview', label: 'Overview', icon: House },
    { id: 'viewing', label: 'Viewing analytics', icon: ChartLine },
    { id: 'quality', label: 'Stream quality', icon: Gauge },
    { id: 'content', label: 'Content performance', icon: FilmSlate },
  ];
  return <aside className="sidebar">
    <a className="brand" href="#overview" onClick={() => onChange('overview')}>
      <span className="brand-mark"><PlayCircle weight="fill" size={24} /></span>
      <span>stream<span className="brand-light">pulse</span><small>VIEWING INTELLIGENCE</small></span>
    </a>
    <div className="side-label">WORKSPACE</div>
    <nav aria-label="Dashboard sections">
      {items.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-link ${active === id ? 'active' : ''}`} onClick={() => onChange(id)}>
        <Icon size={19} weight={active === id ? 'fill' : 'regular'} />{label}
      </button>)}
    </nav>
    <div className="sidebar-bottom">
      <div className="system-card">
        <div className="system-title"><span className={`status-dot ${health?.data_available ? 'online' : ''}`} /> API STATUS</div>
        <strong>{health?.data_available ? 'Data connected' : 'Waiting for data'}</strong>
        <span>{health?.data_mode || 'local'} environment</span>
      </div>
      <div className="profile"><div className="avatar">SP</div><div><strong>StreamPulse</strong><small>Capstone workspace</small></div><ListBullets size={18} /></div>
    </div>
  </aside>;
}

function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} aria-label="Loading" />;
}

function Metric({ icon: Icon, label, value, suffix, detail, tone, loading }) {
  return <article className="metric">
    <div className="metric-top"><span>{label}</span><span className={`metric-icon ${tone}`}><Icon size={19} weight="duotone" /></span></div>
    {loading ? <Skeleton className="metric-skeleton" /> : <div className="metric-value">{value}{suffix && <small>{suffix}</small>}</div>}
    <div className="metric-detail">{detail}</div>
  </article>;
}

function Panel({ title, subtitle, action, children, className = '' }) {
  return <section className={`panel ${className}`}>
    <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
    {children}
  </section>;
}

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><span>{label}</span>{payload.map((entry) => <strong key={entry.dataKey} style={{ color: entry.color }}>{entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : entry.value}</strong>)}</div>;
}

function ActivityChart({ rows, loading }) {
  if (loading) return <Skeleton className="chart-skeleton" />;
  if (!rows.length) return <EmptyState icon={ChartLine} title="No activity yet" text="Daily activity will appear after the batch pipeline writes Gold data." />;
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={rows} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
    <defs><linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#d86650" stopOpacity={0.23} /><stop offset="100%" stopColor="#d86650" stopOpacity={0.01} /></linearGradient></defs>
    <CartesianGrid vertical={false} stroke="#e6e9e5" strokeDasharray="3 5" />
    <XAxis dataKey="date" tickFormatter={dateLabel} tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <YAxis tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <Tooltip content={<ChartTip />} />
    <Area type="monotone" dataKey="daily_active_users" name="Active users" stroke="#d86650" strokeWidth={2.5} fill="url(#activityFill)" activeDot={{ r: 4, fill: '#d86650', stroke: '#fff', strokeWidth: 2 }} />
  </AreaChart></ResponsiveContainer>;
}

function QosChart({ rows, loading }) {
  if (loading) return <Skeleton className="chart-skeleton" />;
  if (!rows.length) return <EmptyState icon={Waveform} title="No QoS samples" text="Five-minute quality windows will appear after processing." />;
  const normalized = Object.values(rows.reduce((acc, row) => {
    const current = acc[row.window_start] || { window_start: row.window_start, avg_bitrate: 0, rebuffer_ratio: 0, count: 0 };
    current.avg_bitrate += Number(row.avg_bitrate || 0);
    current.rebuffer_ratio += Number(row.rebuffer_ratio || 0);
    current.count += 1;
    acc[row.window_start] = current;
    return acc;
  }, {})).map((row) => ({ ...row, avg_bitrate: row.avg_bitrate / row.count, rebuffer_ratio: row.rebuffer_ratio / row.count, label: new Date(row.window_start).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }) }));
  return <ResponsiveContainer width="100%" height="100%"><LineChart data={normalized} margin={{ top: 10, right: 8, left: -15, bottom: 0 }}>
    <CartesianGrid vertical={false} stroke="#e6e9e5" strokeDasharray="3 5" />
    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <YAxis yAxisId="left" tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <Tooltip content={<ChartTip />} />
    <Line yAxisId="left" type="monotone" dataKey="avg_bitrate" name="Bitrate (Kbps)" stroke="#d2a34a" strokeWidth={2.2} dot={false} />
    <Line yAxisId="right" type="monotone" dataKey="rebuffer_ratio" name="Buffer ratio" stroke="#607d9c" strokeWidth={2.2} dot={false} />
  </LineChart></ResponsiveContainer>;
}

function CompletionChart({ rows, loading }) {
  if (loading) return <Skeleton className="chart-skeleton" />;
  if (!rows.length) return <EmptyState icon={ChartLine} title="No completion windows" text="Completion rates will appear after QoS windows are processed." />;
  const normalized = Object.values(rows.reduce((acc, row) => {
    const current = acc[row.window_start] || { window_start: row.window_start, completion_rate: 0, count: 0 };
    current.completion_rate += Number(row.completion_rate || 0);
    current.count += 1;
    acc[row.window_start] = current;
    return acc;
  }, {})).map((row) => ({ ...row, completion_rate: row.completion_rate / row.count, label: new Date(row.window_start).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }) }));
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={normalized} margin={{ top: 10, right: 8, left: -17, bottom: 0 }}>
    <CartesianGrid vertical={false} stroke="#e6e9e5" strokeDasharray="3 5" />
    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tickLine={false} axisLine={false} tick={{ fill: '#89918d', fontSize: 11 }} />
    <Tooltip content={<ChartTip />} />
    <Bar dataKey="completion_rate" name="Completion rate" fill="#708f82" radius={[3, 3, 0, 0]} maxBarSize={22} />
  </BarChart></ResponsiveContainer>;
}

function DeviceChart({ rows, loading }) {
  if (loading) return <Skeleton className="device-skeleton" />;
  if (!rows.length) return <EmptyState icon={UsersThree} title="No device split" text="Device sessions will be summarized here." />;
  const totals = Object.values(rows.reduce((acc, row) => {
    acc[row.device] = acc[row.device] || { device: row.device, sessions: 0 };
    acc[row.device].sessions += Number(row.sessions || 0);
    return acc;
  }, {}));
  return <div className="device-chart"><ResponsiveContainer width="58%" height={170}><PieChart>
    <Pie data={totals} dataKey="sessions" nameKey="device" innerRadius={53} outerRadius={74} paddingAngle={3} stroke="none">
      {totals.map((entry, index) => <Cell key={entry.device} fill={chartColors[index % chartColors.length]} />)}
    </Pie><Tooltip content={<ChartTip />} />
  </PieChart></ResponsiveContainer><div className="device-legend">{totals.map((item, index) => <div key={item.device}><span style={{ background: chartColors[index % chartColors.length] }} /><span>{item.device}</span><strong>{number(item.sessions)}</strong></div>)}</div></div>;
}

function EmptyState({ icon: Icon, title, text }) {
  return <div className="empty-state"><span><Icon size={22} /></span><strong>{title}</strong><p>{text}</p></div>;
}

function Recommendations({ users, sample }) {
  const [userId, setUserId] = useState('');
  const [result, setResult] = useState({ loading: false, error: '', data: null });
  useEffect(() => {
    if (!users.length) { setUserId(''); return; }
    setUserId((current) => current && users.some((user) => String(user.user_id) === current) ? current : String(users[0].user_id));
  }, [users]);
  useEffect(() => {
    if (!userId) return undefined;
    const controller = new AbortController();
    setResult({ loading: true, error: '', data: null });
    api.recommendations(userId, controller.signal).then((data) => setResult({ loading: false, error: '', data }))
      .catch((error) => { if (error.name !== 'AbortError') setResult({ loading: false, error: error.message, data: null }); });
    return () => controller.abort();
  }, [userId]);
  return <Panel title="For your next watch" subtitle="Precomputed viewing recommendations" action={<label className="select-wrap"><span className="sr-only">Select user</span><select value={userId} onChange={(event) => setUserId(event.target.value)} disabled={!users.length}><option value="">Choose user</option>{users.map((user) => <option key={user.user_id} value={user.user_id}>Viewer {user.user_id}</option>)}</select></label>} className="recommendations-panel">
    {result.loading ? <div className="recommendation-loading"><CircleNotch className="spin" size={22} /> Loading recommendations</div> : null}
    {result.error && <div className="inline-error"><WarningCircle size={18} />{result.error}</div>}
    {!result.loading && !result.error && result.data?.data?.length > 0 && <div className="recommendation-list">{result.data.data.slice(0, 5).map((item, index) => <article className="recommendation" key={`${item.movie_id}-${item.rank}`}>
      <div className="recommend-rank">{String(item.rank || index + 1).padStart(2, '0')}</div>
      <div className="poster" style={{ '--poster-accent': chartColors[index % chartColors.length] }}><FilmSlate size={22} /></div>
      <div className="recommend-copy"><strong>{item.title || `Title ${item.movie_id}`}</strong><span>{item.genre || 'Unclassified'} · {item.recommendation_source === 'popularity' ? 'Popular pick' : 'Personalized'}</span></div>
      <div className="recommend-score"><SealCheck size={16} />{Number(item.score || 0).toFixed(2)}</div>
    </article>)}</div>}
    {!result.loading && !result.error && result.data && !result.data.data.length && <EmptyState icon={FilmSlate} title="No recommendations yet" text="This viewer has no saved recommendation slate. Run the batch recommender to create one." />}
    {!result.loading && !result.error && !result.data && !users.length && <EmptyState icon={UsersThree} title="No viewers available" text="Processed user activity will populate this selector." />}
    <div className="recommendation-footnote">{sample ? 'Sample dataset' : 'Gold output'} · ALS ranking scores are not probabilities; popularity fallback is labeled.</div>
  </Panel>;
}

function ContentTable({ rows, loading }) {
  const [sort, setSort] = useState('views');
  const sorted = [...rows].sort((a, b) => Number(b[sort] || 0) - Number(a[sort] || 0)).slice(0, 8);
  return <Panel title="Content performance" subtitle="Title completion and drop-off" action={<button className="text-button" onClick={() => setSort((current) => current === 'views' ? 'avg_completion' : 'views')}>Sort by {sort === 'views' ? 'completion' : 'views'}</button>}>
    {loading ? <div className="table-loading">{Array.from({ length: 5 }, (_, index) => <Skeleton key={index} />)}</div> : sorted.length ? <div className="table-scroll"><table><thead><tr><th>CONTENT</th><th>VIEWS</th><th>COMPLETION</th><th>DROP-OFF</th></tr></thead><tbody>{sorted.map((row) => <tr key={row.movie_id}><td><span className="table-film"><FilmSlate size={17} />{row.title || `Title ${row.movie_id}`}</span></td><td>{number(row.views)}</td><td><span className="completion-cell"><span><i style={{ width: `${Math.min(100, Math.max(0, row.avg_completion * 100))}%` }} /></span>{(Number(row.avg_completion || 0) * 100).toFixed(0)}%</span></td><td>{(Number(row.drop_off_point || 0) * 100).toFixed(0)}%</td></tr>)}</tbody></table></div> : <EmptyState icon={FilmSlate} title="No content analytics" text="Run the batch pipeline to calculate completion per title." />}
  </Panel>;
}

function App() {
  const { loading, error, data, reload } = useDashboard();
  const [active, setActive] = useState('overview');
  const overview = data?.overview || {};
  const activity = data?.activity?.data || [];
  const qos = data?.qos?.data || [];
  const devices = data?.devices?.data || [];
  const content = data?.content?.data || [];
  const users = data?.users?.data || [];
  const section = (id) => {
    setActive(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return <div className="app-shell">
    <Sidebar active={active} onChange={section} health={data?.health} />
    <main className="main-content">
      <header className="topbar"><div className="breadcrumb">Analytics <span>/</span> <strong>Overview</strong></div><div className="top-actions"><span className="updated"><span className="status-dot online" />{data?.health?.data_available ? 'Pipeline connected' : 'Awaiting Gold data'}</span><button className="refresh-button" onClick={reload} disabled={loading}><ClockCounterClockwise size={17} /> Refresh</button><div className="top-avatar">SP</div></div></header>
      <div className="page-wrap">
        <div className="page-heading"><div><div className="eyebrow">STREAMING INTELLIGENCE <span>·</span> {data?.health?.data_mode || 'LOCAL'} MODE</div><h1>Viewing overview</h1><p>A live view of audience behavior, playback quality, and content performance.</p></div><div className="heading-date"><Activity size={16} /> Last processed batch</div></div>
        {data?.health?.sample_data && <div className="sample-banner"><span className="sample-mark">i</span><span><strong>Sample data</strong> — this dashboard is showing the bundled demonstration dataset.</span></div>}
        {error && <div className="error-banner"><WarningCircle size={19} /><span><strong>Could not load dashboard data.</strong> {error}</span><button onClick={reload}>Retry</button></div>}
        {!loading && !error && !data?.health?.data_available && <div className="empty-banner"><WarningCircle size={18} /><span>Gold analytics are not available. Generate events and run the Spark batch pipeline; this dashboard does not start Spark jobs.</span></div>}
        <div className="metrics-grid" id="overview">
          <Metric icon={Activity} label="Total events" value={number(overview.total_events)} detail="Processed telemetry" tone="coral" loading={loading} />
          <Metric icon={UsersThree} label="Daily active users" value={number(overview.daily_active_users)} detail="Most recent activity date" tone="green" loading={loading} />
          <Metric icon={PlayCircle} label="Completed views" value={number(overview.completed_views)} detail={`${(Number(overview.completion_rate || 0) * 100).toFixed(1)}% average completion`} tone="gold" loading={loading} />
          <Metric icon={Waveform} label="Average buffering" value={number(Math.round(overview.average_buffer_ms || 0))} suffix="ms" detail="Across processed events" tone="blue" loading={loading} />
        </div>
        <div className="primary-grid" id="viewing">
          <div className="chart-stack"><Panel title="Audience activity" subtitle="Daily active viewers" action={<span className="chart-period">BY DAY</span>} className="activity-panel"><div className="large-chart"><ActivityChart rows={activity} loading={loading} /></div></Panel><Panel title="Completion rate" subtitle="Completed events ÷ play events" action={<span className="chart-period">5 MIN</span>}><div className="completion-chart"><CompletionChart rows={qos} loading={loading} /></div></Panel></div>
          <Panel title="Device mix" subtitle="Viewing sessions by device"><DeviceChart rows={devices} loading={loading} /></Panel>
        </div>
        <div className="secondary-grid" id="quality">
          <Panel title="Playback quality" subtitle="Average bitrate and rebuffer ratio across five-minute windows" action={<span className="chart-period">5 MIN</span>}><div className="qos-chart"><QosChart rows={qos} loading={loading} /></div><div className="chart-legend"><span><i className="legend-gold" /> Bitrate (Kbps)</span><span><i className="legend-blue" /> Rebuffer ratio</span></div></Panel>
          <div className="quality-summary"><div className="quality-summary-title"><Gauge size={18} />QUALITY SNAPSHOT</div><div className="quality-stat"><span>Average bitrate</span><strong>{qos.length ? `${Math.round(qos.reduce((sum, row) => sum + Number(row.avg_bitrate || 0), 0) / qos.length)} <small>Kbps</small>` : '—'}</strong><div className="quality-track"><i style={{ width: `${Math.min(100, qos.length ? qos.reduce((sum, row) => sum + Number(row.avg_bitrate || 0), 0) / qos.length / 80 : 0)}%` }} /></div></div><div className="quality-stat"><span>Rebuffer ratio</span><strong>{qos.length ? `${(qos.reduce((sum, row) => sum + Number(row.rebuffer_ratio || 0), 0) / qos.length * 100).toFixed(2)}<small>%</small>` : '—'}</strong><p>Buffer duration ÷ playback duration</p></div><div className="quality-note"><span className="note-icon"><Waveform size={16} /></span><span>Quality metrics use processed event-time windows. Empty values mean no pipeline data is available.</span></div></div>
        </div>
        <div className="bottom-grid" id="content"><ContentTable rows={content} loading={loading} /><Recommendations users={users} sample={Boolean(data?.health?.sample_data)} /></div>
        <footer className="footer"><span>StreamPulse Analytics</span><span>Local-first · Near-real-time micro-batch data</span><span>{data?.health?.data_mode || 'local'} / API</span></footer>
      </div>
    </main>
  </div>;
}

export default App;