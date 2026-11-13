
import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './CivicMap2D.css'
import complaints from '../data/complaints'

const MAP_STYLES = {
    light: `https://api.maptiler.com/maps/dataviz-v4/style.json?key=${import.meta.env.VITE_MAPTILER_KEY}`,

    dark: `https://api.maptiler.com/maps/01a1d652-0a39-709c-9767-a516d6a90a1a/style.json?key=${import.meta.env.VITE_MAPTILER_KEY}`,
}



function addComplaintHeatmap(map) {
    const complaintFeatures = complaints.map((complaint) => ({
        type: 'Feature',
        geometry: {
            type: 'Point',
            coordinates: [
                complaint.longitude,
                complaint.latitude,
            ],
        },
        properties: {
            id: complaint.id,
            category: complaint.category,
            severity: complaint.severity,
            priority: complaint.priority,
            weight:
                complaint.severity >= 8 ? 3 :
                    complaint.severity >= 5 ? 2 : 1,
        },
    }))

    const complaintGeoJSON = {
        type: 'FeatureCollection',
        features: complaintFeatures,
    }

    if (map.getSource('complaints')) {
        if (map.getLayer('complaint-points')) {
            map.removeLayer('complaint-points')
        }

        if (map.getLayer('complaint-heatmap')) {
            map.removeLayer('complaint-heatmap')
        }

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
            'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'weight'],
                1, 0.5,
                2, 0.75,
                3, 1,
            ],

            'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                7, 0.8,
                11, 1.2,
                15, 1.6,
                17, 1.8,
            ],

            'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                7, 18,
                10, 26,
                13, 34,
                16, 42,
                17, 45,
            ],

            'heatmap-opacity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                7, 0.8,
                12, 0.8,
                14, 0.65,
                16, 0.4,
                17, 0.2,
            ],

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
        minzoom: 12,

        paint: {
            'circle-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                12, 4,
                16, 7,
            ],

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



