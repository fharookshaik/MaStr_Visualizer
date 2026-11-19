import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Activity, Database, FilterX, Info, MapPinned, RotateCcw, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { queryUnits } from './data'
import MapView, { type UnitDetails } from './MapView'
import './MapExplorer.css'

type FilterOptions = { tech: string[]; status: string[]; state: string[] }
type Summary = { data_quality: { total_units: number; exact_coordinate_units: number; municipality_only_units: number }; total_capacity_mw: { capacity_mw: number }[] }
type Metrics = { units: number; capacity: number }

const EMPTY_OPTIONS: FilterOptions = { tech: [], status: [], state: [] }
const EMPTY_METRICS: Metrics = { units: 0, capacity: 0 }
const TECH_COLORS: Record<string, string> = { Solar: '#eda100', Wind: '#2a78d6', Biomass: '#008300', Storage: '#6250d6', Hydro: '#1baf7a', Thermal: '#eb6834', Gas: '#e87ba4', Geothermal: '#e87ba4', Nuclear: '#6250d6', 'Gas Storage': '#1baf7a' }
const TECH_STROKES: Record<string, string> = { Solar: '#805600', Wind: '#184f95', Biomass: '#005a00', Storage: '#40318f', Hydro: '#08794f', Thermal: '#9e3e1b', Gas: '#98365c', Geothermal: '#98365c', Nuclear: '#40318f', 'Gas Storage': '#08794f' }
const EMPTY_SUMMARY: Summary = { data_quality: { total_units: 0, exact_coordinate_units: 0, municipality_only_units: 0 }, total_capacity_mw: [] }

function sqlLiteral(value: string) {
  return `'${value.replaceAll("'", "''")}'`
}

