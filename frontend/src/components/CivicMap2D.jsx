import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './CivicMap2D.css'
import citizenService from '../services/citizenService'

const MAP_STYLES = {
    light: `https://api.maptiler.com/maps/dataviz-v4/style.json?key=${import.meta.env.VITE_MAPTILER_KEY || 'default'}`,
    dark: `https://api.maptiler.com/maps/01a1d652-0a39-709c-9767-a516d6a90a1a/style.json?key=${import.meta.env.VITE_MAPTILER_KEY || 'default'}`,
}

function addComplaintLayers(map, complaintItems = []) {
    const complaintFeatures = (complaintItems || []).map((complaint) => ({
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [complaint.longitude, complaint.latitude],
        },
        properties: {
            id: complaint.id,
            category: complaint.category || 'Civic Issue',
            severity: complaint.severity || 5,
            priority: complaint.priority || 'Medium',
            status: complaint.status || 'Submitted',
            title: complaint.title || complaint.category || 'Civic Complaint',
            department: complaint.department_name || complaint.department || 'Municipal Operations',
            weight: (complaint.severity || 5) >= 8 ? 3 : (complaint.severity || 5) >= 5 ? 2 : 1,
        },
    }))

    const complaintGeoJSON = {
        type: 'FeatureCollection',
        features: complaintFeatures,
    }

    if (map.getSource('complaints')) {
        if (map.getLayer('complaint-points')) map.removeLayer('complaint-points')
        if (map.getLayer('complaint-heatmap')) map.removeLayer('complaint-heatmap')
        map.removeSource('complaints')
    }

    map.addSource('complaints', {
        type: 'geojson',
        data: complaintGeoJSON,
    })

    // Complaint density heatmap
    map.addLayer({
        id: 'complaint-heatmap',
        type: 'heatmap',
        source: 'complaints',
        maxzoom: 17,
        paint: {
            'heatmap-weight': ['interpolate', ['linear'], ['get', 'weight'], 1, 0.5, 2, 0.75, 3, 1],
            'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 7, 0.8, 11, 1.2, 15, 1.6, 17, 1.8],
            'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 7, 18, 10, 26, 13, 34, 16, 42, 17, 45],
            'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 7, 0.8, 12, 0.8, 14, 0.65, 16, 0.4, 17, 0.2],
            'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(0, 0, 0, 0)',
                0.15, '#36c5b4',
                0.3, '#70d6a0',
                0.45, '#f5e66b',
                0.6, '#ffad55',
                0.8, '#f45b69',
                1, '#c92f45',
            ],
        },
    })

    // Individual complaint markers
    map.addLayer({
        id: 'complaint-points',
        type: 'circle',
        source: 'complaints',
        minzoom: 11,
        paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 11, 4, 16, 7],
            'circle-color': [
                'match',
                ['get', 'priority'],
                'Critical', '#c92f45',
                'High', '#ff5964',
                'Medium', '#ffb454',
                'Low', '#55c98a',
                '#ffffff',
            ],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.5,
            'circle-opacity': 0.95,
        },
    })
}

function addProjectLayers(map, projectItems = []) {
    const projectFeatures = (projectItems || []).map((project) => ({
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [project.longitude, project.latitude],
        },
        properties: {
            id: project.id,
            title: project.title,
            description: project.description,
            department: project.department_name || 'Municipal Department',
            status: project.status || 'Ongoing',
            start_date: project.start_date,
            expected_end_date: project.expected_end_date,
        },
    }))

    const projectGeoJSON = {
        type: 'FeatureCollection',
        features: projectFeatures,
    }

    if (map.getSource('projects')) {
        if (map.getLayer('project-points')) map.removeLayer('project-points')
        map.removeSource('projects')
    }

    map.addSource('projects', {
        type: 'geojson',
        data: projectGeoJSON,
    })

    map.addLayer({
        id: 'project-points',
        type: 'circle',
        source: 'projects',
        minzoom: 7,
        paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 5, 12, 8, 16, 11],
            'circle-color': [
                'match',
                ['get', 'status'],
                'Ongoing', '#00bcb4',
                'Planned', '#ffb547',
                'Completed', '#10b981',
                '#00bcb4',
            ],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 2,
            'circle-opacity': 0.95,
        },
    })
}

