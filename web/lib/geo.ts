// Small geography helpers shared by the market and property maps.
import type { Neighbourhood, PropertyLocation, Snapshot } from "@/lib/data";
import type { Palette } from "@/lib/theme";

const EARTH_RADIUS_KM = 6371.0088; // same constant as cri.locations

export function haversineKm(a: PropertyLocation, b: PropertyLocation): number {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLon = (b.lon - a.lon) * rad;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(Math.min(1, h)));
}

/** Distance from each located property to its nearest located neighbour. */
export function nearestKm(locations: PropertyLocation[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const a of locations) {
    let best = Infinity;
    for (const b of locations) if (b !== a) best = Math.min(best, haversineKm(a, b));
    out.set(a.property_id, best);
  }
  return out;
}

export interface Status {
  word: string;
  color: string;
}

/** What a property's point says for one aspect, strongest evidence first: a shared
 * neighbourhood decline, then the property's own dated decline relative to the
 * market (which a whole-period average can hide), then its lead/lag flag. */
export function statusFor(
  data: Snapshot,
  propertyId: string,
  aspect: string,
  C: Palette,
  hood: Neighbourhood | undefined,
): Status {
  if (hood?.members.includes(propertyId)) return { word: "shared decline", color: C.marigold };
  const pdata = data.per_property[propertyId];
  const declined = pdata?.changepoints.some((c) => c.aspect === aspect && c.direction === "negative");
  if (declined) return { word: "declined", color: C.buransh };
  const row = pdata?.scorecard.find((r) => r.aspect === aspect);
  if (!row) return { word: "no reviews", color: C.stone };
  if (row.flag === "lag") return { word: "behind", color: C.buransh };
  if (row.flag === "lead") return { word: "ahead", color: C.deodar };
  return { word: "on par", color: C.stone };
}

/** Caption line saying what the positions are (CLAUDE.md rules 2 and 4). */
export function positionsNote(data: Snapshot): string {
  if (data.meta.is_synthetic && data.locations_exact)
    return "SYNTHETIC properties at generated positions in Mussoorie, not real hotels.";
  return "Positions are rounded to a 0.5 km grid so that no property can be identified.";
}
