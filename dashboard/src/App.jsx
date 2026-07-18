import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertCircle,
  BarChart3,
  Brain,
  CheckCircle2,
  Clock,
  Database,
  Package,
  RefreshCw,
  Search,
  ShoppingCart,
  Store,
  TrendingUp,
  Upload,
  Zap,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from './api'

const AGENT_LABELS = {
  agent1_forecast: 'Agente 1 — Pronóstico',
  agent2_replenishment: 'Agente 2 — Reabastecimiento',
}

function StatusBadge({ status }) {
  const icons = {
    success: CheckCircle2,
    running: RefreshCw,
    error: AlertCircle,
    idle: Clock,
  }
  const Icon = icons[status] || Clock
  return (
    <span className={`badge badge-${status || 'idle'}`}>
      <Icon size={13} className={status === 'running' ? 'spin' : ''} />
      {status || 'idle'}
    </span>
  )
}

function KpiCard({ label, value, sub, icon: Icon, accent, tooltip }) {
  return (
    <div className="kpi-card" title={tooltip} data-accent={accent}>
      <div className="kpi-card__header">
        <span className="kpi-card__label">{label}</span>
        {Icon && (
          <span className="kpi-card__icon">
            <Icon size={20} />
          </span>
        )}
      </div>
      <div className="kpi-card__value">{value ?? '—'}</div>
      {sub && <div className="kpi-card__sub">{sub}</div>}
    </div>
  )
}

function ProgressBar({ label, value, max, color = 'green' }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div className="progress-block">
      <div className="progress-block__header">
        <span>{label}</span>
        <span className="progress-block__pct">{pct}%</span>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-bar__fill progress-bar__fill--${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="progress-block__detail">
        {value?.toLocaleString()} de {max?.toLocaleString()}
      </div>
    </div>
  )
}

