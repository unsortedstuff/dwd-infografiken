const map = L.map("map", {
  scrollWheelZoom: true,
  zoomControl: true,
}).setView([51.15, 10.45], 6);

L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 18,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const countEl = document.querySelector("#station-count");
const emptyState = document.querySelector("#empty-state");
const card = document.querySelector("#station-card");
const stateEl = document.querySelector("#station-state");
const nameEl = document.querySelector("#station-name");
const idEl = document.querySelector("#station-id");
const heightEl = document.querySelector("#station-height");
const imageLink = document.querySelector("#image-link");
const imageEl = document.querySelector("#station-image");

let activeMarker = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function markerIcon(active = false) {
  return L.divIcon({
    className: "",
    html: `<span class="station-marker${active ? " is-active" : ""}"></span>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

function imageUrl(path) {
  return encodeURI(path);
}

function selectStation(station, marker) {
  if (activeMarker) {
    activeMarker.setIcon(markerIcon(false));
  }

  activeMarker = marker;
  activeMarker.setIcon(markerIcon(true));

  emptyState.classList.add("is-hidden");
  card.classList.remove("is-hidden");
  stateEl.textContent = station.state;
  nameEl.textContent = station.name;
  idEl.textContent = station.id;
  heightEl.textContent = `${station.height} m`;

  const src = imageUrl(station.image);
  imageLink.href = src;
  imageEl.src = src;
  imageEl.alt = `Infografik Heiße Tage in ${station.name}`;
}

async function init() {
  const response = await fetch("assets/stations.json");
  if (!response.ok) {
    throw new Error(`Stationsdaten konnten nicht geladen werden: ${response.status}`);
  }

  const stations = await response.json();
  countEl.textContent = stations.length.toLocaleString("de-DE");

  const bounds = [];
  stations.forEach((station) => {
    const marker = L.marker([station.lat, station.lon], {
      icon: markerIcon(false),
      title: station.name,
    }).addTo(map);

    marker.bindPopup(`
      <div class="popup-title">${escapeHtml(station.name)}</div>
      <div class="popup-subtitle">${escapeHtml(station.state)} · ${escapeHtml(station.id)}</div>
    `);
    marker.on("click", () => selectStation(station, marker));
    bounds.push([station.lat, station.lon]);
  });

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [28, 28] });
  }
}

init().catch((error) => {
  countEl.textContent = "!";
  emptyState.innerHTML = `
    <h2>Daten nicht geladen</h2>
    <p>${error.message}</p>
  `;
});