function addHotspotLayers(map, hotspotItems = []) {
    const hotspotFeatures = (hotspotItems || []).map((hotspot) => ({
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [hotspot.longitude, hotspot.latitude],
        },
        properties: {
            id: hotspot.id,
            description: hotspot.description,
            congestion_level: hotspot.congestion_level || 'Medium',
            source: hotspot.source || 'demo',
            observed_at: hotspot.observed_at,
        },
    }))

    const hotspotGeoJSON = {
        type: 'FeatureCollection',
        features: hotspotFeatures,
    }

    if (map.getSource('traffic-hotspots')) {
        if (map.getLayer('traffic-hotspot-points')) map.removeLayer('traffic-hotspot-points')
        map.removeSource('traffic-hotspots')
    }

    map.addSource('traffic-hotspots', {
        type: 'geojson',
        data: hotspotGeoJSON,
    })

    map.addLayer({
        id: 'traffic-hotspot-points',
        type: 'circle',
        source: 'traffic-hotspots',
        minzoom: 7,
        paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 6, 12, 9, 16, 13],
            'circle-color': [
                'match',
                ['get', 'congestion_level'],
                'High', '#ef4444',
                'Medium', '#f59e0b',
                'Low', '#eab308',
                '#f59e0b',
            ],
            'circle-stroke-color': '#111827',
            'circle-stroke-width': 2,
            'circle-opacity': 0.9,
        },
    })
}

function addSafetyZoneLayers(map, zoneItems = []) {
    const zoneFeatures = (zoneItems || []).map((zone) => ({
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [zone.longitude, zone.latitude],
        },
        properties: {
            id: zone.zone_id,
            zone_id: zone.zone_id,
            category: zone.category,
            report_count: zone.report_count,
            suggested_action: zone.suggested_action,
            status: zone.status || 'Active Reports',
        },
    }))

    const zoneGeoJSON = {
        type: 'FeatureCollection',
        features: zoneFeatures,
    }

    if (map.getSource('safety-zones')) {
        if (map.getLayer('safety-zone-circles')) map.removeLayer('safety-zone-circles')
        map.removeSource('safety-zones')
    }

    map.addSource('safety-zones', {
        type: 'geojson',
        data: zoneGeoJSON,
    })

    map.addLayer({
        id: 'safety-zone-circles',
        type: 'circle',
        source: 'safety-zones',
        minzoom: 7,
        paint: {
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 14, 11, 24, 15, 38],
            'circle-color': 'rgba(168, 85, 247, 0.28)',
            'circle-stroke-color': '#a855f7',
            'circle-stroke-width': 2,
            'circle-opacity': 0.85,
        },
    })
}

function applyLayerVisibility(map, visibility) {
    if (!map || !map.isStyleLoaded()) return
    const setVis = (layerId, isVis) => {
        if (map.getLayer(layerId)) {
            map.setLayoutProperty(layerId, 'visibility', isVis ? 'visible' : 'none')
        }
    }
    setVis('complaint-heatmap', visibility.complaints)
    setVis('complaint-points', visibility.complaints)
    setVis('project-points', visibility.projects)
    setVis('traffic-hotspot-points', visibility.hotspots)
    setVis('safety-zone-circles', visibility.safetyZones)
}

