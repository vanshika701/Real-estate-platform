import L from "leaflet";
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const PIN = L.divIcon({ className: "", html: '<div class="price-marker">📍 Here</div>', iconSize: [0, 0] });

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: (e) => onPick(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))),
  });
  return null;
}

/** Click the map to set the listing's coordinates (the lat/lng inputs stay editable too). */
export function LocationPicker({
  latitude,
  longitude,
  onPick,
}: {
  latitude: number | null;
  longitude: number | null;
  onPick: (lat: number, lng: number) => void;
}) {
  const hasPoint = latitude !== null && longitude !== null && Number.isFinite(latitude) && Number.isFinite(longitude);
  return (
    <MapContainer
      center={hasPoint ? [latitude, longitude] : [22.5, 78.9]}
      zoom={hasPoint ? 14 : 5}
      className="h-64 w-full rounded-lg border border-slate-300"
    >
      <TileLayer url={TILE_URL} attribution={ATTRIBUTION} />
      <ClickHandler onPick={onPick} />
      {hasPoint && <Marker position={[latitude, longitude]} icon={PIN} />}
    </MapContainer>
  );
}
