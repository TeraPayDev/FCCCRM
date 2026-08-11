import { useEffect, useRef, useState } from "react";
import {
  GeoJSONSource,
  Map,
  NavigationControl,
  Popup,
  ScaleControl,
  type MapLayerMouseEvent,
  type MapMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Link, useNavigate } from "react-router-dom";

import { milestone78Api, type GeographicArea, type SpatialLayer } from "../api/client";
import { loadTokens } from "../auth/session";
import "./map.css";

type GeoJsonGeometry =
  | {
      type: "Point";
      coordinates: number[];
    }
  | {
      type: "MultiPoint";
      coordinates: number[][];
    }
  | {
      type: "LineString";
      coordinates: number[][];
    }
  | {
      type: "MultiLineString";
      coordinates: number[][][];
    }
  | {
      type: "Polygon";
      coordinates: number[][][];
    }
  | {
      type: "MultiPolygon";
      coordinates: number[][][][];
    };

type AreaFeature = {
  type: "Feature";
  id: string;
  properties: Record<string, unknown>;
  geometry: GeoJsonGeometry;
};

type AreaFeatureCollection = {
  type: "FeatureCollection";
  features: AreaFeature[];
};

export function MapPage() {
  const navigate = useNavigate();

  const mapNode = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);

  const [layers, setLayers] = useState<SpatialLayer[]>([]);
  const [areas, setAreas] = useState<GeographicArea[]>([]);
  const [coordinates, setCoordinates] = useState("Move pointer over map");
  const [error, setError] = useState("");

  useEffect(() => {
    const tokens = loadTokens();

    if (!tokens) {
      navigate("/login");
      return;
    }

    const accessToken = tokens.access_token;
    let cancelled = false;

    async function loadSpatialData() {
      try {
        const [layerData, areaData] = await Promise.all([
          milestone78Api.spatialLayers(accessToken),
          milestone78Api.geographicAreas(accessToken),
        ]);

        if (cancelled) {
          return;
        }

        setLayers(layerData);
        setAreas(areaData);
      } catch (caught) {
        if (cancelled) {
          return;
        }

        setError(caught instanceof Error ? caught.message : "Unable to load GIS data.");
      }
    }

    void loadSpatialData();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    if (!mapNode.current || mapRef.current) {
      return;
    }

    const map = new Map({
      container: mapNode.current,
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: "background",
            type: "background",
            paint: {
              "background-color": "#eef2f5",
            },
          },
        ],
      },
      center: [-13.25, 8.45],
      zoom: 10,
    });

    map.addControl(new NavigationControl(), "top-right");

    map.addControl(
      new ScaleControl({
        unit: "metric",
      }),
    );

    map.on("mousemove", (event: MapMouseEvent) => {
      setCoordinates(`${event.lngLat.lng.toFixed(5)}, ${event.lngLat.lat.toFixed(5)}`);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;

    if (!map || areas.length === 0) {
      return;
    }

    const activeMap: Map = map;

    const features: AreaFeature[] = areas
      .filter(
        (
          area,
        ): area is GeographicArea & {
          geometry: GeoJsonGeometry;
        } => area.geometry !== null,
      )
      .map((area) => ({
        type: "Feature",
        id: area.id,
        properties: {
          code: area.code,
          name: area.name,
          area_type: area.area_type,
          ...area.metadata,
        },
        geometry: area.geometry,
      }));

    const collection: AreaFeatureCollection = {
      type: "FeatureCollection",
      features,
    };

    function applySpatialLayers() {
      const existingSource = activeMap.getSource("cram-areas");

      if (existingSource instanceof GeoJSONSource) {
        existingSource.setData(collection);
        return;
      }

      activeMap.addSource("cram-areas", {
        type: "geojson",
        data: collection,
      });

      activeMap.addLayer({
        id: "cram-area-fill",
        type: "fill",
        source: "cram-areas",
        paint: {
          "fill-opacity": 0.25,
        },
      });

      activeMap.addLayer({
        id: "cram-area-line",
        type: "line",
        source: "cram-areas",
        paint: {
          "line-width": 2,
        },
      });

      const geoserverBase =
        `${window.location.protocol}//` + `${window.location.hostname}:8080/geoserver/cram/wms`;

      activeMap.addSource("cram-geoserver", {
        type: "raster",
        tiles: [
          `${geoserverBase}` +
            "?service=WMS" +
            "&version=1.1.1" +
            "&request=GetMap" +
            "&layers=cram:geographic_areas" +
            "&styles=" +
            "&bbox={bbox-epsg-3857}" +
            "&width=256" +
            "&height=256" +
            "&srs=EPSG:3857" +
            "&format=image/png" +
            "&transparent=true",
        ],
        tileSize: 256,
      });

      activeMap.addLayer({
        id: "cram-geoserver-published",
        type: "raster",
        source: "cram-geoserver",
        paint: {
          "raster-opacity": 0.35,
        },
      });

      activeMap.on("click", "cram-area-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];

        if (!feature) {
          return;
        }

        const properties = feature.properties ?? {};

        new Popup()
          .setLngLat(event.lngLat)
          .setHTML(
            [
              `<strong>${String(properties.name ?? "Area")}</strong>`,
              `Code: ${String(properties.code ?? "")}`,
              `Type: ${String(properties.area_type ?? "")}`,
            ].join("<br/>"),
          )
          .addTo(activeMap);
      });
    }

    if (activeMap.loaded()) {
      applySpatialLayers();
    } else {
      activeMap.once("load", applySpatialLayers);
    }
  }, [areas]);

  function toggleLayer(visible: boolean) {
    const map = mapRef.current;

    if (!map) {
      return;
    }

    const layerIds = ["cram-area-fill", "cram-area-line", "cram-geoserver-published"];

    for (const id of layerIds) {
      if (map.getLayer(id)) {
        map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
      }
    }
  }

  return (
    <main className="map-page">
      <aside>
        <h1>CRAM GIS</h1>

        <p>Foundation map and spatial-layer verification.</p>

        <Link to="/profile">Profile</Link>

        <h2>Layers</h2>

        {layers.map((layer) => (
          <label key={layer.id}>
            <input
              type="checkbox"
              defaultChecked
              onChange={(event) => toggleLayer(event.target.checked)}
            />{" "}
            {layer.name}
          </label>
        ))}

        <p className="map-note">
          Synthetic acceptance geometry is not an authoritative Freetown hierarchy.
        </p>

        {error && <p className="map-error">{error}</p>}
      </aside>

      <section className="map-stage">
        <div ref={mapNode} className="map-canvas" />

        <output className="map-coordinates">{coordinates}</output>
      </section>
    </main>
  );
}
