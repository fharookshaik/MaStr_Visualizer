import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Map as MapLibreMap, MapGeoJSONFeature, MapLayerMouseEvent } from 'maplibre-gl'
import { useTranslation } from 'react-i18next'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'
import './MapView.css'

export type UnitDetails = {
  mastr_id: string
  tech_type: string
  capacity_mw: number | null
  status: string
  municipality_name: string
  state: string
  coordinates: [number, number]
}

type MapViewProps = {
  tech?: string
  status?: string
  state?: string
  initialZoom?: number
  compact?: boolean
  onUnitSelect?: (unit: UnitDetails) => void
}
type ClusterFeature = {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: Record<string, string | number | null>
}
type ClusterCollection = { type: 'FeatureCollection'; features: ClusterFeature[] }

const TILE_URL = `${import.meta.env.BASE_URL}data/map.pmtiles`
const CLUSTER_URL = `${import.meta.env.BASE_URL}data/map-clusters.geojson`
const MAP_STYLE = 'https://tiles.openfreemap.org/styles/liberty'
const EMPTY_CLUSTERS: ClusterCollection = { type: 'FeatureCollection', features: [] }
const emptyGeoJSON = EMPTY_CLUSTERS as unknown as Parameters<GeoJSONSource['setData']>[0]
const UNKNOWN_COLOR = '#64736a'
const TECH_STROKES: Record<string, string> = {
  Solar: '#805600', Wind: '#184f95', Biomass: '#005a00', Storage: '#40318f', Hydro: '#08794f',
  Thermal: '#9e3e1b', Gas: '#98365c', Geothermal: '#98365c', Nuclear: '#40318f', 'Gas Storage': '#08794f',
}
const TECH_FILL_EXPRESSION: maplibregl.ExpressionSpecification = ['match', ['get', 'tech_type'],
  'Solar', '#eda100', 'Wind', '#2a78d6', 'Biomass', '#008300',
  'Storage', ['case', ['==', ['%', ['to-number', ['slice', ['get', 'mastr_id'], -1]], 2], 0], '#6250d6', '#1baf7a'],
  'Hydro', ['case', ['==', ['%', ['to-number', ['slice', ['get', 'mastr_id'], -1]], 2], 0], '#1baf7a', '#6250d6'],
  'Thermal', ['case', ['==', ['%', ['to-number', ['slice', ['get', 'mastr_id'], -1]], 2], 0], '#eda100', '#eb6834'],
  'Gas', ['case', ['==', ['%', ['to-number', ['slice', ['get', 'mastr_id'], -1]], 2], 0], '#eb6834', '#e87ba4'],
  'Geothermal', '#e87ba4', 'Nuclear', '#6250d6', 'Gas Storage', '#1baf7a', UNKNOWN_COLOR,
]
const pmtilesProtocol = new Protocol()

if (typeof window !== 'undefined') {
  maplibregl.addProtocol('pmtiles', pmtilesProtocol.tile)
}

function filterFor(tech: string, status: string, state: string): maplibregl.FilterSpecification | null {
  const clauses: unknown[][] = []
  if (tech) clauses.push(['==', ['get', 'tech_type'], tech])
  if (status) clauses.push(['==', ['get', 'status'], status])
  if (state) clauses.push(['==', ['get', 'state'], state])
  if (clauses.length === 0) return null
  return (clauses.length === 1 ? clauses[0] : ['all', ...clauses]) as maplibregl.FilterSpecification
}

function pointPopup(properties: Record<string, unknown>, t: (key: string) => string, language: string) {
  const content = document.createElement('div')
  content.className = 'unit-popup'
  const title = document.createElement('strong')
  title.textContent = String(properties.mastr_id || t('unitDetailTitle'))
  content.append(title)
  const rows: Array<[string, string]> = [
    [t('technology'), t(techTranslationKey(String(properties.tech_type ?? '')))],
    [t('capacity'), properties.capacity_mw == null ? '—' : `${new Intl.NumberFormat(language).format(Number(properties.capacity_mw))} MW`],
    [t('municipality'), String(properties.municipality_name || '—')],
  ]
  for (const [label, value] of rows) {
    const row = document.createElement('span')
    row.textContent = `${label}: ${value}`
    content.append(row)
  }
  return content
}

function techTranslationKey(value: string) {
  const keys: Record<string, string> = {
    Solar: 'techSolar', Wind: 'techWind', Biomass: 'techBiomass', Storage: 'techStorage', Hydro: 'techHydro',
    Thermal: 'techThermal', Gas: 'techGas', Geothermal: 'techGeothermal', Nuclear: 'techNuclear', 'Gas Storage': 'techGasStorage',
  }
  return keys[value] ?? value
}

