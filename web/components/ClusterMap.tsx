"use client";

// Map of the cluster: one labelled point per property, coloured by its status, and
// any neighbourhood-wide decline drawn as a shaded circle. Plotly's MapLibre map
// (`scattermap`) on an OpenFreeMap basemap: no API key, attribution shown by MapLibre.
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
  return { center: { lat, lon }, zoom: Math.min(16, Math.max(10, Math.min(zLon, zLat))) };
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
    <Plot
      height={height}
      summary={summary}
      data={[...areas, markers]}
      layout={{
        margin: { l: 0, r: 0, t: 0, b: 0 },
        // The map fills the content column: the viewport minus the page gutters.
        map: {
          style: C.mapStyle,
          ...fit(locations, typeof window === "undefined" ? 1000 : Math.min(window.innerWidth - 32, 1040), height),
        },
        showlegend: false,
      }}
      // Wheel-zoom would trap the page's scrolling; dragging still pans the map.
      config={{ scrollZoom: false }}
    />
  );
}
