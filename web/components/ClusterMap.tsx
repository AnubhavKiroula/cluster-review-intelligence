"use client";

// Map of the cluster: one labelled point per property, coloured by its status, and
// any neighbourhood-wide decline drawn as a shaded circle. Plotly's MapLibre map
// (`scattermap`) on an OpenFreeMap basemap: no API key, attribution shown by MapLibre.
//
// Zoom: + / - / reset buttons, Ctrl (or Cmd) + scroll, and a two-finger pinch.
// MapLibre's "cooperative gestures" keep a plain scroll or one-finger swipe for the
// page, so the map never traps scrolling.
import { useEffect, useRef, useState } from "react";
import Plot from "@/components/Plot";
import type { Neighbourhood, PropertyLocation } from "@/lib/data";
import { usePalette } from "@/lib/theme";

export interface MapPoint {
  id: string;
  /** Short status word shown next to the point, so colour is not the only cue. */
  status: string;
  color: string;
  /** The property the page is about: drawn larger. */
  focus?: boolean;
}

// The labels must use a font the basemap style serves (OpenFreeMap: Noto Sans).
const MAP_FONT = "Noto Sans Regular";
const KM_PER_DEG = 111.2;
const TILE_PX = 512;
// Town level to street level: further out the map is mostly empty, further in the
// SYNTHETIC positions would suggest more precision than they have.
const MIN_ZOOM = 10;
const MAX_ZOOM = 17;

// The part of MapLibre's Map this component uses (Plotly does not export the type).
interface MapLibreMap {
  jumpTo(options: { center?: [number, number]; zoom?: number }, eventData?: object): void;
  getZoom(): number;
  getCenter(): { lng: number; lat: number };
  setMinZoom(z: number): void;
  setMaxZoom(z: number): void;
  on(event: "moveend", listener: () => void): void;
  cooperativeGestures?: { enable(): void };
}

interface View {
  center: { lat: number; lon: number };
  zoom: number;
}

const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function circle(lat: number, lon: number, radiusKm: number, steps = 64) {
  const lats: number[] = [];
  const lons: number[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = (2 * Math.PI * i) / steps;
    lats.push(lat + (radiusKm / KM_PER_DEG) * Math.sin(t));
    lons.push(lon + (radiusKm / (KM_PER_DEG * Math.cos((lat * Math.PI) / 180))) * Math.cos(t));
  }
  return { lats, lons };
}

// Zoom that fits the points into a map of about `width` x `height` px. MapLibre's
// zoom is defined on 512 px tiles: at zoom z one tile spans 360 / 2^z degrees of
// longitude (web mercator); latitude degrees are shorter on screen by cos(latitude).
function fit(locations: PropertyLocation[], width: number, height: number) {
  const lats = locations.map((l) => l.lat);
  const lons = locations.map((l) => l.lon);
  const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const lon = (Math.min(...lons) + Math.max(...lons)) / 2;
  const pad = 1.35;
  const spanLon = Math.max(Math.max(...lons) - Math.min(...lons), 0.002) * pad;
  const spanLat = Math.max(Math.max(...lats) - Math.min(...lats), 0.002) * pad;
  const zLon = Math.log2((360 * width) / (TILE_PX * spanLon));
  const zLat = Math.log2((360 * height * Math.cos((lat * Math.PI) / 180)) / (TILE_PX * spanLat));
  return { center: { lat, lon }, zoom: Math.min(16, Math.max(MIN_ZOOM, Math.min(zLon, zLat))) };
}