export default function MapView({ tech = '', status = '', state = '', initialZoom = 5.2, compact = false, onUnitSelect }: MapViewProps) {
  const { t, i18n } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const popupRef = useRef<maplibregl.Popup | null>(null)
  const clusterFeaturesRef = useRef<ClusterFeature[]>([])
  const hoveredFeatureRef = useRef<{ id: string | number; source: string; sourceLayer?: string } | null>(null)
  const currentFilterRef = useRef({ tech, status, state })
  const translateRef = useRef(t)
  const i18nRef = useRef(i18n)
  const selectRef = useRef(onUnitSelect)
  useEffect(() => {
    currentFilterRef.current = { tech, status, state }
    translateRef.current = t
    i18nRef.current = i18n
    selectRef.current = onUnitSelect
  }, [tech, status, state, t, i18n, onUnitSelect])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [10.4515, 51.1657],
      zoom: initialZoom,
      minZoom: 4.5,
      maxZoom: 14,
      interactive: !compact,
      attributionControl: { compact: true },
    })
    mapRef.current = map
    if (!compact) map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    map.on('load', () => {
      map.addSource('unit-clusters', {
        type: 'geojson',
        data: emptyGeoJSON,
        cluster: true,
        clusterRadius: 50,
        clusterMaxZoom: 7,
        clusterProperties: { unit_count: ['+', ['get', 'unit_count']] },
      })
      map.addSource('mastr-units', {
        type: 'vector',
        url: `pmtiles://${new URL(TILE_URL, window.location.href).toString()}`,
        attribution: 'Daten: Marktstammdatenregister (Bundesnetzagentur), dl-de/by-2.0',
        promoteId: { units: 'mastr_id' },
      })
      map.addLayer({
        id: 'unit-cluster-circles', type: 'circle', source: 'unit-clusters',
        filter: ['has', 'point_count'], maxzoom: 8,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'unit_count'], 1, 15, 100, 21, 1000, 29, 10000, 37],
          'circle-color': '#2a78d6', 'circle-opacity': 0.86,
          'circle-stroke-width': 2, 'circle-stroke-color': '#f4f6f2',
        },
      })
      map.addLayer({
        id: 'unit-cluster-count', type: 'symbol', source: 'unit-clusters',
        filter: ['has', 'point_count'], maxzoom: 8,
        layout: {
          'text-field': ['number-format', ['get', 'unit_count'], { locale: navigator.language }],
          'text-size': 11, 'text-font': ['Open Sans Bold'], 'text-allow-overlap': true,
        },
        paint: { 'text-color': '#ffffff' },
      })
      map.addLayer({
        id: 'unit-cluster-cells', type: 'circle', source: 'unit-clusters',
        filter: ['!', ['has', 'point_count']], maxzoom: 8,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'unit_count'], 1, 4, 100, 8, 1000, 12],
          'circle-color': '#2a78d6', 'circle-opacity': 0.78,
          'circle-stroke-width': 0.75, 'circle-stroke-color': '#184f95',
        },
      })
      map.addLayer({
        id: 'unit-cluster-cell-count', type: 'symbol', source: 'unit-clusters',
        filter: ['!', ['has', 'point_count']], maxzoom: 8,
        layout: { 'text-field': ['number-format', ['get', 'unit_count'], { locale: navigator.language }], 'text-size': 10, 'text-font': ['Open Sans Bold'] },
        paint: { 'text-color': '#ffffff' },
      })
      map.addLayer({
        id: 'units-points', type: 'circle', source: 'mastr-units', 'source-layer': 'units', minzoom: 8,
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 4, 10, 5, 12, 7, 14, 10],
          'circle-color': TECH_FILL_EXPRESSION,
          'circle-opacity': 0.82,
          'circle-stroke-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2, 0.75],
          'circle-stroke-color': ['match', ['get', 'tech_type'],
            'Solar', TECH_STROKES.Solar, 'Wind', TECH_STROKES.Wind, 'Biomass', TECH_STROKES.Biomass,
            'Storage', TECH_STROKES.Storage, 'Hydro', TECH_STROKES.Hydro, 'Thermal', TECH_STROKES.Thermal,
            'Gas', TECH_STROKES.Gas, 'Geothermal', TECH_STROKES.Geothermal, 'Nuclear', TECH_STROKES.Nuclear,
            'Gas Storage', TECH_STROKES['Gas Storage'], '#3b4940'],
        },
      })
      map.addLayer({
        id: 'units-points-hit', type: 'circle', source: 'mastr-units', 'source-layer': 'units', minzoom: 8,
        paint: { 'circle-radius': 14, 'circle-color': '#000000', 'circle-opacity': 0 },
      })
      map.on('mouseenter', 'unit-cluster-circles', () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', 'unit-cluster-circles', () => { map.getCanvas().style.cursor = '' })
      map.on('click', 'unit-cluster-circles', (event) => {
        const cluster = event.features?.[0]
        if (!cluster) return
        const clusterId = Number(cluster.properties?.cluster_id)
        const source = map.getSource('unit-clusters') as GeoJSONSource
        void source.getClusterExpansionZoom(clusterId).then((zoom) => {
          map.easeTo({ center: (cluster.geometry as { coordinates: [number, number] }).coordinates, zoom })
        })
      })
      map.on('mouseenter', 'units-points-hit', () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', 'units-points-hit', () => {
        map.getCanvas().style.cursor = ''
        const previous = hoveredFeatureRef.current
        if (previous) map.setFeatureState({ source: previous.source, sourceLayer: previous.sourceLayer, id: previous.id }, { hover: false })
        hoveredFeatureRef.current = null
        if (selectRef.current) popupRef.current?.remove()
      })
      map.on('mousemove', 'units-points-hit', (event: MapLayerMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const feature = event.features?.[0]
        if (!feature) return
        if (feature.id !== undefined) {
          const previous = hoveredFeatureRef.current
          if (previous && previous.id !== feature.id) map.setFeatureState({ source: previous.source, sourceLayer: previous.sourceLayer, id: previous.id }, { hover: false })
          map.setFeatureState({ source: 'mastr-units', sourceLayer: 'units', id: feature.id }, { hover: true })
          hoveredFeatureRef.current = { source: 'mastr-units', sourceLayer: 'units', id: feature.id }
        }
        if (selectRef.current) return
        const geometry = feature.geometry as { coordinates: [number, number] }
        if (!popupRef.current) popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '260px', offset: 12 })
        popupRef.current.setLngLat(geometry.coordinates).setDOMContent(pointPopup(feature.properties ?? {}, translateRef.current, i18nRef.current.resolvedLanguage ?? 'de')).addTo(map)
      })
      map.on('click', 'units-points-hit', (event: MapLayerMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const feature = event.features?.[0]
        if (!feature) return
        const properties = feature.properties ?? {}
        const geometry = feature.geometry as { coordinates: [number, number] }
        const unit = {
          mastr_id: String(properties.mastr_id ?? ''), tech_type: String(properties.tech_type ?? ''),
          capacity_mw: properties.capacity_mw == null ? null : Number(properties.capacity_mw),
          status: String(properties.status ?? ''), municipality_name: String(properties.municipality_name ?? ''),
          state: String(properties.state ?? ''), coordinates: geometry.coordinates,
        }
        if (selectRef.current) selectRef.current(unit)
        else new maplibregl.Popup({ closeButton: true, maxWidth: '260px' }).setLngLat(unit.coordinates).setDOMContent(pointPopup(properties, translateRef.current, i18nRef.current.resolvedLanguage ?? 'de')).addTo(map)
      })

      void fetch(CLUSTER_URL).then((response) => {
        if (!response.ok) throw new Error(`Cluster data request failed (${response.status})`)
        return response.json() as Promise<ClusterCollection>
      }).then((collection) => {
        clusterFeaturesRef.current = collection.features
        applyFilters(map, clusterFeaturesRef.current, currentFilterRef.current)
      }).catch((error: unknown) => console.error('Unable to load map cluster data', error))
    })

    return () => {
      popupRef.current?.remove()
      popupRef.current = null
      map.remove()
      mapRef.current = null
    }
  }, [compact, initialZoom])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const apply = () => applyFilters(map, clusterFeaturesRef.current, { tech, status, state })
    if (map.isStyleLoaded()) apply()
    else map.once('load', apply)
    return () => { map.off('load', apply) }
  }, [tech, status, state])

  return <div ref={containerRef} className={`map-view${compact ? ' map-view-compact' : ''}`} aria-label={t('mapAriaLabel')} />
}

function applyFilters(map: MapLibreMap, features: ClusterFeature[], filters: { tech: string; status: string; state: string }) {
  const filter = filterFor(filters.tech, filters.status, filters.state)
  if (map.getLayer('units-points')) map.setFilter('units-points', filter)
  if (map.getLayer('units-points-hit')) map.setFilter('units-points-hit', filter)
  const source = map.getSource('unit-clusters') as GeoJSONSource | undefined
  if (source) {
    const matching = features.filter((feature) => {
      const properties = feature.properties ?? {}
      return (!filters.tech || properties.tech_type === filters.tech)
        && (!filters.status || properties.status === filters.status)
        && (!filters.state || properties.state === filters.state)
    })
    void source.setData({ type: 'FeatureCollection', features: matching } as unknown as Parameters<GeoJSONSource['setData']>[0])
  }
}
