import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { Activity, ArrowDownRight, ArrowUpRight, Database, MapPin, RefreshCw, ShieldCheck, CalendarClock } from 'lucide-react'
import { queryUnits } from './data'
import './AnalysisDashboard.css'

type Summary = {
  generated_at: string
  total_capacity_mw: { tech_type: string; status: string; unit_count: number; capacity_mw: number }[]
  weekly_delta: { week: string; tech_type: string; status: string; unit_count: number; delta_units: number; capacity_mw: number; delta_mw: number }[]
  top_municipalities: Municipality[]
  solar_size_distribution: { size_band: string; unit_count: number; capacity_mw: number }[]
  data_quality: {
    total_units: number; exact_coordinate_units: number; municipality_only_units: number; no_location_units: number;
    exact_coordinate_percentage: number; municipality_only_percentage: number;
    by_technology: { tech_type: string; total_units: number; exact_coordinate_units: number; municipality_only_units: number; no_location_units: number; exact_coordinate_percentage: number }[]
  }
  storage_attach_rate_proxy: { solar_unit_count: number; eligible_solar_unit_count: number; matched_solar_unit_count: number; eligible_match_percentage: number; all_solar_match_percentage: number }
}
type Municipality = { municipality_key: string; municipality_name: string; county: string | null; state: string | null; unit_count: number; capacity_mw: number; capacity_density_mw_per_km2: number; tech_mix: { tech_type: string; unit_count: number; capacity_mw: number }[] }
type StatusRow = { tech_type: string; operating: number; planned: number; retired: number }
type ChartDatum = { name: string; capacity: number; units?: number; color: string }

const COLORS: Record<string, string> = {
  Solar: '#2a78d6', Storage: '#eb6834', Wind: '#1baf7a', Biomass: '#eda100', Hydro: '#e87ba4', Thermal: '#008300',
}
const STATUS_ORDER = [
  { key: 'operating', label: 'In Betrieb', color: '#0ca30c' },
  { key: 'planned', label: 'Geplant', color: '#fab219' },
  { key: 'retired', label: 'Stillgelegt', color: '#ec835a' },
]
const MUTED = '#898781'
const EMPTY_SUMMARY: Summary = {
  generated_at: '', total_capacity_mw: [], weekly_delta: [], top_municipalities: [], solar_size_distribution: [],
  data_quality: { total_units: 0, exact_coordinate_units: 0, municipality_only_units: 0, no_location_units: 0, exact_coordinate_percentage: 0, municipality_only_percentage: 0, by_technology: [] },
  storage_attach_rate_proxy: { solar_unit_count: 0, eligible_solar_unit_count: 0, matched_solar_unit_count: 0, eligible_match_percentage: 0, all_solar_match_percentage: 0 },
}

const labels = (t: (key: string) => string): Record<string, string> => ({
  Solar: t('techSolar'), Storage: t('techStorage'), Wind: t('techWind'), Biomass: t('techBiomass'), Hydro: t('techHydro'), Thermal: t('techThermal'),
  Gas: t('techGas'), 'Gas Storage': t('techGasStorage'), Geothermal: t('techGeothermal'), Nuclear: t('techNuclear'),
})

