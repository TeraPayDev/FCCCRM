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
import { useNavigate } from "react-router-dom";
import { milestone78Api, roadmapApi, type GeographicArea } from "../api/client";
import { loadTokens } from "../auth/session";
import "./map.css";

type Feature = {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: { type: string; coordinates: unknown };
};
type Toggles = {
  temperature: boolean;
  rainfall: boolean;
  trees: boolean;
  waterways: boolean;
  boundary: boolean;
  governed: boolean;
};
const initial: Toggles = {
  temperature: true,
  rainfall: false,
  trees: true,
  waterways: true,
  boundary: true,
  governed: true,
};
function features(payload: Record<string, unknown> | null) {
  const raw = payload?.features;
  return Array.isArray(raw)
    ? raw.filter((f): f is Feature => Boolean(f && typeof f === "object"))
    : [];
}

export function MapPage() {
  const navigate = useNavigate();
  const node = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const [areas, setAreas] = useState<GeographicArea[]>([]);
  const [reference, setReference] = useState<Record<string, unknown> | null>(null);
  const [weatherGrid, setWeatherGrid] = useState<Record<string, unknown> | null>(null);
  const [toggles, setToggles] = useState<Toggles>(initial);
  const [coordinates, setCoordinates] = useState("Move pointer over map");
  const [error, setError] = useState("");
  useEffect(() => {
    const tok = loadTokens();
    if (!tok) {
      navigate("/login?reason=expired");
      return;
    }
    let cancelled = false;
    const load = async () => {
      const [a, r, g] = await Promise.allSettled([
        milestone78Api.geographicAreas(tok.access_token),
        roadmapApi.object(tok.access_token, "/api/v1/public-data/gis/reference"),
        roadmapApi.object(tok.access_token, "/api/v1/public-data/weather/grid"),
      ]);
      if (cancelled) return;
      if (a.status === "fulfilled") setAreas(a.value);
      if (r.status === "fulfilled") setReference(r.value);
      if (g.status === "fulfilled") setWeatherGrid(g.value);
      const errs = [a, r, g]
        .filter((x) => x.status === "rejected")
        .map((x) =>
          x.status === "rejected" && x.reason instanceof Error
            ? x.reason.message
            : "Layer unavailable",
        );
      setError(errs.join(" "));
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [navigate]);
  useEffect(() => {
    if (!node.current || mapRef.current) return;
    const map = new Map({
      container: node.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.82 } }],
      },
      center: [-13.24, 8.455],
      zoom: 11,
    });
    map.addControl(new NavigationControl(), "top-right");
    map.addControl(new ScaleControl({ unit: "metric" }));
    map.on("mousemove", (e: MapMouseEvent) =>
      setCoordinates(`${e.lngLat.lng.toFixed(5)}, ${e.lngLat.lat.toFixed(5)}`),
    );
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !reference) return;
    const apply = () => {
      const fc = { type: "FeatureCollection" as const, features: features(reference) };
      const src = map.getSource("reference");
      if (src instanceof GeoJSONSource) src.setData(fc);
      else {
        map.addSource("reference", { type: "geojson", data: fc });
        map.addLayer({
          id: "waterways",
          type: "line",
          source: "reference",
          filter: ["==", ["get", "kind"], "waterway"],
          paint: { "line-color": "#277fb5", "line-width": 2.4, "line-opacity": 0.85 },
        });
        map.addLayer({
          id: "boundary",
          type: "line",
          source: "reference",
          filter: ["==", ["get", "kind"], "administrative-boundary"],
          paint: { "line-color": "#736b91", "line-width": 2.8, "line-dasharray": [3, 2] },
        });
        map.addLayer({
          id: "trees",
          type: "circle",
          source: "reference",
          filter: ["==", ["get", "kind"], "tree"],
          paint: {
            "circle-color": "#20835f",
            "circle-radius": 4,
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 1,
            "circle-opacity": 0.85,
          },
        });
        for (const id of ["waterways", "boundary", "trees"]) {
          map.on("click", id, (e: MapLayerMouseEvent) => {
            const f = e.features?.[0];
            if (!f) return;
            new Popup()
              .setLngLat(e.lngLat)
              .setHTML(
                `<strong>${String(f.properties?.name ?? f.properties?.kind ?? "Feature")}</strong><br/>Source: ${String(f.properties?.source ?? "OpenStreetMap")}`,
              )
              .addTo(map);
          });
        }
      }
    };
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [reference]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !weatherGrid) return;
    const apply = () => {
      const fc = { type: "FeatureCollection" as const, features: features(weatherGrid) };
      const src = map.getSource("weather-grid");
      if (src instanceof GeoJSONSource) src.setData(fc);
      else {
        map.addSource("weather-grid", { type: "geojson", data: fc });
        map.addLayer({
          id: "temperature",
          type: "heatmap",
          source: "weather-grid",
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["to-number", ["get", "temperature_c"]],
              22,
              0.15,
              31,
              1,
            ],
            "heatmap-intensity": 1.3,
            "heatmap-radius": 65,
            "heatmap-opacity": 0.7,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(50,130,180,0)",
              0.2,
              "#5bb7d3",
              0.48,
              "#86ca72",
              0.72,
              "#f1c34d",
              1,
              "#d9534f",
            ],
          },
        });
        map.addLayer({
          id: "rainfall",
          type: "heatmap",
          source: "weather-grid",
          layout: { visibility: "none" },
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["to-number", ["get", "precipitation_mm"]],
              0,
              0,
              1,
              0.3,
              8,
              1,
            ],
            "heatmap-intensity": 1.4,
            "heatmap-radius": 65,
            "heatmap-opacity": 0.75,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(30,100,180,0)",
              0.25,
              "#a5dded",
              0.55,
              "#4ba8d6",
              0.8,
              "#2d6eb2",
              1,
              "#173d78",
            ],
          },
        });
        map.addLayer({
          id: "weather-points",
          type: "circle",
          source: "weather-grid",
          paint: {
            "circle-radius": 4,
            "circle-color": "#fff",
            "circle-stroke-color": "#245f7b",
            "circle-stroke-width": 1.5,
          },
        });
        map.on("click", "weather-points", (e: MapLayerMouseEvent) => {
          const f = e.features?.[0];
          if (!f) return;
          new Popup()
            .setLngLat(e.lngLat)
            .setHTML(
              `<strong>${String(f.properties?.name ?? "Weather grid")}</strong><br/>Temperature: ${String(f.properties?.temperature_c ?? "—")} °C<br/>Precipitation: ${String(f.properties?.precipitation_mm ?? "—")} mm<br/>Source: Open-Meteo`,
            )
            .addTo(map);
        });
      }
    };
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [weatherGrid]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const set = (id: string, on: boolean) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    };
    set("temperature", toggles.temperature);
    set("rainfall", toggles.rainfall);
    set("trees", toggles.trees);
    set("waterways", toggles.waterways);
    set("boundary", toggles.boundary);
    set("cram-area-fill", toggles.governed);
    set("cram-area-line", toggles.governed);
  }, [toggles]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !areas.length) return;
    const fs = areas
      .filter((a) => a.geometry)
      .map((a) => ({
        type: "Feature" as const,
        id: a.id,
        properties: { name: a.name, code: a.code, area_type: a.area_type },
        geometry: a.geometry as never,
      }));
    const apply = () => {
      const fc = { type: "FeatureCollection" as const, features: fs };
      const src = map.getSource("governed");
      if (src instanceof GeoJSONSource) src.setData(fc);
      else {
        map.addSource("governed", { type: "geojson", data: fc });
        map.addLayer({
          id: "cram-area-fill",
          type: "fill",
          source: "governed",
          paint: { "fill-color": "#1f9d78", "fill-opacity": 0.13 },
        });
        map.addLayer({
          id: "cram-area-line",
          type: "line",
          source: "governed",
          paint: { "line-color": "#13725a", "line-width": 2 },
        });
      }
    };
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [areas]);
  const toggle = (key: keyof Toggles) => setToggles((s) => ({ ...s, [key]: !s[key] }));
  return (
    <div className="map-page">
      <aside>
        <p className="eyebrow">Spatial intelligence</p>
        <h1>GIS Explorer</h1>
        <p className="map-intro">
          Combine live public reference data with governed FCC spatial layers.
        </p>
        <div className="map-side-section">
          <h2>Layers</h2>
          {(
            [
              ["temperature", "Temperature surface", "heat"],
              ["rainfall", "Rainfall surface", "rain"],
              ["trees", "Trees", "tree"],
              ["waterways", "Waterways / drainage", "water"],
              ["boundary", "Administrative boundary", "boundary"],
              ["governed", "Governed CRAM layers", "governed"],
            ] as const
          ).map(([key, label, kind]) => (
            <label className="map-layer-row" key={key}>
              <input type="checkbox" checked={toggles[key]} onChange={() => toggle(key)} />
              <span className={`legend-swatch ${kind}`} />
              <span>{label}</span>
            </label>
          ))}
        </div>
        <div className="map-side-section">
          <h2>Legend & provenance</h2>
          <p className="map-note">
            <strong>Public reference:</strong> Open-Meteo and OpenStreetMap provide situational
            context.
          </p>
          <p className="map-note">
            <strong>Governed:</strong> FCC/partner layers remain authoritative CRAM records.
          </p>
        </div>
        {error && <div className="map-error">{error}</div>}
      </aside>
      <section className="map-canvas">
        <div className="coordinate-readout">{coordinates}</div>
        <div className="map-overlay-title">
          <strong>Freetown integrated climate map</strong>
          <span>Temperature · rainfall · trees · waterways · governed layers</span>
        </div>
        <div ref={node} className="map-root" />
      </section>
    </div>
  );
}