export default function MapExplorer() {
  const { t, i18n } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [options, setOptions] = useState<FilterOptions>(EMPTY_OPTIONS)
  const [metrics, setMetrics] = useState<Metrics>(EMPTY_METRICS)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [queryError, setQueryError] = useState<string | null>(null)
  const [selectedUnit, setSelectedUnit] = useState<UnitDetails | null>(null)
  const tech = searchParams.get('tech') ?? ''
  const status = searchParams.get('status') ?? ''
  const state = searchParams.get('state') ?? ''

  const where = useMemo(() => {
    const clauses = ['TRUE']
    if (tech) clauses.push(`tech_type = ${sqlLiteral(tech)}`)
    if (status) clauses.push(`status = ${sqlLiteral(status)}`)
    if (state) clauses.push(`state = ${sqlLiteral(state)}`)
    return clauses.join(' AND ')
  }, [tech, status, state])

  useEffect(() => {
    let cancelled = false
    async function initialize() {
      setLoading(true)
      setQueryError(null)
      try {
        const [techRows, statusRows, stateRows, response] = await Promise.all([
          queryUnits('SELECT DISTINCT tech_type AS value FROM "units.parquet" WHERE tech_type IS NOT NULL ORDER BY value'),
          queryUnits('SELECT DISTINCT status AS value FROM "units.parquet" WHERE status IS NOT NULL ORDER BY value'),
          queryUnits('SELECT DISTINCT state AS value FROM "units.parquet" WHERE state IS NOT NULL ORDER BY value'),
          fetch(`${import.meta.env.BASE_URL}data/summary.json`),
        ])
        if (!response.ok) throw new Error(`Summary request failed (${response.status})`)
        const summaryData = await response.json() as Summary
        if (!cancelled) {
          setOptions({
            tech: techRows.map((row) => String(row.value)),
            status: statusRows.map((row) => String(row.value)),
            state: stateRows.map((row) => String(row.value)),
          })
          setSummary(summaryData)
        }
      } catch (error) {
        if (!cancelled) setQueryError(error instanceof Error ? error.message : t('loadError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void initialize()
    return () => { cancelled = true }
  }, [t])

  useEffect(() => {
    let cancelled = false
    async function refreshMetrics() {
      try {
        const rows = await queryUnits(`SELECT COUNT(*) AS units, COALESCE(SUM(capacity_mw), 0) AS capacity FROM "units.parquet" WHERE lat IS NOT NULL AND lon IS NOT NULL AND ${where}`)
        if (!cancelled && rows[0]) {
          setMetrics({ units: Number(rows[0].units ?? 0), capacity: Number(rows[0].capacity ?? 0) })
        }
      } catch (error) {
        if (!cancelled) setQueryError(error instanceof Error ? error.message : t('loadError'))
      }
    }
    void refreshMetrics()
    return () => { cancelled = true }
  }, [where, t])

  const updateFilter = useCallback((key: 'tech' | 'status' | 'state', value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }, [searchParams, setSearchParams])

  const resetFilters = useCallback(() => setSearchParams({}, { replace: true }), [setSearchParams])
  const hasFilters = Boolean(tech || status || state)
  const exactUnits = summary?.data_quality.exact_coordinate_units ?? 0
  const municipalityUnits = summary?.data_quality.municipality_only_units ?? 0
  const totalCapacity = (summary ?? EMPTY_SUMMARY).total_capacity_mw.reduce((sum, item) => sum + (item.capacity_mw || 0), 0)
  const numberFormat = useMemo(() => new Intl.NumberFormat(i18n.resolvedLanguage === 'en' ? 'en-US' : 'de-DE'), [i18n.resolvedLanguage])

  return (
    <section className="explorer" aria-label={t('explorerTitle')}>
      <aside className="explorer-sidebar">
        <div className="sidebar-heading">
          <div className="sidebar-kicker"><span className="sidebar-kicker-dot" />{t('explorerEyebrow')}</div>
          <h1>{t('explorerTitle')}</h1>
          <p>{t('explorerIntro')}</p>
        </div>

        <div className="dataset-summary">
          <div className="dataset-summary-top"><Database size={15} /><span>{t('datasetLabel')}</span><span className="dataset-status">{t('liveData')}</span></div>
          <div className="coordinate-counts">
            <div><strong>{numberFormat.format(exactUnits)}</strong><span>{t('unitsWithCoordinates')}</span></div>
            <div><strong>{numberFormat.format(municipalityUnits)}</strong><span>{t('unitsMunicipalityOnly')}</span></div>
          </div>
          <div className="coordinate-info-row"><Info size={13} /><span>{t('mapVisibilityLabel')}</span><span className="coordinate-info-tip" tabIndex={0} aria-label={t('coordinateTooltip')}><Info size={13} /><span role="tooltip">{t('coordinateTooltip')} <a href="/data-quality">{t('dataQualityNav')}</a></span></span></div>
          <div className="dataset-capacity"><Activity size={13} /><span>{t('installedCapacity')}</span><strong>{numberFormat.format(Math.round(totalCapacity))} MW</strong></div>
        </div>

        <div className="filter-title-row">
          <div className="filter-heading"><MapPinned size={15} /><h2>{t('filterTitle')}</h2></div>
          {hasFilters && <button className="reset-filters" type="button" onClick={resetFilters}><RotateCcw size={12} />{t('resetFilters')}</button>}
        </div>

        <div className="filter-fields">
          <label className="filter-field">
            <span>{t('technology')}</span>
            <select value={tech} onChange={(event) => updateFilter('tech', event.target.value)} disabled={loading}>
              <option value="">{t('allTechnologies')}</option>
              {options.tech.map((item) => <option key={item} value={item}>{translateTech(item, t)}</option>)}
            </select>
          </label>
          <label className="filter-field">
            <span>{t('operatingStatus')}</span>
            <select value={status} onChange={(event) => updateFilter('status', event.target.value)} disabled={loading}>
              <option value="">{t('allStatuses')}</option>
              {options.status.map((item) => <option key={item} value={item}>{translateStatus(item, t)}</option>)}
            </select>
          </label>
          <label className="filter-field">
            <span>{t('federalState')}</span>
            <select value={state} onChange={(event) => updateFilter('state', event.target.value)} disabled={loading}>
              <option value="">{t('allStates')}</option>
              {options.state.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>

        <div className="filter-result" aria-live="polite">
          <div className="filter-result-icon"><FilterX size={15} /></div>
          <div><strong>{numberFormat.format(metrics.units)}</strong><span>{t(hasFilters ? 'matchingUnits' : 'visibleCoordinateUnits')}</span></div>
          {hasFilters && <span className="result-capacity">{numberFormat.format(Math.round(metrics.capacity))} MW</span>}
        </div>

        {queryError && <p className="query-error" role="status">{t('queryUnavailable')}: {queryError}</p>}
        <div className="sidebar-footnote">{t('mapHint')} <span>·</span> {t('dataUpdated')}</div>
      </aside>

      <div className="explorer-map-wrap">
        <div className="map-topbar">
          <div className="map-location"><span className="map-location-dot" /><strong>{t('germany')}</strong><span>{t('mapSubtitle')}</span></div>
          <div className="map-legend" aria-label={t('mapLegend')}>
            {['Solar', 'Wind', 'Biomass', 'Storage', 'Hydro', 'Thermal', 'Gas', 'Geothermal', 'Nuclear', 'Gas Storage'].map((type) => <span key={type}><i className="legend-swatch" style={{ backgroundColor: TECH_COLORS[type], borderColor: TECH_STROKES[type] }} />{translateTech(type, t)}</span>)}
          </div>
        </div>
        <div className="explorer-map"><MapView tech={tech} status={status} state={state} onUnitSelect={setSelectedUnit} />
        {selectedUnit && <aside className="unit-detail-panel" aria-labelledby="unit-detail-heading">
        <div className="detail-panel-heading"><div><span className="detail-kicker">{t('unitDetailLabel')}</span><h2 id="unit-detail-heading">{selectedUnit.mastr_id}</h2></div><button type="button" className="detail-close" aria-label={t('closeDetail')} onClick={() => setSelectedUnit(null)}><X size={17} /></button></div>
        <dl className="unit-detail-list">
          <div><dt>{t('technology')}</dt><dd>{translateTech(selectedUnit.tech_type, t)}</dd></div>
          <div><dt>{t('capacity')}</dt><dd>{selectedUnit.capacity_mw == null ? '—' : `${numberFormat.format(selectedUnit.capacity_mw)} MW`}</dd></div>
          <div><dt>{t('municipality')}</dt><dd>{selectedUnit.municipality_name || '—'}</dd></div>
          <div><dt>{t('operatingStatus')}</dt><dd>{translateStatus(selectedUnit.status, t)}</dd></div>
          <div><dt>{t('federalState')}</dt><dd>{selectedUnit.state || '—'}</dd></div>
        </dl>
        </aside>}
        </div>
        <div className="map-bottomline"><span>{t('mapAttribution')}</span><span>{t('coordinateNote')}</span></div>
      </div>
    </section>
  )
}

function translateTech(value: string, t: (key: string) => string) {
  const keys: Record<string, string> = {
    Biomass: 'techBiomass', Gas: 'techGas', 'Gas Storage': 'techGasStorage', Geothermal: 'techGeothermal',
    Hydro: 'techHydro', Nuclear: 'techNuclear', Solar: 'techSolar', Storage: 'techStorage', Thermal: 'techThermal', Wind: 'techWind',
  }
  return keys[value] ? t(keys[value]) : value
}

function translateStatus(value: string, t: (key: string) => string) {
  const keys: Record<string, string> = { 'In Betrieb': 'statusOperating', Geplant: 'statusPlanned', Stillgelegt: 'statusRetired' }
  return keys[value] ? t(keys[value]) : value
}