export default function AnalysisDashboard() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage === 'en' ? 'en-US' : 'de-DE'
  const [summary, setSummary] = useState<Summary | null>(null)
  const [statusRows, setStatusRows] = useState<StatusRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const techLabels = useMemo(() => labels(t), [t])
  const numberFormat = useMemo(() => new Intl.NumberFormat(lang), [lang])
  const formatMw = (value: number) => numberFormat.format(Math.round(value))
  const formatCount = (value: number) => numberFormat.format(value)
  const compact = (value: number) => new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 1 }).format(value)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [response, dbRows] = await Promise.all([
          fetch(`${import.meta.env.BASE_URL}data/summary.json`),
          queryUnits(`
            SELECT tech_type,
              COUNT(*) FILTER (WHERE status = 'In Betrieb') AS operating,
              COUNT(*) FILTER (WHERE status = 'Geplant') AS planned,
              COUNT(*) FILTER (WHERE status = 'Stillgelegt') AS retired
            FROM "units.parquet"
            GROUP BY tech_type
            ORDER BY SUM(capacity_mw) DESC
          `),
        ])
        if (!response.ok) throw new Error(`Summary request failed (${response.status})`)
        const summaryData = await response.json() as Summary
        if (!cancelled) {
          setSummary(summaryData)
          setStatusRows(dbRows.map((row) => ({
            tech_type: String(row.tech_type),
            operating: Number(row.operating ?? 0),
            planned: Number(row.planned ?? 0),
            retired: Number(row.retired ?? 0),
          })))
        }
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : t('loadError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [t])

  const data = summary ?? EMPTY_SUMMARY
  const totals = data.total_capacity_mw.reduce<Record<string, { units: number; capacity: number }>>((result, row) => {
    result[row.tech_type] ??= { units: 0, capacity: 0 }
    result[row.tech_type].units += row.unit_count
    result[row.tech_type].capacity += row.capacity_mw
    return result
  }, {})
  const orderedTech = Object.entries(totals).sort((a, b) => b[1].capacity - a[1].capacity)
  const chartTech = orderedTech.slice(0, 5)
  const chartCapacity = chartTech.map(([name, value]) => ({ name: techLabels[name] ?? name, capacity: value.capacity, units: value.units, color: COLORS[name] ?? MUTED }))
  if (orderedTech.length > 5) {
    const other = orderedTech.slice(5).reduce((sum, [, value]) => ({ units: sum.units + value.units, capacity: sum.capacity + value.capacity }), { units: 0, capacity: 0 })
    chartCapacity.push({ name: t('otherTech'), capacity: other.capacity, units: other.units, color: '#c3c2b7' })
  }
  const capacityData: ChartDatum[] = chartCapacity
  const sizeData = data.solar_size_distribution.map((item) => ({
    name: translateSizeBand(item.size_band, t),
    capacity: item.capacity_mw,
    units: item.unit_count,
  }))
  const maxSizeCapacity = Math.max(...sizeData.map((item) => item.capacity)) || 1
    const capacityGrandTotal = capacityData.reduce((sum, item) => sum + item.capacity, 0)
  const solarBandUnitMax = Math.max(...sizeData.map((item) => item.units)) || 1
  const activeHistory = data.weekly_delta.filter((item) => item.week && (item.delta_units !== 0 || item.delta_mw !== 0))
  const historicalWeek = activeHistory[0]?.week
  const historyAvailable = activeHistory.length > 0
  const solarDelta = historyAvailable ? data.weekly_delta.filter((item) => item.tech_type === 'Solar').reduce((sum, item) => sum + item.delta_mw, 0) : null
  const storageUnitsDelta = historyAvailable ? data.weekly_delta.filter((item) => item.tech_type === 'Storage').reduce((sum, item) => sum + item.delta_units, 0) : null

  return (
    <div className="analysis-dashboard">
      <section className="dashboard-head">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />{t('analysisEyebrow')}</div>
          <h1>{t('dashboardTitle')}</h1>
          <p>{t('dashboardIntro')}</p>
        </div>
        <div className="dashboard-updated"><span className="update-dot" />{t('datasetAsOf')}</div>
      </section>

      {error && <div className="dashboard-error" role="status"><RefreshCw size={15} />{t('queryUnavailable')}: {error}</div>}
      {loading && <div className="dashboard-loading" role="status"><span className="loading-spinner" />{t('analysisLoading')}</div>}

      <section className="quality-hero" aria-labelledby="quality-heading">
        <div className="quality-main">
          <div className="quality-icon"><MapPin size={17} /></div>
          <div className="quality-copy">
            <div className="section-kicker">01 <span />{t('dataQualityHeading')}</div>
            <h2 id="quality-heading">{t('qualityLead', { percent: data.data_quality.exact_coordinate_percentage.toFixed(1) })}</h2>
            <p>{t('qualityExplanation', { percent: Math.round(data.data_quality.municipality_only_percentage) })}</p>
          </div>
        </div>
        <div className="quality-stats">
          <div><strong>{formatCount(data.data_quality.exact_coordinate_units)}</strong><span>{t('exactCoordinates')}</span></div>
          <div><strong>{formatCount(data.data_quality.municipality_only_units)}</strong><span>{t('municipalityAggregated')}</span></div>
          <div><strong>{formatCount(data.data_quality.no_location_units)}</strong><span>{t('noLocation')}</span></div>
        </div>
        <div className="coverage-track" role="img" aria-label={`${data.data_quality.exact_coordinate_percentage.toFixed(1)}% ${t('exactCoordinates')}, ${data.data_quality.municipality_only_percentage.toFixed(1)}% ${t('municipalityAggregated')}`}>
          <span className="coverage-exact" style={{ width: `${data.data_quality.exact_coordinate_percentage}%` }} />
          <span className="coverage-municipal" style={{ width: `${data.data_quality.municipality_only_percentage}%` }} />
        </div>
        <div className="coverage-legend"><span><i className="exact-key" />{t('exactCoordinates')}</span><span><i className="municipal-key" />{t('municipalityAggregated')}</span><span><i className="missing-key" />{t('noLocation')}</span></div>
      </section>

      <section className="dashboard-grid quality-section">
        <article className="viz-card quality-breakdown">
          <CardHeading number="02" title={t('coverageByTech')} subtitle={t('coverageByTechIntro')} />
          <div className="viz-table-wrap">
            <table className="viz-table">
              <thead><tr><th>{t('technology')}</th><th>{t('unitCount')}</th><th>{t('exactCoordinate')}</th><th>{t('coverage')}</th></tr></thead>
              <tbody>{data.data_quality.by_technology.map((row) => <tr key={row.tech_type}>
                <th scope="row"><span className="tech-swatch" style={{ backgroundColor: COLORS[row.tech_type] ?? MUTED }} />{techLabels[row.tech_type] ?? row.tech_type}</th>
                <td>{formatCount(row.total_units)}</td>
                <td>{formatCount(row.exact_coordinate_units)}</td>
                <td><div className="coverage-cell"><span className="coverage-mini"><i style={{ width: `${Math.min(100, row.exact_coordinate_percentage)}%` }} /></span><strong>{row.exact_coordinate_percentage.toFixed(1)}%</strong></div></td>
              </tr>)}</tbody>
            </table>
          </div>
        </article>
        <article className="viz-card insight-card">
          <CardHeading number="03" title={t('coordinateInsight')} subtitle={t('coordinateInsightIntro')} />
          <div className="insight-stat"><strong>{data.data_quality.by_technology.find((row) => row.tech_type === 'Wind')?.exact_coordinate_percentage.toFixed(1) ?? '—'}%</strong><span>{t('windCoordinateCoverage')}</span></div>
          <div className="insight-stat muted-insight"><strong>{data.data_quality.by_technology.find((row) => row.tech_type === 'Solar')?.exact_coordinate_percentage.toFixed(1) ?? '—'}%</strong><span>{t('solarCoordinateCoverage')}</span></div>
          <p className="insight-note"><ShieldCheck size={14} />{t('coordinateCaveat')}</p>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="section-intro"><div><div className="section-kicker">04 <span />{t('municipalitySection')}</div><h2>{t('municipalityHeading')}</h2></div><p>{t('municipalityIntro')}</p></div>
        <div className="dashboard-grid municipality-grid">
          <article className="viz-card municipality-table-card">
            <CardHeading number="05" title={t('topMunicipalities')} subtitle={t('topMunicipalitiesIntro')} />
            <div className="viz-table-wrap municipality-scroll">
              <table className="viz-table municipality-table">
                <thead><tr><th>{t('municipality')}</th><th>{t('federalState')}</th><th>{t('capacity')}</th><th>{t('unitCount')}</th><th>{t('leadingTech')}</th></tr></thead>
                <tbody>{data.top_municipalities.slice(0, 20).map((row) => <tr key={row.municipality_key}>
                  <th scope="row"><span className="municipality-name">{row.municipality_name}</span><small>{row.county ?? row.municipality_key}</small></th>
                  <td>{row.state ?? '—'}</td>
                  <td className="numeric-cell">{formatMw(Math.round(row.capacity_mw))} MW</td>
                  <td>{formatCount(row.unit_count)}</td>
                  <td>{leadingMix(row.tech_mix, techLabels)}</td>
                </tr>)}</tbody>
              </table>
            </div>
            <p className="table-note"><Database size={13} />{t('municipalityTableNote')}</p>
          </article>
          <article className="viz-card tech-mix-card">
            <CardHeading number="06" title={t('municipalityMix')} subtitle={t('municipalityMixIntro')} />
            {data.top_municipalities.slice(0, 3).map((municipality) => {
              const mix = municipality.tech_mix.slice().sort((a, b) => b.capacity_mw - a.capacity_mw).slice(0, 3)
              const sum = municipality.tech_mix.reduce((total, item) => total + item.capacity_mw, 0) || 1
              return <div className="mix-row" key={municipality.municipality_key}>
                <div className="mix-row-title"><strong>{municipality.municipality_name}</strong><span>{formatMw(Math.round(municipality.capacity_mw))} MW</span></div>
                <div className="mix-stack" role="img" aria-label={mix.map((item) => `${techLabels[item.tech_type] ?? item.tech_type}: ${Math.round(item.capacity_mw / sum * 100)}%`).join(', ')}>
                  {mix.map((item) => <i key={item.tech_type} style={{ width: `${Math.max(1, item.capacity_mw / sum * 100)}%`, backgroundColor: COLORS[item.tech_type] ?? MUTED }} />)}
                </div>
                <div className="mix-legend">{mix.map((item) => <span key={item.tech_type}><i style={{ backgroundColor: COLORS[item.tech_type] ?? MUTED }} />{techLabels[item.tech_type] ?? item.tech_type} {Math.round(item.capacity_mw / sum * 100)}%</span>)}</div>
              </div>
            })}
          </article>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-intro"><div><div className="section-kicker">07 <span />{t('analysisSection')}</div><h2>{t('analysisSectionTitle')}</h2></div><p>{t('analysisSectionIntro')}</p></div>
        <div className="dashboard-grid charts-grid">
          <article className="viz-card weekly-card">
            <CardHeading number="08" title={t('weeklyDelta')} subtitle={historyAvailable ? t('weeklyCompare', { week: historicalWeek }) : t('weeklyNoBaseline')} />
            {historyAvailable ? <div className="weekly-highlights">
              {activeHistory.filter((item) => item.tech_type === 'Solar').length === 0
                ? <DeltaHighlight icon={<Activity size={17} />} label={t('solarCapacityDelta')} value={t('noBaselineYet')} positive />
                : <DeltaHighlight icon={solarDelta !== null && solarDelta >= 0 ? <ArrowUpRight size={17} /> : <ArrowDownRight size={17} />} label={t('solarCapacityDelta')} value={`${solarDelta !== null && solarDelta >= 0 ? '+' : ''}${formatMw(solarDelta ?? 0)} MW`} positive={(solarDelta ?? 0) >= 0} />}
              {activeHistory.filter((item) => item.tech_type === 'Storage').length === 0
                ? <DeltaHighlight icon={<Activity size={17} />} label={t('storageUnitsDelta')} value={t('noBaselineYet')} positive />
                : <DeltaHighlight icon={(storageUnitsDelta ?? 0) >= 0 ? <ArrowUpRight size={17} /> : <ArrowDownRight size={17} />} label={t('storageUnitsDelta')} value={`${(storageUnitsDelta ?? 0) >= 0 ? '+' : ''}${formatCount(storageUnitsDelta ?? 0)} ${t('unitsShort')}`} positive={(storageUnitsDelta ?? 0) >= 0} />}
            </div> : <div className="no-baseline"><CalendarClock size={19} /><div><strong>{t('weeklyNoBaseline')}</strong><span>{t('weeklyNoBaselineDetail')}</span></div></div>}
            {historyAvailable && <div className="weekly-table-wrap"><table className="viz-table"><thead><tr><th>{t('technology')}</th><th>{t('status')}</th><th>{t('deltaCapacity')}</th><th>{t('deltaUnits')}</th></tr></thead><tbody>{activeHistory.filter((row) => ['Solar', 'Storage', 'Wind', 'Biomass'].includes(row.tech_type)).map((row) => <tr key={`${row.tech_type}-${row.status}`}><th scope="row">{techLabels[row.tech_type] ?? row.tech_type}</th><td>{translateStatus(row.status, t)}</td><td>{row.delta_mw >= 0 ? '+' : ''}{formatMw(row.delta_mw)} MW</td><td>{row.delta_units >= 0 ? '+' : ''}{formatCount(row.delta_units)}</td></tr>)}</tbody></table></div>}
          </article>

          <article className="viz-card donut-card">
            <CardHeading number="09" title={t('capacityMix')} subtitle={t('capacityMixIntro')} />
            <div className="donut-layout">
              <div className="chart-holder donut-holder"><ResponsiveContainer width="100%" height="100%"><PieChart>
                <Pie data={capacityData} dataKey="capacity" nameKey="name" innerRadius="54%" outerRadius="88%" paddingAngle={1.5} stroke="#fcfcfb" strokeWidth={2}>
                  {capacityData.map((item) => <Cell key={item.name} fill={item.color} />)}
                </Pie>
                <Tooltip content={<CapacityTooltip formatValue={formatMw} locale={lang} />} />
              </PieChart></ResponsiveContainer><div className="donut-center"><strong>{formatMw(capacityGrandTotal)}</strong><span>MW</span></div></div>
              <div className="chart-legend">{capacityData.map((item) => <div className="chart-legend-row" key={item.name}><i style={{ backgroundColor: item.color }} /><span>{item.name}</span><strong>{formatMw(item.capacity)}</strong></div>)}</div>
            </div>
          </article>

          <article className="viz-card status-card">
            <CardHeading number="10" title={t('statusBreakdown')} subtitle={t('statusBreakdownIntro')} />
            <div className="chart-holder status-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={statusRows.map((row) => {
              const total = row.operating + row.planned + row.retired || 1
              return { ...row, operating: row.operating / total * 100, planned: row.planned / total * 100, retired: row.retired / total * 100, name: techLabels[row.tech_type] ?? row.tech_type }
            })} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 3 }} barCategoryGap="22%">
              <CartesianGrid horizontal={false} stroke="#e1e0d9" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: MUTED, fontSize: 10 }} axisLine={{ stroke: '#c3c2b7' }} tickLine={false} tickFormatter={(value) => `${value}%`} />
              <YAxis type="category" dataKey="name" width={86} tick={{ fill: '#52514e', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<PercentageTooltip t={t} techLabels={techLabels} />} />
              <Legend formatter={(value) => translateStatus(value, t)} wrapperStyle={{ fontSize: 10, color: '#52514e' }} />
              {STATUS_ORDER.map((status) => <Bar key={status.key} dataKey={status.key} name={status.label} stackId="status" fill={status.color} maxBarSize={20} />)}
            </BarChart></ResponsiveContainer></div>
            <p className="chart-note">{t('statusChartNote')}</p>
          </article>

          <article className="viz-card size-card">
            <CardHeading number="11" title={t('solarSizeDistribution')} subtitle={t('solarSizeDistributionIntro')} />
            <div className="size-chart-layout">
              <div className="size-small-multiples">
                <div className="size-small-chart"><strong>{t('unitCount')}</strong><div className="chart-holder size-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={sizeData} margin={{ top: 6, right: 6, bottom: 28, left: 0 }} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke="#e1e0d9" /><XAxis dataKey="name" interval={0} angle={-16} textAnchor="end" height={45} tick={{ fill: MUTED, fontSize: 8 }} axisLine={{ stroke: '#c3c2b7' }} tickLine={false} />
                  <YAxis domain={[0, solarBandUnitMax * 1.15]} tick={{ fill: MUTED, fontSize: 8 }} axisLine={false} tickLine={false} tickFormatter={compact} width={34} />
                  <Tooltip content={<SizeMeasureTooltip measure="units" formatValue={formatMw} unitsLabel={t('unitsShort')} locale={lang} />} />
                  <Bar dataKey="units" name={t('unitCount')} fill="#eda100" radius={[4, 4, 0, 0]} maxBarSize={36} />
                </BarChart></ResponsiveContainer></div></div>
                <div className="size-small-chart"><strong>{t('capacity')} · MW</strong><div className="chart-holder size-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={sizeData} margin={{ top: 6, right: 6, bottom: 28, left: 0 }} barCategoryGap="28%">
                  <CartesianGrid vertical={false} stroke="#e1e0d9" /><XAxis dataKey="name" interval={0} angle={-16} textAnchor="end" height={45} tick={{ fill: MUTED, fontSize: 8 }} axisLine={{ stroke: '#c3c2b7' }} tickLine={false} />
                  <YAxis domain={[0, maxSizeCapacity * 1.15]} tick={{ fill: MUTED, fontSize: 8 }} axisLine={false} tickLine={false} tickFormatter={compact} width={34} />
                  <Tooltip content={<SizeMeasureTooltip measure="capacity" formatValue={formatMw} unitsLabel={t('unitsShort')} locale={lang} />} />
                  <Bar dataKey="capacity" name={`${t('capacity')} · MW`} fill="#2a78d6" radius={[4, 4, 0, 0]} maxBarSize={36} />
                </BarChart></ResponsiveContainer></div></div>
              </div>
              <div className="size-data-table-wrap"><table className="size-data-table"><thead><tr><th>{t('sizeBand')}</th><th>{t('unitCount')}</th><th>{t('capacity')}</th></tr></thead><tbody>{sizeData.map((item) => <tr key={item.name}><th scope="row">{item.name}</th><td>{formatCount(item.units)}</td><td>{formatMw(item.capacity)} MW</td></tr>)}</tbody></table></div>
            </div>
            <div className="size-insight"><span className="insight-mark" /><p>{t('solarSizeInsight', { percent: Math.round((data.solar_size_distribution.filter((item) => item.size_band === '< 10 kW').reduce((sum, item) => sum + item.unit_count, 0) / Math.max(1, data.solar_size_distribution.reduce((sum, item) => sum + item.unit_count, 0))) * 100), largePercent: Math.round((data.solar_size_distribution.filter((item) => item.size_band === '≥ 1 MW').reduce((sum, item) => sum + item.capacity_mw, 0) / Math.max(1, data.solar_size_distribution.reduce((sum, item) => sum + item.capacity_mw, 0))) * 100) })}</p></div>
          </article>

          <article className="viz-card attach-card">
            <CardHeading number="12" title={t('storageAttachRate')} subtitle={t('storageAttachIntro')} />
            <div className="attach-number">{data.storage_attach_rate_proxy.eligible_match_percentage.toFixed(1)}<span>%</span></div>
            <p className="attach-label">{t('storageAttachEligible')}</p>
            <div className="attach-track"><i style={{ width: `${Math.min(100, data.storage_attach_rate_proxy.eligible_match_percentage)}%` }} /></div>
            <div className="attach-foot"><span>{formatCount(data.storage_attach_rate_proxy.matched_solar_unit_count)} {t('matchedSolar')}</span><span>{formatCount(data.storage_attach_rate_proxy.eligible_solar_unit_count)} {t('eligibleSolar')}</span></div>
            <p className="proxy-caveat">{t('storageAttachCaveat')}</p>
          </article>
        </div>
      </section>

      <section className="dashboard-section">
        <div className="section-intro"><div><div className="section-kicker">13 <span />{t('dataTableSection')}</div><h2>{t('dataTableTitle')}</h2></div><p>{t('dataTableIntro')}</p></div>
        <div className="viz-card full-table-card">
          <div className="viz-table-wrap municipality-scroll"><table className="viz-table municipality-table">
            <thead><tr><th>{t('municipality')}</th><th>{t('federalState')}</th><th>{t('capacity')}</th><th>{t('unitCount')}</th><th>{t('leadingTech')}</th></tr></thead>
            <tbody>{data.top_municipalities.slice(0, 100).map((row) => <tr key={row.municipality_key}><th scope="row"><span className="municipality-name">{row.municipality_name}</span><small>{row.municipality_key}</small></th><td>{row.state ?? '—'}</td><td className="numeric-cell">{formatMw(Math.round(row.capacity_mw))} MW</td><td>{formatCount(row.unit_count)}</td><td>{leadingMix(row.tech_mix, techLabels)}</td></tr>)}</tbody>
          </table></div>
        </div>
      </section>

      <div className="dashboard-source-note"><Database size={14} /><span>{t('dashboardSourceNote')}</span></div>
    </div>
  )
}

