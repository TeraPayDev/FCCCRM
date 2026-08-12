import { useEffect, useRef } from "react";
import { GeoJSONSource, Map, NavigationControl, Popup, type MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import "./climate-map.css";

type Feature = {
  type: "Feature";
  properties: Record<string, unknown>;
  geometry: { type: string; coordinates: unknown };
};

type Props = {
  features: Feature[];
  weatherGrid?: Feature[];
  mode: "trees" | "flood" | "heat" | "all";
  height?: number;
};

export function ClimateMap({ features, weatherGrid = [], mode, height = 360 }: Props) {
  const node = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
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
      center: [-13.235, 8.455],
      zoom: 11.2,
    });
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const fc = { type: "FeatureCollection" as const, features };
      const existing = map.getSource("context");
      if (existing instanceof GeoJSONSource) existing.setData(fc);
      else {
        map.addSource("context", { type: "geojson", data: fc });
        map.addLayer({
          id: "waterways",
          type: "line",
          source: "context",
          filter: ["==", ["get", "kind"], "waterway"],
          paint: { "line-color": "#2e83b8", "line-width": 2.5, "line-opacity": 0.85 },
        });
        map.addLayer({
          id: "trees",
          type: "circle",
          source: "context",
          filter: ["==", ["get", "kind"], "tree"],
          paint: {
            "circle-color": "#23845e",
            "circle-radius": 4,
            "circle-opacity": 0.82,
            "circle-stroke-color": "#fff",
            "circle-stroke-width": 1,
          },
        });
        map.addLayer({
          id: "boundary",
          type: "line",
          source: "context",
          filter: ["==", ["get", "kind"], "administrative-boundary"],
          paint: { "line-color": "#6c7b87", "line-width": 2.2, "line-dasharray": [3, 2] },
        });
        for (const id of ["waterways", "trees", "boundary"]) {
          map.on("click", id, (event: MapLayerMouseEvent) => {
            const f = event.features?.[0];
            if (!f) return;
            new Popup()
              .setLngLat(event.lngLat)
              .setHTML(
                `<strong>${String(f.properties?.name ?? f.properties?.kind ?? "Feature")}</strong><br/>Source: ${String(f.properties?.source ?? "CRAM")}`,
              )
              .addTo(map);
          });
        }
      }
      const grid = { type: "FeatureCollection" as const, features: weatherGrid };
      const gridSource = map.getSource("weather-grid");
      if (gridSource instanceof GeoJSONSource) gridSource.setData(grid);
      else {
        map.addSource("weather-grid", { type: "geojson", data: grid });
        map.addLayer({
          id: "temperature-heat",
          type: "heatmap",
          source: "weather-grid",
          maxzoom: 14,
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["to-number", ["get", "temperature_c"]],
              22,
              0.2,
              31,
              1,
            ],
            "heatmap-intensity": 1.25,
            "heatmap-radius": 56,
            "heatmap-opacity": 0.72,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(36,119,183,0)",
              0.25,
              "#69b7d6",
              0.5,
              "#75c97d",
              0.72,
              "#f4c95d",
              1,
              "#dd6655",
            ],
          },
        });
        map.addLayer({
          id: "rain-heat",
          type: "heatmap",
          source: "weather-grid",
          maxzoom: 14,
          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              ["to-number", ["get", "precipitation_mm"]],
              0,
              0,
              2,
              0.4,
              8,
              1,
            ],
            "heatmap-intensity": 1.35,
            "heatmap-radius": 54,
            "heatmap-opacity": 0.74,
            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0,
              "rgba(36,119,183,0)",
              0.3,
              "#9bd6eb",
              0.55,
              "#3e9bd1",
              0.8,
              "#286bb3",
              1,
              "#16447c",
            ],
          },
        });
      }
      const visible = (id: string, on: boolean) =>
        map.getLayer(id) && map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
      visible("trees", mode === "trees" || mode === "all");
      visible("waterways", mode === "flood" || mode === "all");
      visible("boundary", mode === "all");
      visible("temperature-heat", mode === "heat" || mode === "all");
      visible("rain-heat", mode === "flood");
    };
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [features, weatherGrid, mode]);
  return <div className="climate-map" style={{ height }} ref={node} />;
}
