
import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import goaBoundary from '../data/goaBoundary'


const goaCities = [
    {
        name: 'Panaji',
        longitude: 73.8278,
        latitude: 15.4909,
    },
    {
        name: 'Margao',
        longitude: 73.9862,
        latitude: 15.2832,
    },
    {
        name: 'Vasco da Gama',
        longitude: 73.8113,
        latitude: 15.3982,
    },
    {
        name: 'Mapusa',
        longitude: 73.8080,
        latitude: 15.5915,
    },
    {
        name: 'Ponda',
        longitude: 74.0120,
        latitude: 15.4010,
    },
    {
        name: 'Bicholim',
        longitude: 73.9457,
        latitude: 15.5937,
    },
]


function createGoaClippingCollection() {
    const polygons = goaBoundary.geometry.coordinates.map((polygon) => {
        // Each MultiPolygon component contains one or more rings.
        // The first ring is its exterior boundary.
        const ring = polygon[0]

        // Remove the duplicate closing coordinate if present.
        const first = ring[0]
        const last = ring[ring.length - 1]

        const isClosed =
            first[0] === last[0] && first[1] === last[1]

        const coordinates = isClosed ? ring.slice(0, -1) : ring

        const positions = Cesium.Cartesian3.fromDegreesArray(
            coordinates.flatMap(([longitude, latitude]) => [
                longitude,
                latitude,
            ])
        )

        return new Cesium.ClippingPolygon({ positions })
    })

    return new Cesium.ClippingPolygonCollection({
        polygons,
        inverse: true,
    })
}