export default function CivicMap2D() {
    const mapContainer = useRef(null)
    const mapRef = useRef(null)

    const [theme, setTheme] = useState('light')
    const [mapLoaded, setMapLoaded] = useState(false)
    const [selectedComplaint, setSelectedComplaint] = useState(null)

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

        map.addControl(
            new maplibregl.NavigationControl(),
            'top-right'
        )

        map.on('load', () => {
            map.resize()
            addComplaintHeatmap(map)

            // Handle complaint marker clicks
            // Handle complaint marker clicks
            let activePopup = null

            map.on('mouseenter', 'complaint-points', (event) => {
                const feature = event.features?.[0]
                if (!feature) return

                const complaint = complaints.find(
                    (item) => item.id === feature.properties.id
                )

                if (!complaint) return

                if (activePopup) {
                    activePopup.remove()
                }

                const popupContent = document.createElement('div')
                popupContent.className = 'complaint-popup'

                const header = document.createElement('div')
                header.className = 'popup-header'

                const id = document.createElement('strong')
                id.textContent = complaint.id

                const priority = document.createElement('span')
                priority.className = `priority-badge priority-${complaint.priority.toLowerCase()}`
                priority.textContent = complaint.priority

                header.append(id, priority)

                const title = document.createElement('h4')
                title.textContent = complaint.title

                const footer = document.createElement('div')
                footer.className = 'popup-footer'

                const status = document.createElement('span')
                status.className = `status-badge status-${complaint.status.toLowerCase().replaceAll(' ', '-')}`
                status.textContent = complaint.status

                footer.append(status)
                popupContent.append(header, title, footer)

                activePopup = new maplibregl.Popup({
                    closeButton: false,
                    closeOnClick: false,
                    maxWidth: '240px',
                    offset: 14,
                    className: 'civic-complaint-popup',
                })
                    .setLngLat(feature.geometry.coordinates)
                    .setDOMContent(popupContent)
                    .addTo(map)
            })

            map.on('mouseleave', 'complaint-points', () => {
                if (activePopup) {
                    activePopup.remove()
                    activePopup = null
                }
            })

            // Handle complaint marker clicks to show full details
            map.on('click', 'complaint-points', (event) => {
                const feature = event.features?.[0]

                if (!feature) return

                const complaint = complaints.find(
                    (item) => item.id === feature.properties.id
                )

                if (!complaint) return

                // Close the small hover popup
                if (activePopup) {
                    activePopup.remove()
                    activePopup = null
                }

                // Open the full complaint details panel
                setSelectedComplaint(complaint)
            })

            // Show pointer cursor over complaint markers
            map.on('mouseenter', 'complaint-points', () => {
                map.getCanvas().style.cursor = 'pointer'
            })

            map.on('mouseleave', 'complaint-points', () => {
                map.getCanvas().style.cursor = ''
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

    useEffect(() => {
        const map = mapRef.current

        if (!map || !mapLoaded) return

        map.setStyle(MAP_STYLES[theme])

        map.once('style.load', () => {
            addComplaintHeatmap(map)
        })
    }, [theme, mapLoaded])

    return (
        <div className={`civic-map-wrapper ${theme}-theme`}>

            <div className="civic-map-header">
                <div>
                    <span className="civic-map-eyebrow">
                        CIVICSYNC / GEOSPATIAL
                    </span>
                    <h2>Goa Civic Map</h2>
                    <p>Explore civic activity across Goa</p>
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


            {selectedComplaint && (
                <div className="complaint-details-panel">
                    <div className="complaint-panel-header">
                        <div>
                            <span className="civic-map-eyebrow">
                                COMPLAINT DETAILS
                            </span>

                            <h3>
                                {selectedComplaint.id}
                            </h3>
                        </div>

                        <button
                            className="complaint-close-button"
                            onClick={() => setSelectedComplaint(null)}
                        >
                            ✕
                        </button>
                    </div>

                    <div className="complaint-details-grid">

                        <div className="complaint-detail-item">
                            <span>Title</span>
                            <strong>{selectedComplaint.title}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Category</span>
                            <strong>{selectedComplaint.category}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Issue Type</span>
                            <strong>{selectedComplaint.issue_type}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Department</span>
                            <strong>{selectedComplaint.department}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Severity</span>
                            <strong>{selectedComplaint.severity}/10</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Priority</span>
                            <strong className={`priority-badge priority-${selectedComplaint.priority.toLowerCase()}`}>
                                {selectedComplaint.priority}
                            </strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Status</span>
                            <strong className={`status-badge status-${selectedComplaint.status.toLowerCase().replaceAll(' ', '-')}`}>
                                {selectedComplaint.status}
                            </strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Reports</span>
                            <strong>{selectedComplaint.report_count}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Latitude</span>
                            <strong>{selectedComplaint.latitude}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Longitude</span>
                            <strong>{selectedComplaint.longitude}</strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Date Reported</span>
                            <strong>
                                {new Date(selectedComplaint.created_at).toLocaleDateString('en-IN')}
                            </strong>
                        </div>

                        <div className="complaint-detail-item">
                            <span>Safety Related</span>
                            <strong>{selectedComplaint.safety_related ? 'Yes' : 'No'}</strong>
                        </div>

                        <div className="complaint-description">
                            <span>Description</span>
                            <p>{selectedComplaint.description}</p>
                        </div>

                        <a
                            className="google-maps-button"
                            href={`https://www.google.com/maps/dir/?api=1&destination=${selectedComplaint.latitude},${selectedComplaint.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            <span></span>
                            Get Directions on Google Maps
                        </a>

                    </div>
                </div>
            )}


            <div className="civic-map-container">
                {!mapLoaded && (
                    <div className="map-loading">
                        Loading Goa map...
                    </div>
                )}

                <div
                    ref={mapContainer}
                    className="civic-map-canvas"
                />
            </div>

            <div className="civic-map-footer">
                <span>GOA, INDIA</span>
                <span>MAP DATA © MAPTILER © OPENSTREETMAP</span>
            </div>

        </div>
    )
}