function CardHeading({ number, title, subtitle }: { number: string; title: string; subtitle: string }) {
  return <div className="viz-card-heading"><div className="section-kicker">{number} <span />{title}</div><p>{subtitle}</p></div>
}

function DeltaHighlight({ icon, label, value, positive }: { icon: React.ReactNode; label: string; value: string; positive: boolean }) {
  return <div className={`delta-highlight ${positive ? 'delta-positive' : 'delta-negative'}`}><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></div>
}

function CapacityTooltip({ active, payload, formatValue, locale }: { active?: boolean; payload?: { payload?: ChartDatum }[]; formatValue: (value: number) => string; locale: string }) {
  if (!active || !payload?.length || !payload[0].payload) return null
  const item = payload[0].payload
  return <div className="chart-tooltip"><strong>{formatValue(item.capacity)}</strong><span>{item.name}</span><small>{item.units === undefined ? '' : `${new Intl.NumberFormat(locale).format(item.units)} units`}</small></div>
}

function SizeMeasureTooltip({ active, payload, measure, formatValue, unitsLabel, locale }: { active?: boolean; payload?: { payload?: { name: string; capacity: number; units: number } }[]; measure: 'capacity' | 'units'; formatValue: (value: number) => string; unitsLabel: string; locale: string }) {
  if (!active || !payload?.length || !payload[0].payload) return null
  const item = payload[0].payload
  return <div className="chart-tooltip"><strong>{measure === 'capacity' ? `${formatValue(item.capacity)} MW` : `${new Intl.NumberFormat(locale).format(item.units)} ${unitsLabel}`}</strong><span>{item.name}</span><small>{measure === 'capacity' ? `${new Intl.NumberFormat(locale).format(item.units)} ${unitsLabel}` : `${formatValue(item.capacity)} MW`}</small></div>
}