function Goa3DMap() {
    const mapRef = useRef(null)
    const viewerRef = useRef(null)

    const [status, setStatus] = useState('Loading 3D map...')
    const [error, setError] = useState('')

    useEffect(() => {
        let cancelled = false
        let viewer

        async function initializeMap() {
            try {
                const token = import.meta.env.VITE_CESIUM_ION_TOKEN

                if (!token) {
                    throw new Error(
                        'Cesium token not found. Check your .env file.'
                    )
                }

                Cesium.Ion.defaultAccessToken = token

                viewer = new Cesium.Viewer(mapRef.current, {
                    terrain: Cesium.Terrain.fromWorldTerrain(),
                    animation: false,
                    timeline: false,
                    baseLayerPicker: false,
                    geocoder: false,
                    homeButton: false,
                    sceneModePicker: false,
                    navigationHelpButton: false,
                    fullscreenButton: false,
                    infoBox: false,
                    selectionIndicator: false,
                })

                viewerRef.current = viewer

                viewer.scene.requestRenderMode = false
                viewer.resolutionScale = Math.min(
                    window.devicePixelRatio || 1,
                    2
                )

                const animationStart = Cesium.JulianDate.now()

                // Warm ivory background outside Goa.
                viewer.scene.backgroundColor =
                    Cesium.Color.fromCssColorString('#F4F0E5')

                viewer.scene.skyBox.show = false
                viewer.scene.skyAtmosphere.show = false
                viewer.scene.globe.showGroundAtmosphere = false

                // Hide the globe outside Goa's boundary.
                viewer.scene.globe.clippingPolygons =
                    createGoaClippingCollection()

                // Restore realistic aerial imagery.
                viewer.imageryLayers.removeAll()

                const aerialProvider =
                    await Cesium.IonImageryProvider.fromAssetId(2)

                if (cancelled) return

                const aerialLayer =
                    viewer.imageryLayers.addImageryProvider(aerialProvider)

                // Softer, illustrated-atlas colour treatment
                aerialLayer.saturation = 0.72
                aerialLayer.brightness = 1.08
                aerialLayer.contrast = 0.92
                aerialLayer.gamma = 1.05

                // Draw a subtle outline around every Goa polygon.
                goaBoundary.geometry.coordinates.forEach((polygon) => {
                    const ring = polygon[0]

                    const positions = ring.map(([longitude, latitude]) =>
                        Cesium.Cartesian3.fromDegrees(longitude, latitude, 100)
                    )

                    viewer.entities.add({
                        polyline: {
                            positions,
                            width: 4,
                            material: Cesium.Color.fromCssColorString(
                                '#526B43'
                            ),
                            clampToGround: true,
                        },
                    })
                })


                // Add city markers across Goa
                goaCities.forEach((city) => {
                    viewer.entities.add({
                        name: city.name,

                        position: Cesium.Cartesian3.fromDegrees(
                            city.longitude,
                            city.latitude,
                            100
                        ),


                        point: {
                            pixelSize: new Cesium.CallbackProperty((time) => {
                                const seconds = Cesium.JulianDate.secondsDifference(
                                    time,
                                    animationStart
                                )

                                return 9 + Math.sin(seconds * 2.2) * 2
                            }, false),

                            color: new Cesium.CallbackProperty((time) => {
                                const seconds = Cesium.JulianDate.secondsDifference(
                                    time,
                                    animationStart
                                )

                                const pulse = (Math.sin(seconds * 2.2) + 1) / 2

                                return Cesium.Color.fromCssColorString('#64DCC2')
                                    .withAlpha(0.65 + pulse * 0.35)
                            }, false),

                            outlineColor: Cesium.Color.WHITE,
                            outlineWidth: 2,

                            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                        },

                        show: true,

                        label: {
                            text: city.name,

                            font: '600 19px Inter, Arial, sans-serif',

                            fillColor: Cesium.Color.fromCssColorString('#FFFFFF'),
                            outlineColor: Cesium.Color.fromCssColorString('#18352D'),
                            outlineWidth: 3,

                            style: Cesium.LabelStyle.FILL_AND_OUTLINE,

                            showBackground: true,
                            backgroundColor: Cesium.Color.fromCssColorString(
                                '#102B24CC'
                            ),
                            backgroundPadding: new Cesium.Cartesian2(9, 6),

                            pixelOffset: new Cesium.Cartesian2(0, -25),

                            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,

                            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,

                            disableDepthTestDistance: Number.POSITIVE_INFINITY,
                        },

                    })
                })

                const cityClickHandler = new Cesium.ScreenSpaceEventHandler(
                    viewer.scene.canvas
                )

                cityClickHandler.setInputAction((click) => {
                    const pickedObject = viewer.scene.pick(click.position)

                    if (!Cesium.defined(pickedObject) || !pickedObject.id) {
                        return
                    }

                    const selectedCity = goaCities.find(
                        (city) => city.name === pickedObject.id.name
                    )

                    if (!selectedCity) return

                    viewer.camera.flyTo({
                        destination: Cesium.Cartesian3.fromDegrees(
                            selectedCity.longitude,
                            selectedCity.latitude,
                            14000
                        ),
                        orientation: {
                            heading: Cesium.Math.toRadians(0),
                            pitch: Cesium.Math.toRadians(-55),
                            roll: 0,
                        },
                        duration: 2.5,
                    })

                }, Cesium.ScreenSpaceEventType.LEFT_CLICK)


                // Calculate the complete Goa boundary extent.
                const allCoordinates =
                    goaBoundary.geometry.coordinates.flatMap((polygon) =>
                        polygon.flatMap((ring) => ring)
                    )

                const longitudes = allCoordinates.map((point) => point[0])
                const latitudes = allCoordinates.map((point) => point[1])

                const west = Math.min(...longitudes)
                const east = Math.max(...longitudes)
                const south = Math.min(...latitudes)
                const north = Math.max(...latitudes)

                const goaRectangle = Cesium.Rectangle.fromDegrees(
                    west - 0.08,
                    south - 0.08,
                    east + 0.08,
                    north + 0.08
                )


                viewer.camera.flyTo({
                    destination: goaRectangle,
                    duration: 3,
                })


                setStatus('Loading 3D buildings...')

                // Load and clip the OpenStreetMap 3D buildings.
                const buildings = await Cesium.createOsmBuildingsAsync({
                    defaultColor: Cesium.Color.fromCssColorString('#D9CBB5'),
                    showOutline: true,
                })

                if (cancelled) {
                    buildings.destroy()
                    return
                }

                buildings.clippingPolygons =
                    createGoaClippingCollection()

                viewer.scene.primitives.add(buildings)

                setStatus('Goa 3D map ready')
            } catch (err) {
                console.error('Cesium error:', err)

                if (!cancelled) {
                    setError(err.message || 'Unable to load the 3D map.')
                    setStatus('Map loading failed')
                }
            }
        }

        initializeMap()

        return () => {
            cancelled = true

            if (viewer && !viewer.isDestroyed()) {
                viewer.destroy()
            }

            viewerRef.current = null
        }
    }, [])

    return (
        <div className="goa-map-wrapper">
            <div className="map-top-label">
                <div>
                    <span className="map-eyebrow">
                        CIVICSYNC / GEOSPATIAL
                    </span>
                    <h2>Goa 3D City View</h2>
                </div>

                <span className="map-live-status">
                    <span className="status-dot"></span>
                    {status}
                </span>
            </div>

            {error && (
                <div className="map-error">
                    {error}
                </div>
            )}

            <div className="cesium-map" ref={mapRef}></div>

            <div className="map-footer">
                <span>GOA, INDIA</span>
                <span>OPENSTREETMAP 3D BUILDINGS</span>
            </div>
        </div>
    )
}

export default Goa3DMap
