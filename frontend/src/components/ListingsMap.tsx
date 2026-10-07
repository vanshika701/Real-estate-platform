import L, { type LatLngBoundsExpression } from "leaflet";
import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { Link } from "react-router-dom";

import { formatPriceShort } from "../lib/format";
import type { ListingSummary } from "../types/api";

const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const INDIA_CENTER: [number, number] = [22.5, 78.9];

/**
 * Price-label markers built from HTML (divIcon). They read better than generic pins and avoid
 * Leaflet's default marker images, which bundlers don't resolve without extra config.
 */
function priceIcon(price: number): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div class="price-marker">${formatPriceShort(price)}</div>`,
    iconSize: [0, 0],
  });
}

function FitToListings({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }, [map, bounds]);
  return null;
}

export function ListingsMap({ listings }: { listings: ListingSummary[] }) {
  const bounds = useMemo<LatLngBoundsExpression | null>(
    () => (listings.length ? listings.map((l) => [l.latitude, l.longitude] as [number, number]) : null),
    [listings],
  );

  return (
    <MapContainer
      center={INDIA_CENTER}
      zoom={5}
      scrollWheelZoom
      className="h-[60vh] min-h-[360px] w-full rounded-xl border border-slate-200"
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
      <FitToListings bounds={bounds} />
      {listings.map((listing) => (
        <Marker
          key={listing.id}
          position={[listing.latitude, listing.longitude]}
          icon={priceIcon(listing.price)}
          title={listing.title}
        >
          <Popup>
            <div className="space-y-1">
              <p className="font-semibold">{formatPriceShort(listing.price)}</p>
              <p className="text-sm">{listing.title}</p>
              <Link to={`/listings/${listing.id}`} className="text-sm font-medium text-brand-700">
                View details →
              </Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

export function SingleListingMap({
  latitude,
  longitude,
  label,
}: {
  latitude: number;
  longitude: number;
  label: string;
}) {
  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={14}
      scrollWheelZoom={false}
      className="h-72 w-full rounded-xl border border-slate-200"
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
      <Marker
        position={[latitude, longitude]}
        title={label}
        icon={L.divIcon({ className: "", html: '<div class="price-marker">📍 Here</div>', iconSize: [0, 0] })}
      />
    </MapContainer>
  );
}
