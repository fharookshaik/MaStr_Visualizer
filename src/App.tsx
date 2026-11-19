import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Globe2, Leaf, MapPin, Zap } from 'lucide-react'
import './App.css'
import MapView from './MapView'

type OverviewSummary = {
  data_quality: { total_units: number; exact_coordinate_units: number; exact_coordinate_percentage: number }
  total_capacity_mw: { tech_type: string; unit_count: number; capacity_mw: number | null }[]
}
const EMPTY_OVERVIEW_SUMMARY: OverviewSummary = { data_quality: { total_units: 0, exact_coordinate_units: 0, exact_coordinate_percentage: 0 }, total_capacity_mw: [] }

const MapExplorer = lazy(() => import('./MapExplorer'))
const AnalysisDashboard = lazy(() => import('./AnalysisDashboard'))

function AppShell() {
  const { t, i18n } = useTranslation()
  const isEnglish = i18n.resolvedLanguage === 'en'

  function toggleLanguage() {
    void i18n.changeLanguage(isEnglish ? 'de' : 'en')
  }

  return (
    <main className="min-h-screen bg-paper text-forest">
      <header className="site-header">
        <NavLink className="brand" to="/" aria-label={t('appName')}>
          <span className="brand-mark"><Leaf size={17} strokeWidth={2.2} /></span>
          <span className="brand-name">MaStR<span>.</span></span>
        </NavLink>
        <nav className="main-nav" aria-label={t('navLabel')}>
          <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('home')}</NavLink>
          <NavLink to="/analysis" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('analysis')}</NavLink>
          <NavLink to="/data-quality" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('dataQualityNav')}</NavLink>
          <NavLink to="/map" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>{t('exploreMap')}</NavLink>
        </nav>
        <button className="language-button" type="button" onClick={toggleLanguage} aria-label={t('languageLabel')}>
          <Globe2 size={16} />
          <span>{isEnglish ? 'EN' : 'DE'}</span>
          <span className="language-chevron">⌄</span>
        </button>
      </header>

      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/analysis" element={<Suspense fallback={<div className="route-loading">{t('analysisLoading')}</div>}><AnalysisDashboard /></Suspense>} />
        <Route path="/data-quality" element={<Suspense fallback={<div className="route-loading">{t('analysisLoading')}</div>}><AnalysisDashboard /></Suspense>} />
        <Route path="/map" element={<Suspense fallback={<div className="route-loading">{t('analysisLoading')}</div>}><MapExplorer /></Suspense>} />
      </Routes>

      <footer className="site-footer">
        <span>{t('appName')} <span className="footer-dot">·</span> Open data, clearer energy</span>
        <span className="footer-source"><strong>{t('sourcesAndLicense')}</strong><span>{t('bundesnetzagentur')}</span><span>{t('licenseAttribution')}</span><a href="https://www.govdata.de/dl-de/by-2-0" target="_blank" rel="noreferrer">{t('openLicense')}</a></span>
      </footer>
    </main>
  )
}

function Overview() {
  const { t, i18n } = useTranslation()
  const [summary, setSummary] = useState<OverviewSummary | null>(null)
  const number = useMemo(() => new Intl.NumberFormat(i18n.resolvedLanguage === 'en' ? 'en-US' : 'de-DE'), [i18n.resolvedLanguage])

  useEffect(() => {
    let cancelled = false
    void fetch(`${import.meta.env.BASE_URL}data/summary.json`).then((response) => {
      if (!response.ok) throw new Error(`Summary request failed (${response.status})`)
      return response.json() as Promise<OverviewSummary>
    }).then((data) => { if (!cancelled) setSummary(data) }).catch((error: unknown) => console.error('Unable to load overview summary', error))
    return () => { cancelled = true }
  }, [])

  const data = summary ?? EMPTY_OVERVIEW_SUMMARY
  const solarUnits = data.total_capacity_mw.filter((row) => row.tech_type === 'Solar').reduce((sum, row) => sum + row.unit_count, 0)
  const windCapacity = data.total_capacity_mw.filter((row) => row.tech_type === 'Wind').reduce((sum, row) => sum + (row.capacity_mw ?? 0), 0)
  const totalCapacity = data.total_capacity_mw.reduce((sum, row) => sum + (row.capacity_mw ?? 0), 0)

  return (
    <div className="page-wrap">
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line" />{t('eyebrow')}</div>
          <h1>{t('title')}</h1>
          <p className="hero-description">{t('intro')}</p>
          <div className="hero-note"><span className="live-dot" />{number.format(data.data_quality.total_units)} {t('heroRegisteredUnits')} · {number.format(Math.round(totalCapacity))} MW {t('heroInstalledCapacity')} · {t('datasetAsOf')}</div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="sun-orb" />
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="land land-back" />
          <div className="land land-front" />
          <div className="windmill windmill-one"><span /><i /><b /></div>
          <div className="windmill windmill-two"><span /><i /><b /></div>
          <div className="turbine turbine-one"><span /><i /><b /></div>
          <div className="turbine turbine-two"><span /><i /><b /></div>
          <div className="power-line"><span /><span /><span /><span /></div>
          <div className="art-label"><span className="art-label-icon"><Zap size={14} fill="currentColor" /></span>Deutschland · 2026</div>
        </div>
      </section>

      <section className="content-grid" aria-label={t('dataTitle')}>
        <div className="section-heading">
          <div>
            <div className="section-kicker">01 <span />{t('overviewSection')}</div>
            <h2>{t('dataTitle')}</h2>
          </div>
          <p>{t('overviewIntro')}</p>
        </div>
        <div className="stat-grid">
          <StatCard icon={<Zap size={17} />} label={t('solarInstallations')} value={`${(solarUnits / 1_000_000).toLocaleString(i18n.resolvedLanguage === 'en' ? 'en-US' : 'de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${t('millionShort')}`} detail={t('largestByUnitCount')} trend="↗" />
          <StatCard icon={<MapPin size={17} />} label={t('windCapacity')} value={`${number.format(Math.round(windCapacity))} MW`} detail={t('largestByCapacity')} trend="↗" />
          <StatCard icon={<Globe2 size={17} />} label={t('coordinateCoverage')} value={`${data.data_quality.exact_coordinate_percentage.toLocaleString(i18n.resolvedLanguage === 'en' ? 'en-US' : 'de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`} detail={t('exactCoordinates')} trend="↗" />
        </div>
      </section>

      <section className="preview-panel">
        <div className="preview-copy">
          <div className="section-kicker">02 <span />{t('mapPreviewSection')}</div>
          <h2>{t('mapPreviewTitle')}</h2>
          <p>{t('mapPreviewIntro')}</p>
          <NavLink className="map-preview-cta" to="/map">{t('mapPreviewCta')} <span>→</span></NavLink>
        </div>
        <div className="preview-map"><MapView initialZoom={5.8} compact /></div>
      </section>
    </div>
  )
}

function StatCard({ icon, label, value, detail, trend }: { icon: React.ReactNode; label: string; value: string; detail: string; trend: string }) {
  return (
    <article className="stat-card">
      <div className="stat-top"><span className="stat-icon">{icon}</span><span className="stat-trend">{trend}</span></div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-detail">{detail}</div>
    </article>
  )
}

export default function App() {
  return <AppShell />
}