function PercentageTooltip({ active, payload, label, t, techLabels }: { active?: boolean; payload?: { name?: string; value?: number; color?: string }[]; label?: string; t: (key: string) => string; techLabels: Record<string, string> }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tooltip"><strong>{label}</strong>{payload.map((item) => <span key={item.name}><i style={{ background: item.color }} />{translateStatus(item.name ?? '', t)}: {(item.value ?? 0).toFixed(1)}%</span>)}<small>{t('statusDenominator')}: {techLabels[label ?? ''] ?? label}</small></div>
}

function translateSizeBand(value: string, t: (key: string) => string) {
  const keys: Record<string, string> = { '< 10 kW': 'sizeUnder10', '10–100 kW': 'size10to100', '100 kW–1 MW': 'size100to1000', '≥ 1 MW': 'sizeOver1mw' }
  return t(keys[value] ?? value)
}

function translateStatus(value: string, t: (key: string) => string) {
  const keys: Record<string, string> = { 'In Betrieb': 'statusOperating', Geplant: 'statusPlanned', Stillgelegt: 'statusRetired' }
  return keys[value] ? t(keys[value]) : value
}

function leadingMix(mix: Municipality['tech_mix'], techLabels: Record<string, string>) {
  const item = mix.slice().sort((a, b) => b.capacity_mw - a.capacity_mw)[0]
  if (!item) return '—'
  const total = mix.reduce((sum, entry) => sum + entry.capacity_mw, 0) || 1
  return `${techLabels[item.tech_type] ?? item.tech_type} ${Math.round(item.capacity_mw / total * 100)}%`
}