export default function ClusterMap({
  locations,
  points,
  neighbourhoods = [],
  height = 440,
  summary,
}: {
  locations: PropertyLocation[];
  points: MapPoint[];
  neighbourhoods?: Neighbourhood[];
  height?: number;
  summary: string;
}) {
  const C = usePalette();
  const mapRef = useRef<MapLibreMap | null>(null);
  // The starting view, fitted once to the screen; Reset returns to it.
  const [home] = useState<View>(() =>
    fit(locations, typeof window === "undefined" ? 1000 : Math.min(window.innerWidth - 32, 1040), height),
  );
  // Only for the buttons' disabled state; updated once a move ends.
  const [zoom, setZoom] = useState(home.zoom);
  const animating = useRef(false);

  // Configure the MapLibre map as soon as Plotly has created it. Plotly's own "drawn"
  // callback only fires once the basemap has loaded (seconds later), so poll the
  // chart element from mount instead; a new map (Plotly may rebuild it) is
  // configured again.
  const wrapRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const configure = (map: MapLibreMap) => {
      mapRef.current = map;
      map.setMinZoom(MIN_ZOOM);
      map.setMaxZoom(MAX_ZOOM);
      map.cooperativeGestures?.enable();
      map.on("moveend", () => {
        if (!animating.current) setZoom(map.getZoom());
      });
    };
    const timer = window.setInterval(() => {
      const gd = wrapRef.current?.querySelector(".js-plotly-plot");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const map = (gd as any)?._fullLayout?.map?._subplot?.map as MapLibreMap | undefined;
      if (map && map !== mapRef.current) configure(map);
    }, 100);
    return () => window.clearInterval(timer);
  }, []);

  // Move over ~250 ms with jumpTo: in the MapLibre build bundled with Plotly 2.35,
  // easeTo / zoomIn / zoomTo leave the view unchanged, while jumpTo works.
  // Each jump carries an `originalEvent`, so Plotly records it as the visitor's own
  // view (as it does for a drag) and, with `uirevision`, keeps it when the page
  // re-renders or the basemap style changes.
  const moveTo = (target: View) => {
    const map = mapRef.current;
    if (!map) return;
    const z1 = clampZoom(target.zoom);
    const jump = (z: number, lon: number, lat: number) =>
      map.jumpTo({ zoom: z, center: [lon, lat] }, { originalEvent: { type: "map-control" } });
    const finish = () => {
      animating.current = false;
      setZoom(map.getZoom());
    };
    if (reducedMotion()) {
      jump(z1, target.center.lon, target.center.lat);
      finish();
      return;
    }
    const z0 = map.getZoom();
    const c0 = map.getCenter();
    const start = performance.now();
    animating.current = true;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 250);
      const e = 1 - (1 - t) ** 3; // ease-out
      jump(
        z0 + (z1 - z0) * e,
        c0.lng + (target.center.lon - c0.lng) * e,
        c0.lat + (target.center.lat - c0.lat) * e,
      );
      if (t < 1) requestAnimationFrame(step);
      else finish();
    };
    requestAnimationFrame(step);
  };
  const zoomBy = (delta: number) => {
    const map = mapRef.current;
    if (!map) return;
    const c = map.getCenter();
    moveTo({ center: { lat: c.lat, lon: c.lng }, zoom: map.getZoom() + delta });
  };
  const reset = () => moveTo(home);

  const byId = new Map(locations.map((l) => [l.property_id, l]));
  const shown = points.filter((p) => byId.has(p.id));
  const letter = (id: string) => id.replace(/^Property\s+/, "");

  const areas = neighbourhoods.map((h) => {
    // Pad the circle so the outermost members sit inside it, not on its edge.
    const ring = circle(h.centre_lat, h.centre_lon, Math.max(h.radius_km, 0.1) + 0.12);
    return {
      type: "scattermap",
      mode: "lines",
      fill: "toself",
      fillcolor: `${C.marigold}2E`,
      line: { color: C.marigold, width: 2 },
      lat: ring.lats,
      lon: ring.lons,
      hoverinfo: "text",
      text: `${h.aspect}: neighbourhood-wide decline since ${h.change_month} (${h.n_members} properties)`,
      showlegend: false,
    };
  });

  const markers = {
    type: "scattermap",
    mode: "markers+text",
    lat: shown.map((p) => byId.get(p.id)!.lat),
    lon: shown.map((p) => byId.get(p.id)!.lon),
    marker: { size: shown.map((p) => (p.focus ? 20 : 14)), color: shown.map((p) => p.color), opacity: 0.95 },
    text: shown.map((p) => `${letter(p.id)} ${p.status}`),
    textposition: "top right",
    textfont: { family: MAP_FONT, size: 12, color: C.ink },
    hovertext: shown.map((p) => `${p.id}: ${p.status}`),
    hoverinfo: "text",
    showlegend: false,
  };

  return (
    <div className="map-wrap" ref={wrapRef}>
      <Plot
        height={height}
        summary={summary}
        data={[...areas, markers]}
        layout={{
          margin: { l: 0, r: 0, t: 0, b: 0 },
          // uirevision: Plotly keeps the visitor's pan and zoom (drags, Ctrl+scroll and
          // the buttons) when the page re-renders or the basemap style changes.
          map: { style: C.mapStyle, center: home.center, zoom: home.zoom, uirevision: "cluster-map" },
          uirevision: "cluster-map",
          showlegend: false,
        }}
        // Scroll zoom is on, but cooperative: only with Ctrl/Cmd (see attach).
        config={{ scrollZoom: true }}
      />
      <div className="map-controls" role="group" aria-label="Map zoom">
        <button
          type="button"
          onClick={() => zoomBy(1)}
          aria-label="Zoom in"
          disabled={zoom >= MAX_ZOOM - 0.01}
        >
          <span aria-hidden>+</span>
        </button>
        <button
          type="button"
          onClick={() => zoomBy(-1)}
          aria-label="Zoom out"
          disabled={zoom <= MIN_ZOOM + 0.01}
        >
          <span aria-hidden>−</span>
        </button>
        <button type="button" onClick={reset} aria-label="Reset map view" className="map-reset">
          Reset
        </button>
      </div>
    </div>
  );
}
