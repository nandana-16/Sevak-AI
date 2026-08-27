import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const RISK_COLOR = { HIGH: "#C0392B", MEDIUM: "#A9740A", LOW: "#1E7F4F" };
const RISK_RADIUS = { HIGH: 14, MEDIUM: 10, LOW: 7 };

export default function HeatmapView({ points }) {
  const center = points.length ? [points[0].lat, points[0].lng] : [18.52, 73.85];
  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={10} style={{ height: "420px", width: "100%", borderRadius: "12px" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map((p, i) => (
          <CircleMarker
            key={i}
            center={[p.lat, p.lng]}
            radius={RISK_RADIUS[p.risk_level] || 6}
            pathOptions={{ color: RISK_COLOR[p.risk_level] || "#888", fillOpacity: 0.6 }}
          >
            <Popup>
              <strong>{p.village}</strong><br />
              {p.risk_level} risk · {p.patient_count} case(s)
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