export default function App() {
  const [agents, setAgents] = useState([])
  const [kpis, setKpis] = useState(null)
  const [chartData, setChartData] = useState({ historico: [], pronostico: [] })
  const [recommendations, setRecommendations] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState({ forecast: false, replenishment: false, refresh: false })
  const [toast, setToast] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('todas')
  const [lastUpdated, setLastUpdated] = useState(null)

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 4500)
  }

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setLoading((l) => ({ ...l, refresh: true }))
    try {
      const [statusRes, kpiRes, chartRes, recRes, histRes] = await Promise.all([
        api.getStatus(),
        api.getKpis(),
        api.getChart(),
        api.getRecommendations(),
        api.getHistory(),
      ])
      setAgents(statusRes.agents || [])
      setKpis(kpiRes)
      setChartData(chartRes)
      setRecommendations(recRes.recommendations || [])
      setHistory(histRes.history || [])
      setLastUpdated(new Date())
    } catch (e) {
      showToast(`Error al cargar datos: ${e.message}`, 'error')
    } finally {
      if (!silent) setLoading((l) => ({ ...l, refresh: false }))
    }
  }, [])

  useEffect(() => {
    refresh(true)
    const interval = setInterval(() => refresh(true), 15000)
    return () => clearInterval(interval)
  }, [refresh])

  const runForecast = async () => {
    setLoading((l) => ({ ...l, forecast: true }))
    try {
      const res = await api.runForecast()
      showToast(`Pronóstico completado: ${res.summary?.productos_modelados} productos modelados`)
      await refresh(true)
    } catch (e) {
      showToast(e.message, 'error')
    } finally {
      setLoading((l) => ({ ...l, forecast: false }))
    }
  }

  const runReplenishment = async () => {
    setLoading((l) => ({ ...l, replenishment: true }))
    try {
      const res = await api.runReplenishment()
      showToast(`${res.total_recommendations} recomendaciones de abastecimiento generadas`)
      await refresh(true)
    } catch (e) {
      showToast(e.message, 'error')
    } finally {
      setLoading((l) => ({ ...l, replenishment: false }))
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const res = await api.uploadDataset(file)
      showToast(`Dataset cargado: ${res.summary.total_registros.toLocaleString()} registros`)
      await refresh(true)
    } catch (err) {
      showToast(err.message, 'error')
    }
    e.target.value = ''
  }

  const mergedChart = useMemo(
    () => [
      ...chartData.historico.map((d) => ({
        fecha: d.fecha?.slice(5),
        historico: d.demanda,
        pronostico: null,
      })),
      ...chartData.pronostico.map((d) => ({
        fecha: d.fecha?.slice(5),
        historico: null,
        pronostico: d.demanda_pronosticada,
      })),
    ],
    [chartData],
  )

  const filteredRecommendations = useMemo(() => {
    return recommendations.filter((r) => {
      const matchesSearch =
        !searchTerm || r.producto?.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesPriority =
        priorityFilter === 'todas' || r.prioridad === priorityFilter
      return matchesSearch && matchesPriority
    })
  }, [recommendations, searchTerm, priorityFilter])

  const agent1 = agents.find((a) => a.agent === 'agent1_forecast')
  const agent2 = agents.find((a) => a.agent === 'agent2_replenishment')
  const altaCount = kpis?.recomendaciones_alta_prioridad ?? 0
  const totalRecs = kpis?.recomendaciones_total ?? 0

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">
          <img src="/sigi-logo.png" alt="SIGI Retail" className="header__logo" />
          <div>
            <h1>
              SIGI <span className="brand-accent">Retail</span>
            </h1>
            <p>Inventarios inteligentes, decisiones oportunas</p>
          </div>
        </div>
        <div className="header__actions">
          {lastUpdated && (
            <span className="header__updated" title="Última sincronización con el backend">
              <Clock size={14} />
              Actualizado {lastUpdated.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => refresh()}
            disabled={loading.refresh}
          >
            {loading.refresh ? <span className="spinner" /> : <RefreshCw size={16} />}
            <span>Actualizar</span>
          </button>
        </div>
      </header>

      <section className="agents-grid">
        <article className={`agent-card ${agent1?.status === 'running' ? 'agent-card--active' : ''}`}>
          <div className="agent-card__top">
            <div className="agent-card__icon agent-card__icon--forecast">
              <Brain size={22} />
            </div>
            <StatusBadge status={agent1?.status || 'idle'} />
          </div>
          <h3>Agente 1 — Pronóstico de demanda</h3>
          <p className="agent-card__desc">
            Analiza el dataset de ventas, limpia los datos y genera pronósticos con regresión
            lineal (scikit-learn).
          </p>
          <p className="agent-card__message">{agent1?.message || 'Esperando ejecución'}</p>
        </article>

        <article className={`agent-card ${agent2?.status === 'running' ? 'agent-card--active' : ''}`}>
          <div className="agent-card__top">
            <div className="agent-card__icon agent-card__icon--replenishment">
              <Package size={22} />
            </div>
            <StatusBadge status={agent2?.status || 'idle'} />
          </div>
          <h3>Agente 2 — Políticas de reabastecimiento</h3>
          <p className="agent-card__desc">
            Aplica reglas de punto de reorden y genera sugerencias de compra basadas en los
            pronósticos del Agente 1.
          </p>
          <p className="agent-card__message">{agent2?.message || 'Esperando pronósticos'}</p>
        </article>
      </section>

      <section className="actions-bar">
        <button className="btn btn-primary" onClick={runForecast} disabled={loading.forecast}>
          {loading.forecast ? <span className="spinner" /> : <TrendingUp size={18} />}
          <span>Ejecutar pronóstico</span>
        </button>
        <button
          className="btn btn-accent"
          onClick={runReplenishment}
          disabled={loading.replenishment}
        >
          {loading.replenishment ? <span className="spinner" /> : <ShoppingCart size={18} />}
          <span>Generar sugerencias</span>
        </button>
        <label className="btn btn-secondary btn-upload">
          <Upload size={18} />
          <span>Cargar dataset CSV</span>
          <input type="file" accept=".csv" onChange={handleUpload} />
        </label>
      </section>

      {kpis && (
        <section className="kpi-grid">
          <KpiCard
            label="Registros de ventas"
            value={kpis.total_registros?.toLocaleString()}
            icon={Database}
            accent="navy"
            tooltip="Total de transacciones en el dataset activo"
          />
          <KpiCard
            label="Productos únicos"
            value={kpis.productos_unicos}
            icon={Package}
            accent="green"
            tooltip="Productos distintos en el inventario analizado"
          />
          <KpiCard
            label="Tiendas"
            value={kpis.tiendas}
            icon={Store}
            accent="navy"
            tooltip="Puntos de venta incluidos en el análisis"
          />
          <KpiCard
            label="Demanda pronosticada"
            value={kpis.demanda_pronosticada_total?.toLocaleString()}
            sub="Próximos 14 días"
            icon={TrendingUp}
            accent="green"
            tooltip="Unidades totales esperadas según el último pronóstico"
          />
          <KpiCard
            label="Recomendaciones"
            value={kpis.recomendaciones_total}
            sub={`${kpis.recomendaciones_alta_prioridad} de alta prioridad`}
            icon={Zap}
            accent="amber"
            tooltip="Sugerencias de compra generadas por el Agente 2"
          />
          <KpiCard
            label="Unidades a comprar"
            value={kpis.unidades_sugeridas_compra?.toLocaleString()}
            icon={ShoppingCart}
            accent="green"
            tooltip="Suma de cantidades sugeridas en todas las recomendaciones"
          />
        </section>
      )}

      {totalRecs > 0 && (
        <section className="insights-row">
          <div className="card card--compact">
            <h2>Cobertura de prioridad alta</h2>
            <ProgressBar
              label="Recomendaciones urgentes"
              value={altaCount}
              max={totalRecs}
              color="amber"
            />
          </div>
          <div className="card card--compact">
            <h2>Capacidad de abastecimiento</h2>
            <ProgressBar
              label="Unidades sugeridas vs demanda"
              value={kpis?.unidades_sugeridas_compra ?? 0}
              max={kpis?.demanda_pronosticada_total ?? 1}
              color="green"
            />
          </div>
        </section>
      )}

      <section className="grid-2">
        <div className="card">
          <h2>
            <BarChart3 size={20} />
            Demanda histórica vs pronóstico
          </h2>
          {mergedChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={340}>
              <AreaChart data={mergedChart}>
                <defs>
                  <linearGradient id="colorHist" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1B3A5C" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#1B3A5C" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorFc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2D8659" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#2D8659" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="fecha" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="historico"
                  name="Histórico"
                  stroke="#1B3A5C"
                  strokeWidth={2}
                  fill="url(#colorHist)"
                  connectNulls
                />
                <Area
                  type="monotone"
                  dataKey="pronostico"
                  name="Pronóstico"
                  stroke="#2D8659"
                  strokeWidth={2}
                  fill="url(#colorFc)"
                  connectNulls
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <BarChart3 size={40} />
              <p>Ejecute el pronóstico para visualizar la tendencia de demanda</p>
            </div>
          )}
        </div>

        <div className="card">
          <h2>
            <Activity size={20} />
            Historial de ejecuciones
          </h2>
          {history.length > 0 ? (
            <div className="history-list">
              {history.slice(0, 8).map((h) => (
                <div key={h.id} className="history-item">
                  <div className="history-item__header">
                    <strong>{AGENT_LABELS[h.agent] || h.agent}</strong>
                    <StatusBadge status={h.status} />
                  </div>
                  <p>{h.message}</p>
                  <time className="history-item__time">{h.created_at}</time>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Activity size={40} />
              <p>Sin ejecuciones registradas aún</p>
            </div>
          )}
        </div>
      </section>

      <section className="card card--full">
        <div className="card__toolbar">
          <h2>
            <Zap size={20} />
            Recomendaciones de abastecimiento
            {recommendations.length > 0 && (
              <span className="count-badge">{filteredRecommendations.length}</span>
            )}
          </h2>
          <div className="toolbar-controls">
            <div className="search-box">
              <Search size={16} />
              <input
                type="search"
                placeholder="Buscar producto..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <select
              className="filter-select"
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              title="Filtrar por prioridad"
            >
              <option value="todas">Todas las prioridades</option>
              <option value="alta">Alta</option>
              <option value="media">Media</option>
              <option value="baja">Baja</option>
            </select>
          </div>
        </div>

        <div className="table-wrap">
          {filteredRecommendations.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad sugerida</th>
                  <th>Prioridad</th>
                  <th>Comprar antes de</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecommendations.slice(0, 20).map((r, i) => (
                  <tr key={`${r.producto}-${i}`}>
                    <td className="cell-product">{r.producto}</td>
                    <td className="cell-qty">{r.cantidad_sugerida.toLocaleString()} uds.</td>
                    <td>
                      <span className={`priority-tag priority-${r.prioridad}`}>
                        {r.prioridad}
                      </span>
                    </td>
                    <td>{r.fecha_sugerida}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : recommendations.length > 0 ? (
            <div className="empty-state">
              <Search size={40} />
              <p>No hay recomendaciones que coincidan con los filtros aplicados</p>
            </div>
          ) : (
            <div className="empty-state">
              <ShoppingCart size={40} />
              <p>Genere sugerencias después de ejecutar el pronóstico</p>
            </div>
          )}
        </div>
      </section>

      {toast && (
        <div className={`toast toast--${toast.type}`} role="alert">
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toast.msg}</span>
        </div>
      )}
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip__label">{label}</p>
      {payload.map((entry) =>
        entry.value != null ? (
          <p key={entry.dataKey} style={{ color: entry.color }}>
            {entry.name}: <strong>{Number(entry.value).toLocaleString()} uds.</strong>
          </p>
        ) : null,
      )}
    </div>
  )
}