export default function CivicMap2D() {
    const mapContainer = useRef(null)
    const mapRef = useRef(null)

    const [theme, setTheme] = useState('light')
    const [mapLoaded, setMapLoaded] = useState(false)
    const [loadingData, setLoadingData] = useState(true)
    const [mapError, setMapError] = useState(null)

    // Four datasets
    const [complaintsData, setComplaintsData] = useState([])
    const [projectsData, setProjectsData] = useState([])
    const [hotspotsData, setHotspotsData] = useState([])
    const [safetyZonesData, setSafetyZonesData] = useState([])

    // Ref copies for event listeners
    const dataRef = useRef({
        complaints: [],
        projects: [],
        hotspots: [],
        safetyZones: [],
    })

    // Layer toggles
    const [layerVisibility, setLayerVisibility] = useState({
        complaints: true,
        projects: true,
        hotspots: true,
        safetyZones: true,
    })

    // Unified selected marker
    const [selectedItem, setSelectedItem] = useState(null)

    // Synchronize ref with state
    useEffect(() => {
        dataRef.current = {
            complaints: complaintsData,
            projects: projectsData,
            hotspots: hotspotsData,
            safetyZones: safetyZonesData,
        }
    }, [complaintsData, projectsData, hotspotsData, safetyZonesData])

    // Load all four map endpoints in parallel
    useEffect(() => {
        let isMounted = true
        async function fetchAllMapData() {
            setLoadingData(true)
            setMapError(null)

            const [cRes, pRes, hRes, sRes] = await Promise.allSettled([
                citizenService.getMapComplaints(),
                citizenService.getMapProjects(),
                citizenService.getMapHotspots(),
                citizenService.getMapSafetyZones(),
            ])

            if (!isMounted) return

            if (cRes.status === 'fulfilled' && Array.isArray(cRes.value)) {
                setComplaintsData(cRes.value)
            } else if (cRes.status === 'rejected') {
                console.warn('Unable to load map complaints:', cRes.reason?.message)
            }

            if (pRes.status === 'fulfilled' && Array.isArray(pRes.value)) {
                setProjectsData(pRes.value)
            } else if (pRes.status === 'rejected') {
                console.warn('Unable to load map projects:', pRes.reason?.message)
            }

            if (hRes.status === 'fulfilled' && Array.isArray(hRes.value)) {
                setHotspotsData(hRes.value)
            } else if (hRes.status === 'rejected') {
                console.warn('Unable to load map hotspots:', hRes.reason?.message)
            }

            if (sRes.status === 'fulfilled' && Array.isArray(sRes.value)) {
                setSafetyZonesData(sRes.value)
            } else if (sRes.status === 'rejected') {
                console.warn('Unable to load map safety zones:', sRes.reason?.message)
            }

            setLoadingData(false)

            if (mapRef.current && mapRef.current.isStyleLoaded()) {
                refreshAllMapLayers(mapRef.current)
            }
        }

        fetchAllMapData()
        return () => { isMounted = false }
    }, [])

    function refreshAllMapLayers(map) {
        if (!map || !map.isStyleLoaded()) return
        addComplaintLayers(map, dataRef.current.complaints)
        addProjectLayers(map, dataRef.current.projects)
        addHotspotLayers(map, dataRef.current.hotspots)
        addSafetyZoneLayers(map, dataRef.current.safetyZones)
        applyLayerVisibility(map, layerVisibility)
    }

    function toggleLayer(layerKey) {
        setLayerVisibility(prev => {
            const next = { ...prev, [layerKey]: !prev[layerKey] }
            if (mapRef.current && mapRef.current.isStyleLoaded()) {
                applyLayerVisibility(mapRef.current, next)
            }
            return next
        })
    }

    // Map initialization
    useEffect(() => {
        if (mapRef.current) return

        const map = new maplibregl.Map({
            container: mapContainer.current,
            style: MAP_STYLES[theme],
            center: [73.95, 15.45],
            zoom: 9,
            minZoom: 7,
            maxZoom: 19,
            attributionControl: true,
        })

        mapRef.current = map

        map.addControl(new maplibregl.NavigationControl(), 'top-right')

        map.on('load', () => {
            map.resize()
            refreshAllMapLayers(map)

            let activePopup = null

            // Helper to clean popup
            const removePopup = () => {
                if (activePopup) {
                    activePopup.remove()
                    activePopup = null
                }
            }

            // 1. Complaint hover & click
            map.on('mouseenter', 'complaint-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const complaint = dataRef.current.complaints.find(
                    (item) => String(item.id) === String(feature.properties.id)
                )
                if (!complaint) return

                removePopup()
                const popupContent = document.createElement('div')
                popupContent.className = 'complaint-popup'
                popupContent.innerHTML = `
                    <div class="popup-header">
                        <strong>#${String(complaint.id).slice(0, 8)}</strong>
                        <span class="priority-badge priority-${(complaint.priority || 'Medium').toLowerCase()}">${complaint.priority || 'Medium'}</span>
                    </div>
                    <h4>${complaint.title || complaint.category || 'Civic Issue'}</h4>
                    <div class="popup-footer">
                        <span class="status-badge status-${String(complaint.status || 'Submitted').toLowerCase().replaceAll(' ', '-')}">${complaint.status || 'Submitted'}</span>
                    </div>
                `
                activePopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '240px', offset: 14, className: 'civic-complaint-popup' })
                    .setLngLat(feature.geometry.coordinates)
                    .setDOMContent(popupContent)
                    .addTo(map)
            })

            map.on('mouseleave', 'complaint-points', removePopup)
            map.on('click', 'complaint-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const complaint = dataRef.current.complaints.find(
                    (item) => String(item.id) === String(feature.properties.id)
                )
                if (complaint) {
                    removePopup()
                    setSelectedItem({ type: 'complaint', data: complaint })
                }
            })

            // 2. Project hover & click
            map.on('mouseenter', 'project-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const project = dataRef.current.projects.find(
                    (p) => String(p.id) === String(feature.properties.id)
                )
                if (!project) return

                removePopup()
                const popupContent = document.createElement('div')
                popupContent.className = 'complaint-popup'
                popupContent.innerHTML = `
                    <div class="popup-header">
                        <strong style="color: #00bcb4;">MUNICIPAL PROJECT</strong>
                        <span class="status-badge status-${String(project.status || 'Ongoing').toLowerCase()}">${project.status || 'Ongoing'}</span>
                    </div>
                    <h4>${project.title}</h4>
                    <div class="popup-footer">
                        <span style="font-size: 11px; color: #9aa8b2;">${project.department_name || 'Public Works'}</span>
                    </div>
                `
                activePopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '260px', offset: 14, className: 'civic-complaint-popup' })
                    .setLngLat(feature.geometry.coordinates)
                    .setDOMContent(popupContent)
                    .addTo(map)
            })

            map.on('mouseleave', 'project-points', removePopup)
            map.on('click', 'project-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const project = dataRef.current.projects.find(
                    (p) => String(p.id) === String(feature.properties.id)
                )
                if (project) {
                    removePopup()
                    setSelectedItem({ type: 'project', data: project })
                }
            })

            // 3. Traffic Hotspots hover & click (DEMO DATA)
            map.on('mouseenter', 'traffic-hotspot-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const hotspot = dataRef.current.hotspots.find(
                    (h) => String(h.id) === String(feature.properties.id)
                )
                if (!hotspot) return

                removePopup()
                const popupContent = document.createElement('div')
                popupContent.className = 'complaint-popup'
                popupContent.innerHTML = `
                    <div class="popup-header">
                        <strong style="color: #f59e0b;">[DEMO] TRAFFIC HOTSPOT</strong>
                        <span class="priority-badge priority-${String(hotspot.congestion_level || 'Medium').toLowerCase()}">${hotspot.congestion_level || 'Medium'}</span>
                    </div>
                    <h4>${hotspot.description}</h4>
                    <div class="popup-footer">
                        <span style="font-size: 10px; color: #f59e0b; font-weight: bold;">Simulated Demo Feed</span>
                    </div>
                `
                activePopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '250px', offset: 14, className: 'civic-complaint-popup' })
                    .setLngLat(feature.geometry.coordinates)
                    .setDOMContent(popupContent)
                    .addTo(map)
            })

            map.on('mouseleave', 'traffic-hotspot-points', removePopup)
            map.on('click', 'traffic-hotspot-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const hotspot = dataRef.current.hotspots.find(
                    (h) => String(h.id) === String(feature.properties.id)
                )
                if (hotspot) {
                    removePopup()
                    setSelectedItem({ type: 'hotspot', data: hotspot })
                }
            })

            // 4. Aggregated Safety Zones hover & click (PRIVACY PRESERVED)
            map.on('mouseenter', 'safety-zone-circles', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const zone = dataRef.current.safetyZones.find(
                    (z) => String(z.zone_id) === String(feature.properties.id)
                )
                if (!zone) return

                removePopup()
                const popupContent = document.createElement('div')
                popupContent.className = 'complaint-popup'
                popupContent.innerHTML = `
                    <div class="popup-header">
                        <strong style="color: #a855f7;">[AGGREGATED] SAFETY ZONE</strong>
                        <span style="font-size: 10px; color: #e9d5ff; font-weight: bold;">${zone.report_count} reports (k &gt;= 3)</span>
                    </div>
                    <h4>${zone.category}</h4>
                    <div class="popup-footer">
                        <span style="font-size: 10px; color: #a855f7;">${zone.suggested_action}</span>
                    </div>
                `
                activePopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, maxWidth: '260px', offset: 14, className: 'civic-complaint-popup' })
                    .setLngLat(feature.geometry.coordinates)
                    .setDOMContent(popupContent)
                    .addTo(map)
            })

            map.on('mouseleave', 'safety-zone-circles', removePopup)
            map.on('click', 'safety-zone-circles', (event) => {
                const feature = event.features?.[0]
                if (!feature) return
                const zone = dataRef.current.safetyZones.find(
                    (z) => String(z.zone_id) === String(feature.properties.id)
                )
                if (zone) {
                    removePopup()
                    setSelectedItem({ type: 'safety_zone', data: zone })
                }
            })

            // Cursor pointers
            const interactiveLayers = ['complaint-points', 'project-points', 'traffic-hotspot-points', 'safety-zone-circles']
            interactiveLayers.forEach(lyr => {
                map.on('mouseenter', lyr, () => { map.getCanvas().style.cursor = 'pointer' })
                map.on('mouseleave', lyr, () => { map.getCanvas().style.cursor = '' })
            })

            setMapLoaded(true)
        })

        map.on('error', (event) => {
            console.error('MapLibre error:', event.error)
        })

        return () => {
            map.remove()
            mapRef.current = null
        }
    }, [])

    // Update style on theme toggle and restore layers
    useEffect(() => {
        const map = mapRef.current
        if (!map || !mapLoaded) return

        map.setStyle(MAP_STYLES[theme])
        map.once('style.load', () => {
            refreshAllMapLayers(map)
        })
    }, [theme, mapLoaded])

    return (
        <div className={`civic-map-wrapper ${theme}-theme`}>
            <div className="civic-map-header">
                <div>
                    <span className="civic-map-eyebrow">CIVICSYNC / GEOSPATIAL</span>
                    <h2>Goa Civic Map</h2>
                    <p>Explore real-time municipal reports, public projects, demo traffic, and aggregated safety zones</p>
                </div>

                <div className="map-theme-switch">
                    <button
                        className={theme === 'light' ? 'active' : ''}
                        onClick={() => setTheme('light')}
                    >
                        ☀ Light
                    </button>
                    <button
                        className={theme === 'dark' ? 'active' : ''}
                        onClick={() => setTheme('dark')}
                    >
                        ☾ Dark
                    </button>
                </div>
            </div>

            {/* LAYER TOGGLE CONTROLS */}
            <div className="map-layer-toggles">
                <button
                    className={`map-layer-btn ${layerVisibility.complaints ? 'active' : ''}`}
                    onClick={() => toggleLayer('complaints')}
                >
                    <span className="layer-dot complaint-dot" />
                    Complaints ({complaintsData.length})
                </button>

                <button
                    className={`map-layer-btn ${layerVisibility.projects ? 'active' : ''}`}
                    onClick={() => toggleLayer('projects')}
                >
                    <span className="layer-dot project-dot" />
                    Projects ({projectsData.length})
                </button>

                <button
                    className={`map-layer-btn ${layerVisibility.hotspots ? 'active' : ''}`}
                    onClick={() => toggleLayer('hotspots')}
                >
                    <span className="layer-dot hotspot-dot" />
                    Traffic [Demo] ({hotspotsData.length})
                </button>

                <button
                    className={`map-layer-btn ${layerVisibility.safetyZones ? 'active' : ''}`}
                    onClick={() => toggleLayer('safetyZones')}
                >
                    <span className="layer-dot safety-dot" />
                    Safety Zones [Aggregated] ({safetyZonesData.length})
                </button>
            </div>

            {/* SELECTED ITEM DETAILS PANEL */}
            {selectedItem && (
                <div className="complaint-details-panel">
                    <div className="complaint-panel-header">
                        <div>
                            <span className="civic-map-eyebrow">
                                {selectedItem.type === 'complaint' && 'COMPLAINT DETAILS'}
                                {selectedItem.type === 'project' && 'MUNICIPAL INFRASTRUCTURE PROJECT'}
                                {selectedItem.type === 'hotspot' && 'TRAFFIC HOTSPOT (DEMO DATA)'}
                                {selectedItem.type === 'safety_zone' && 'AGGREGATED SAFETY ZONE (PRIVACY PRESERVED)'}
                            </span>
                            <h3>
                                {selectedItem.type === 'complaint' && `#${String(selectedItem.data.id).slice(0, 8)}`}
                                {selectedItem.type === 'project' && selectedItem.data.title}
                                {selectedItem.type === 'hotspot' && `${selectedItem.data.congestion_level} Congestion Hotspot`}
                                {selectedItem.type === 'safety_zone' && selectedItem.data.zone_id}
                            </h3>
                        </div>

                        <button
                            className="complaint-close-button"
                            onClick={() => setSelectedItem(null)}
                        >
                            ✕
                        </button>
                    </div>

                    <div className="complaint-details-grid">
                        {/* 1. Complaint View */}
                        {selectedItem.type === 'complaint' && (
                            <>
                                <div className="complaint-detail-item">
                                    <span>Title</span>
                                    <strong>{selectedItem.data.title || selectedItem.data.category}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Category</span>
                                    <strong>{selectedItem.data.category}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Department</span>
                                    <strong>{selectedItem.data.department_name || 'Municipal Operations'}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Priority</span>
                                    <strong className={`priority-badge priority-${(selectedItem.data.priority || 'Medium').toLowerCase()}`}>
                                        {selectedItem.data.priority || 'Medium'}
                                    </strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Status</span>
                                    <strong className={`status-badge status-${String(selectedItem.data.status || 'Submitted').toLowerCase().replaceAll(' ', '-')}`}>
                                        {selectedItem.data.status || 'Submitted'}
                                    </strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Reports</span>
                                    <strong>{selectedItem.data.report_count || 1}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Coordinates</span>
                                    <strong>{selectedItem.data.latitude?.toFixed(4)}, {selectedItem.data.longitude?.toFixed(4)}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Date Reported</span>
                                    <strong>
                                        {selectedItem.data.created_at ? new Date(selectedItem.data.created_at).toLocaleDateString('en-IN') : 'Recent'}
                                    </strong>
                                </div>
                            </>
                        )}

                        {/* 2. Project View */}
                        {selectedItem.type === 'project' && (
                            <>
                                <div className="complaint-detail-item">
                                    <span>Title</span>
                                    <strong>{selectedItem.data.title}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Department</span>
                                    <strong>{selectedItem.data.department_name || 'Public Works'}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Status</span>
                                    <strong className="status-badge status-in-progress">
                                        {selectedItem.data.status}
                                    </strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Timeline</span>
                                    <strong>{selectedItem.data.start_date} to {selectedItem.data.expected_end_date}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Coordinates</span>
                                    <strong>{selectedItem.data.latitude?.toFixed(4)}, {selectedItem.data.longitude?.toFixed(4)}</strong>
                                </div>
                                <div className="complaint-description">
                                    <span>Description</span>
                                    <p>{selectedItem.data.description || 'Public works infrastructure initiative.'}</p>
                                </div>
                            </>
                        )}

                        {/* 3. Traffic Hotspot View */}
                        {selectedItem.type === 'hotspot' && (
                            <>
                                <div className="complaint-detail-item">
                                    <span>Congestion Level</span>
                                    <strong className={`priority-badge priority-${String(selectedItem.data.congestion_level || 'Medium').toLowerCase()}`}>
                                        {selectedItem.data.congestion_level}
                                    </strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Data Source</span>
                                    <strong style={{ color: '#f59e0b' }}>Demo / Simulated Feed</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Observed At</span>
                                    <strong>
                                        {selectedItem.data.observed_at ? new Date(selectedItem.data.observed_at).toLocaleString('en-IN') : 'Active Feed'}
                                    </strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Coordinates</span>
                                    <strong>{selectedItem.data.latitude?.toFixed(4)}, {selectedItem.data.longitude?.toFixed(4)}</strong>
                                </div>
                                <div className="complaint-description">
                                    <span>Observation Description</span>
                                    <p>{selectedItem.data.description}</p>
                                </div>
                            </>
                        )}

                        {/* 4. Aggregated Safety Zone View */}
                        {selectedItem.type === 'safety_zone' && (
                            <>
                                <div className="complaint-detail-item">
                                    <span>Safety Category</span>
                                    <strong style={{ color: '#a855f7' }}>{selectedItem.data.category}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Community Reports</span>
                                    <strong>{selectedItem.data.report_count} citizen concerns (k &gt;= 3)</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Status</span>
                                    <strong className="status-badge status-resolved">{selectedItem.data.status}</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Privacy Protection</span>
                                    <strong>Centroid rounded to 2 decimal places. No individual reports exposed.</strong>
                                </div>
                                <div className="complaint-detail-item">
                                    <span>Centroid Coordinates</span>
                                    <strong>{selectedItem.data.latitude?.toFixed(2)}, {selectedItem.data.longitude?.toFixed(2)}</strong>
                                </div>
                                <div className="complaint-description">
                                    <span>Recommended Municipal Action</span>
                                    <p>{selectedItem.data.suggested_action}</p>
                                </div>
                            </>
                        )}

                        <a
                            className="google-maps-button"
                            href={`https://www.google.com/maps/dir/?api=1&destination=${selectedItem.data.latitude},${selectedItem.data.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Get Directions on Google Maps
                        </a>
                    </div>
                </div>
            )}

            <div className="civic-map-container">
                {(!mapLoaded || loadingData) && (
                    <div className="map-loading">
                        {loadingData ? 'Fetching city map data layers...' : 'Initializing Goa map...'}
                    </div>
                )}
                <div ref={mapContainer} className="civic-map-canvas" />
            </div>

            <div className="civic-map-footer">
                <span>GOA, INDIA · 4 INTEGRATED LAYERS (COMPLAINTS, PROJECTS, DEMO TRAFFIC, AGGREGATED SAFETY)</span>
                <span>MAP DATA © MAPTILER © OPENSTREETMAP</span>
            </div>
        </div>
    )
}
