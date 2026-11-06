"""Timezone manager and GTK4 timezone picker widget for LSD-Welcome.

Provides:
- TimezoneManager: High-performance indexed timezone database, city searching,
  spherical coordinate proximity calculation, and map coordinate projection.
- TimezonePickerWidget / TimezoneMapWidget: GTK4 interactive world map component
  with pin marker, click-to-select, and city search bar.
"""

from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Callable
import unicodedata

# GTK4 import with headless safety
try:
    import gi
    gi.require_version("Gdk", "4.0")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gdk, Gtk
    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = object  # type: ignore


# Built-in fallback database of major global timezones and reference coordinates
DEFAULT_TIMEZONES: list[dict] = [
    # South America
    {"name": "America/Sao_Paulo", "city": "São Paulo", "country": "BR", "lat": -23.5505, "lon": -46.6333, "label": "America/Sao_Paulo (São Paulo, Brasil)"},
    {"name": "America/Manaus", "city": "Manaus", "country": "BR", "lat": -3.1190, "lon": -60.0217, "label": "America/Manaus (Manaus, Brasil)"},
    {"name": "America/Belem", "city": "Belém", "country": "BR", "lat": -1.4558, "lon": -48.4902, "label": "America/Belem (Belém, Brasil)"},
    {"name": "America/Fortaleza", "city": "Fortaleza", "country": "BR", "lat": -3.7319, "lon": -38.5267, "label": "America/Fortaleza (Fortaleza, Brasil)"},
    {"name": "America/Recife", "city": "Recife", "country": "BR", "lat": -8.0476, "lon": -34.8770, "label": "America/Recife (Recife, Brasil)"},
    {"name": "America/Cuiaba", "city": "Cuiabá", "country": "BR", "lat": -15.6014, "lon": -56.0979, "label": "America/Cuiaba (Cuiabá, Brasil)"},
    {"name": "America/Campo_Grande", "city": "Campo Grande", "country": "BR", "lat": -20.4697, "lon": -54.6201, "label": "America/Campo_Grande (Campo Grande, Brasil)"},
    {"name": "America/Porto_Velho", "city": "Porto Velho", "country": "BR", "lat": -8.7619, "lon": -63.9039, "label": "America/Porto_Velho (Porto Velho, Brasil)"},
    {"name": "America/Boa_Vista", "city": "Boa Vista", "country": "BR", "lat": 2.8235, "lon": -60.6758, "label": "America/Boa_Vista (Boa Vista, Brasil)"},
    {"name": "America/Rio_Branco", "city": "Rio Branco", "country": "BR", "lat": -9.9753, "lon": -67.8249, "label": "America/Rio_Branco (Rio Branco, Brasil)"},
    {"name": "America/Noronha", "city": "Fernando de Noronha", "country": "BR", "lat": -3.8573, "lon": -32.4297, "label": "America/Noronha (Fernando de Noronha, Brasil)"},
    {"name": "America/Bahia", "city": "Salvador", "country": "BR", "lat": -12.9777, "lon": -38.5016, "label": "America/Bahia (Salvador, Brasil)"},
    {"name": "America/Maceio", "city": "Maceió", "country": "BR", "lat": -9.6658, "lon": -35.7350, "label": "America/Maceio (Maceió, Brasil)"},
    {"name": "America/Argentina/Buenos_Aires", "city": "Buenos Aires", "country": "AR", "lat": -34.6037, "lon": -58.3816, "label": "America/Argentina/Buenos_Aires (Buenos Aires, Argentina)"},
    {"name": "America/Santiago", "city": "Santiago", "country": "CL", "lat": -33.4489, "lon": -70.6693, "label": "America/Santiago (Santiago, Chile)"},
    {"name": "America/Lima", "city": "Lima", "country": "PE", "lat": -12.0464, "lon": -77.0428, "label": "America/Lima (Lima, Peru)"},
    {"name": "America/Bogota", "city": "Bogotá", "country": "CO", "lat": 4.7110, "lon": -74.0721, "label": "America/Bogota (Bogotá, Colombia)"},
    {"name": "America/Caracas", "city": "Caracas", "country": "VE", "lat": 10.4806, "lon": -66.9036, "label": "America/Caracas (Caracas, Venezuela)"},
    {"name": "America/Montevideo", "city": "Montevideo", "country": "UY", "lat": -34.9011, "lon": -56.1645, "label": "America/Montevideo (Montevideo, Uruguai)"},
    {"name": "America/Asuncion", "city": "Assunção", "country": "PY", "lat": -25.2637, "lon": -57.5759, "label": "America/Asuncion (Assunção, Paraguai)"},
    {"name": "America/La_Paz", "city": "La Paz", "country": "BO", "lat": -16.5000, "lon": -68.1500, "label": "America/La_Paz (La Paz, Bolívia)"},

    # North America
    {"name": "America/New_York", "city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060, "label": "America/New_York (New York, EUA)"},
    {"name": "America/Chicago", "city": "Chicago", "country": "US", "lat": 41.8781, "lon": -87.6298, "label": "America/Chicago (Chicago, EUA)"},
    {"name": "America/Denver", "city": "Denver", "country": "US", "lat": 39.7392, "lon": -104.9903, "label": "America/Denver (Denver, EUA)"},
    {"name": "America/Los_Angeles", "city": "Los Angeles", "country": "US", "lat": 34.0522, "lon": -118.2437, "label": "America/Los_Angeles (Los Angeles, EUA)"},
    {"name": "America/Anchorage", "city": "Anchorage", "country": "US", "lat": 61.2181, "lon": -149.9003, "label": "America/Anchorage (Anchorage, EUA)"},
    {"name": "Pacific/Honolulu", "city": "Honolulu", "country": "US", "lat": 21.3069, "lon": -157.8583, "label": "Pacific/Honolulu (Honolulu, EUA)"},
    {"name": "America/Toronto", "city": "Toronto", "country": "CA", "lat": 43.6532, "lon": -79.3832, "label": "America/Toronto (Toronto, Canadá)"},
    {"name": "America/Vancouver", "city": "Vancouver", "country": "CA", "lat": 49.2827, "lon": -123.1207, "label": "America/Vancouver (Vancouver, Canadá)"},
    {"name": "America/Mexico_City", "city": "Cidade do México", "country": "MX", "lat": 19.4326, "lon": -99.1332, "label": "America/Mexico_City (Cidade do México, México)"},

    # Europe
    {"name": "Europe/London", "city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278, "label": "Europe/London (London, Reino Unido)"},
    {"name": "Europe/Paris", "city": "Paris", "country": "FR", "lat": 48.8566, "lon": 2.3522, "label": "Europe/Paris (Paris, França)"},
    {"name": "Europe/Berlin", "city": "Berlin", "country": "DE", "lat": 52.5200, "lon": 13.4050, "label": "Europe/Berlin (Berlin, Alemanha)"},
    {"name": "Europe/Lisbon", "city": "Lisboa", "country": "PT", "lat": 38.7223, "lon": -9.1393, "label": "Europe/Lisbon (Lisboa, Portugal)"},
    {"name": "Europe/Madrid", "city": "Madrid", "country": "ES", "lat": 40.4168, "lon": -3.7038, "label": "Europe/Madrid (Madrid, Espanha)"},
    {"name": "Europe/Rome", "city": "Roma", "country": "IT", "lat": 41.9028, "lon": 12.4964, "label": "Europe/Rome (Roma, Itália)"},
    {"name": "Europe/Amsterdam", "city": "Amsterdam", "country": "NL", "lat": 52.3676, "lon": 4.9041, "label": "Europe/Amsterdam (Amsterdam, Holanda)"},
    {"name": "Europe/Brussels", "city": "Bruxelas", "country": "BE", "lat": 50.8503, "lon": 4.3517, "label": "Europe/Brussels (Bruxelas, Bélgica)"},
    {"name": "Europe/Zurich", "city": "Zurique", "country": "CH", "lat": 47.3769, "lon": 8.5417, "label": "Europe/Zurich (Zurique, Suíça)"},
    {"name": "Europe/Vienna", "city": "Viena", "country": "AT", "lat": 48.2082, "lon": 16.3738, "label": "Europe/Vienna (Viena, Áustria)"},
    {"name": "Europe/Warsaw", "city": "Varsóvia", "country": "PL", "lat": 52.2297, "lon": 21.0122, "label": "Europe/Warsaw (Varsóvia, Polônia)"},
    {"name": "Europe/Athens", "city": "Atenas", "country": "GR", "lat": 37.9838, "lon": 23.7275, "label": "Europe/Athens (Atenas, Grécia)"},
    {"name": "Europe/Dublin", "city": "Dublin", "country": "IE", "lat": 53.3498, "lon": -6.2603, "label": "Europe/Dublin (Dublin, Irlanda)"},
    {"name": "Europe/Stockholm", "city": "Estocolmo", "country": "SE", "lat": 59.3293, "lon": 18.0686, "label": "Europe/Stockholm (Estocolmo, Suécia)"},
    {"name": "Europe/Oslo", "city": "Oslo", "country": "NO", "lat": 59.9139, "lon": 10.7522, "label": "Europe/Oslo (Oslo, Noruega)"},
    {"name": "Europe/Helsinki", "city": "Helsinque", "country": "FI", "lat": 60.1699, "lon": 24.9384, "label": "Europe/Helsinki (Helsinque, Finlândia)"},
    {"name": "Europe/Copenhagen", "city": "Copenhague", "country": "DK", "lat": 55.6761, "lon": 12.5683, "label": "Europe/Copenhagen (Copenhague, Dinamarca)"},
    {"name": "Europe/Kyiv", "city": "Kyiv", "country": "UA", "lat": 50.4501, "lon": 30.5234, "label": "Europe/Kyiv (Kyiv, Ucrânia)"},
    {"name": "Europe/Moscow", "city": "Moscou", "country": "RU", "lat": 55.7558, "lon": 37.6173, "label": "Europe/Moscow (Moscou, Rússia)"},

    # Asia & Middle East
    {"name": "Asia/Tokyo", "city": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503, "label": "Asia/Tokyo (Tóquio, Japão)"},
    {"name": "Asia/Shanghai", "city": "Shanghai", "country": "CN", "lat": 31.2304, "lon": 121.4737, "label": "Asia/Shanghai (Xangai, China)"},
    {"name": "Asia/Hong_Kong", "city": "Hong Kong", "country": "HK", "lat": 22.3193, "lon": 114.1694, "label": "Asia/Hong_Kong (Hong Kong, China)"},
    {"name": "Asia/Seoul", "city": "Seul", "country": "KR", "lat": 37.5665, "lon": 126.9780, "label": "Asia/Seoul (Seul, Coreia do Sul)"},
    {"name": "Asia/Singapore", "city": "Singapura", "country": "SG", "lat": 1.3521, "lon": 103.8198, "label": "Asia/Singapore (Singapura)"},
    {"name": "Asia/Bangkok", "city": "Bangkok", "country": "TH", "lat": 13.7563, "lon": 100.5018, "label": "Asia/Bangkok (Bangkok, Tailândia)"},
    {"name": "Asia/Jakarta", "city": "Jacarta", "country": "ID", "lat": -6.2088, "lon": 106.8456, "label": "Asia/Jakarta (Jacarta, Indonésia)"},
    {"name": "Asia/Kolkata", "city": "Kolkata", "country": "IN", "lat": 22.5726, "lon": 88.3639, "label": "Asia/Kolkata (Kolkata, Índia)"},
    {"name": "Asia/Dubai", "city": "Dubai", "country": "AE", "lat": 25.2048, "lon": 55.2708, "label": "Asia/Dubai (Dubai, EAU)"},
    {"name": "Asia/Riyadh", "city": "Riad", "country": "SA", "lat": 24.7136, "lon": 46.6753, "label": "Asia/Riyadh (Riad, Arábia Saudita)"},
    {"name": "Asia/Istanbul", "city": "Istambul", "country": "TR", "lat": 41.0082, "lon": 28.9784, "label": "Asia/Istanbul (Istambul, Turquia)"},
    {"name": "Asia/Jerusalem", "city": "Jerusalém", "country": "IL", "lat": 31.7683, "lon": 35.2137, "label": "Asia/Jerusalem (Jerusalém, Israel)"},

    # Oceania
    {"name": "Australia/Sydney", "city": "Sydney", "country": "AU", "lat": -33.8688, "lon": 151.2093, "label": "Australia/Sydney (Sydney, Austrália)"},
    {"name": "Australia/Melbourne", "city": "Melbourne", "country": "AU", "lat": -37.8136, "lon": 144.9631, "label": "Australia/Melbourne (Melbourne, Austrália)"},
    {"name": "Australia/Brisbane", "city": "Brisbane", "country": "AU", "lat": -27.4698, "lon": 153.0251, "label": "Australia/Brisbane (Brisbane, Austrália)"},
    {"name": "Australia/Perth", "city": "Perth", "country": "AU", "lat": -31.9505, "lon": 115.8605, "label": "Australia/Perth (Perth, Austrália)"},
    {"name": "Pacific/Auckland", "city": "Auckland", "country": "NZ", "lat": -36.8485, "lon": 174.7633, "label": "Pacific/Auckland (Auckland, Nova Zelândia)"},

    # Africa
    {"name": "Africa/Cairo", "city": "Cairo", "country": "EG", "lat": 30.0444, "lon": 31.2357, "label": "Africa/Cairo (Cairo, Egito)"},
    {"name": "Africa/Johannesburg", "city": "Johannesburg", "country": "ZA", "lat": -26.2041, "lon": 28.0473, "label": "Africa/Johannesburg (Johannesburgo, África do Sul)"},
    {"name": "Africa/Lagos", "city": "Lagos", "country": "NG", "lat": 6.5244, "lon": 3.3792, "label": "Africa/Lagos (Lagos, Nigéria)"},
    {"name": "Africa/Nairobi", "city": "Nairóbi", "country": "KE", "lat": -1.2921, "lon": 36.8219, "label": "Africa/Nairobi (Nairóbi, Quênia)"},
    {"name": "Africa/Casablanca", "city": "Casablanca", "country": "MA", "lat": 33.5731, "lon": -7.5898, "label": "Africa/Casablanca (Casablanca, Marrocos)"},

    # UTC / Universal
    {"name": "UTC", "city": "UTC", "country": "", "lat": 0.0, "lon": 0.0, "label": "UTC (Tempo Universal Coordenado)"},
]

# Common city synonyms and regional aliases mapping to canonical timezones
COMMON_CITY_ALIASES: dict[str, str] = {
    # Brazilian capitals & major cities
    "sao paulo": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "rio": "America/Sao_Paulo",
    "brasilia": "America/Sao_Paulo",
    "belo horizonte": "America/Sao_Paulo",
    "curitiba": "America/Sao_Paulo",
    "porto alegre": "America/Sao_Paulo",
    "florianopolis": "America/Sao_Paulo",
    "vitoria": "America/Sao_Paulo",
    "goiania": "America/Sao_Paulo",
    "salvador": "America/Bahia",
    "bahia": "America/Bahia",
    "fortaleza": "America/Fortaleza",
    "recife": "America/Recife",
    "belem": "America/Belem",
    "manaus": "America/Manaus",
    "cuiaba": "America/Cuiaba",
    "campo grande": "America/Campo_Grande",
    "porto velho": "America/Porto_Velho",
    "boa vista": "America/Boa_Vista",
    "rio branco": "America/Rio_Branco",
    "macapa": "America/Belem",
    "palmas": "America/Araguaina",
    "natal": "America/Fortaleza",
    "maceio": "America/Maceio",
    "joao pessoa": "America/Fortaleza",
    "aracaju": "America/Maceio",
    "teresina": "America/Fortaleza",
    "sao luis": "America/Fortaleza",
    "fernando de noronha": "America/Noronha",
    "noronha": "America/Noronha",

    # International cities
    "new york": "America/New_York",
    "nova york": "America/New_York",
    "nyc": "America/New_York",
    "washington": "America/New_York",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "chicago": "America/Chicago",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "denver": "America/Denver",
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "vancouver": "America/Vancouver",
    "cidade do mexico": "America/Mexico_City",
    "mexico city": "America/Mexico_City",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "lima": "America/Lima",
    "bogota": "America/Bogota",
    "caracas": "America/Caracas",
    "montevideo": "America/Montevideo",
    "assuncao": "America/Asuncion",
    "asuncion": "America/Asuncion",
    "la paz": "America/La_Paz",
    "paris": "Europe/Paris",
    "london": "Europe/London",
    "londres": "Europe/London",
    "berlin": "Europe/Berlin",
    "berlim": "Europe/Berlin",
    "lisboa": "Europe/Lisbon",
    "lisbon": "Europe/Lisbon",
    "madrid": "Europe/Madrid",
    "madri": "Europe/Madrid",
    "rome": "Europe/Rome",
    "roma": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam",
    "bruxelas": "Europe/Brussels",
    "brussels": "Europe/Brussels",
    "zurique": "Europe/Zurich",
    "zurich": "Europe/Zurich",
    "viena": "Europe/Vienna",
    "vienna": "Europe/Vienna",
    "varsovia": "Europe/Warsaw",
    "warsaw": "Europe/Warsaw",
    "atenas": "Europe/Athens",
    "athens": "Europe/Athens",
    "dublin": "Europe/Dublin",
    "estocolmo": "Europe/Stockholm",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "helsinque": "Europe/Helsinki",
    "helsinki": "Europe/Helsinki",
    "copenhague": "Europe/Copenhagen",
    "copenhagen": "Europe/Copenhagen",
    "kyiv": "Europe/Kyiv",
    "kiev": "Europe/Kyiv",
    "moscou": "Europe/Moscow",
    "moscow": "Europe/Moscow",
    "toquio": "Asia/Tokyo",
    "tokyo": "Asia/Tokyo",
    "pequim": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "xangai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "seul": "Asia/Seoul",
    "seoul": "Asia/Seoul",
    "singapura": "Asia/Singapore",
    "singapore": "Asia/Singapore",
    "bangkok": "Asia/Bangkok",
    "jacarta": "Asia/Jakarta",
    "jakarta": "Asia/Jakarta",
    "delhi": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "riad": "Asia/Riyadh",
    "riyadh": "Asia/Riyadh",
    "istambul": "Asia/Istanbul",
    "istanbul": "Asia/Istanbul",
    "jerusalem": "Asia/Jerusalem",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",
    "cairo": "Africa/Cairo",
    "johanesburgo": "Africa/Johannesburg",
    "johannesburg": "Africa/Johannesburg",
    "lagos": "Africa/Lagos",
    "nairobi": "Africa/Nairobi",
    "casablanca": "Africa/Casablanca",
}


def _normalize_string(text: str) -> str:
    """Removes diacritics, extra spaces, and lowercases string."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[_\-\s/]+", " ", no_accents)
    return cleaned.strip().lower()


def _parse_iso6709(coord_str: str) -> tuple[float, float] | None:
    """Parses ISO 6709 coordinate string (e.g. ±DDMM±DDDMM or ±DDMMSS±DDDMMSS)."""
    m = re.match(
        r"^([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?$",
        coord_str.strip(),
    )
    if not m:
        return None
    lat_sign, lat_deg, lat_min, lat_sec, lon_sign, lon_deg, lon_min, lon_sec = m.groups()
    lat = int(lat_deg) + int(lat_min) / 60.0 + (int(lat_sec) / 3600.0 if lat_sec else 0.0)
    if lat_sign == "-":
        lat = -lat
    lon = int(lon_deg) + int(lon_min) / 60.0 + (int(lon_sec) / 3600.0 if lon_sec else 0.0)
    if lon_sign == "-":
        lon = -lon
    return lat, lon


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two points."""
    r = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class TimezoneManager:
    """Manages timezone data, coordinate conversions, and city searches."""

    def __init__(self, zoneinfo_path: str | Path = "/usr/share/zoneinfo") -> None:
        self.zoneinfo_path = Path(zoneinfo_path)
        self._timezones: dict[str, dict] = {}
        self._city_to_tz: dict[str, str] = {}
        self._load_database()

    def _load_database(self) -> None:
        """Populates the timezone database from system zoneinfo and defaults."""
        # 1. Load built-in defaults first
        for tz in DEFAULT_TIMEZONES:
            self._register_entry(
                name=tz["name"],
                city=tz["city"],
                country=tz["country"],
                lat=tz["lat"],
                lon=tz["lon"],
                label=tz["label"],
            )

        # 2. Enrich from /usr/share/zoneinfo/zone1970.tab or zone.tab if present
        for tab_filename in ("zone1970.tab", "zone.tab"):
            tab_path = self.zoneinfo_path / tab_filename
            if tab_path.is_file():
                self._load_tab_file(tab_path)
                break

        # 3. Register predefined aliases
        for alias, tz_name in COMMON_CITY_ALIASES.items():
            norm_alias = _normalize_string(alias)
            if tz_name in self._timezones and norm_alias not in self._city_to_tz:
                self._city_to_tz[norm_alias] = tz_name

    def _load_tab_file(self, tab_path: Path) -> None:
        try:
            with tab_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    country = parts[0]
                    coord_str = parts[1]
                    tz_name = parts[2]
                    comment = parts[3] if len(parts) > 3 else ""

                    coords = _parse_iso6709(coord_str)
                    if not coords:
                        continue
                    lat, lon = coords

                    # Extract primary city name from timezone path (e.g. America/Sao_Paulo -> Sao Paulo)
                    city_candidate = tz_name.split("/")[-1].replace("_", " ")
                    label = f"{tz_name} ({city_candidate})"
                    if comment:
                        label += f" - {comment}"

                    # If already present from defaults, keep existing refined label/coords or update
                    if tz_name not in self._timezones:
                        self._register_entry(
                            name=tz_name,
                            city=city_candidate,
                            country=country,
                            lat=lat,
                            lon=lon,
                            label=label,
                        )
        except OSError:
            pass

    def _register_entry(
        self,
        name: str,
        city: str,
        country: str,
        lat: float,
        lon: float,
        label: str,
    ) -> None:
        entry = {
            "name": name,
            "timezone": name,
            "city": city,
            "country": country,
            "lat": lat,
            "lon": lon,
            "label": label,
        }
        self._timezones[name] = entry

        # Index by normalized city name
        norm_city = _normalize_string(city)
        if norm_city:
            self._city_to_tz[norm_city] = name

        # Also index by normalized last component of timezone name
        last_comp = _normalize_string(name.split("/")[-1])
        if last_comp and last_comp not in self._city_to_tz:
            self._city_to_tz[last_comp] = name

    def get_available_timezones(self) -> list[dict]:
        """Returns sorted list of all available timezones."""
        return sorted(self._timezones.values(), key=lambda x: x["name"])

    def get_timezone_info(self, tz_name: str) -> dict | None:
        """Returns metadata dictionary for a specific timezone name."""
        return self._timezones.get(tz_name)

    def find_timezone(self, city_query: str) -> str | None:
        """Finds timezone by city name, alias, or timezone identifier.
        
        Supports accented and non-accented queries, case insensitivity,
        and substring matching.
        """
        if not city_query or not city_query.strip():
            return None

        clean_query = city_query.strip()
        norm_query = _normalize_string(clean_query)

        # 1. Exact match on normalized city name or alias
        if norm_query in self._city_to_tz:
            return self._city_to_tz[norm_query]

        # 2. Exact match on raw timezone name
        if clean_query in self._timezones:
            return clean_query

        # 3. Match on normalized full timezone name (e.g. 'america sao paulo')
        for name, entry in self._timezones.items():
            if _normalize_string(name) == norm_query:
                return name

        # 4. Prefix match on city names / aliases
        for city_norm, tz_name in self._city_to_tz.items():
            if city_norm.startswith(norm_query):
                return tz_name

        # 5. Substring match on city names / aliases
        for city_norm, tz_name in self._city_to_tz.items():
            if norm_query in city_norm:
                return tz_name

        # 6. Substring match on full timezone name
        for name in self._timezones:
            if norm_query in _normalize_string(name):
                return name

        return None

    def find_timezone_by_city(self, city_query: str) -> str | None:
        """Alias for find_timezone."""
        return self.find_timezone(city_query)

    def coords_to_timezone(self, lat: float, lon: float) -> str:
        """Finds the closest timezone given latitude and longitude."""
        if not self._timezones:
            return "UTC"

        # Clamp latitude and normalize longitude to [-180, 180]
        clamped_lat = max(-90.0, min(90.0, float(lat)))
        wrapped_lon = ((float(lon) + 180.0) % 360.0) - 180.0

        best_tz = "UTC"
        min_dist = float("inf")

        for tz_name, data in self._timezones.items():
            dist = _haversine_distance(
                clamped_lat,
                wrapped_lon,
                data["lat"],
                data["lon"],
            )
            if dist < min_dist:
                min_dist = dist
                best_tz = tz_name

        return best_tz

    def coords_to_percent(self, lat: float, lon: float) -> tuple[float, float]:
        """Maps geographic coordinates to (x_pct, y_pct) in [0.0, 100.0] range."""
        clamped_lat = max(-90.0, min(90.0, float(lat)))
        wrapped_lon = ((float(lon) + 180.0) % 360.0) - 180.0

        x_pct = ((wrapped_lon + 180.0) / 360.0) * 100.0
        y_pct = ((90.0 - clamped_lat) / 180.0) * 100.0

        return max(0.0, min(100.0, round(x_pct, 4))), max(0.0, min(100.0, round(y_pct, 4)))

    def percent_to_coords(self, x_pct: float, y_pct: float) -> tuple[float, float]:
        """Maps (x_pct, y_pct) in [0.0, 100.0] range to geographic coordinates (lat, lon)."""
        clamped_x = max(0.0, min(100.0, float(x_pct)))
        clamped_y = max(0.0, min(100.0, float(y_pct)))

        lon = (clamped_x / 100.0) * 360.0 - 180.0
        lat = 90.0 - (clamped_y / 100.0) * 180.0

        return max(-90.0, min(90.0, round(lat, 4))), max(-180.0, min(180.0, round(lon, 4)))

    def percent_to_timezone(self, x_pct: float, y_pct: float) -> str:
        """Directly resolves map percentage coordinates to the closest timezone."""
        lat, lon = self.percent_to_coords(x_pct, y_pct)
        return self.coords_to_timezone(lat, lon)

    def timezone_to_coords(self, tz_name: str) -> tuple[float, float] | None:
        """Returns (lat, lon) anchor for the given timezone, or None."""
        info = self.get_timezone_info(tz_name)
        if info:
            return info["lat"], info["lon"]
        return None

    def timezone_to_percent(self, tz_name: str) -> tuple[float, float] | None:
        """Returns (x_pct, y_pct) map coordinates for the given timezone, or None."""
        coords = self.timezone_to_coords(tz_name)
        if coords:
            return self.coords_to_percent(coords[0], coords[1])
        return None


def get_world_map_asset_path() -> Path:
    """Finds the absolute path to world_map.png."""
    # 1. Project development directory
    local_asset = Path(__file__).resolve().parent.parent / "assets" / "world_map.png"
    if local_asset.is_file():
        return local_asset

    # 2. Installed system directory
    sys_asset = Path("/usr/share/lsd-welcome/assets/world_map.png")
    if sys_asset.is_file():
        return sys_asset

    # 3. Fallback to mockups if present
    mockup_asset = Path(__file__).resolve().parent.parent.parent.parent / "mockups" / "timezone.png"
    if mockup_asset.is_file():
        return mockup_asset

    return local_asset


class TimezonePickerWidget(Gtk.Box):  # type: ignore
    """GTK4 component for interactive timezone selection."""

    def __init__(
        self,
        tz_manager: TimezoneManager | None = None,
        initial_timezone: str = "America/Sao_Paulo",
        headless: bool = False,
        **kwargs,
    ) -> None:
        self.tz_manager = tz_manager or TimezoneManager()
        self._selected_timezone = initial_timezone
        self._selected_city = self._resolve_city_name(initial_timezone)
        self._callbacks: list[Callable[[str], None]] = []

        # Check headless or missing display server
        is_headless = headless or (
            not GTK_AVAILABLE
            or not hasattr(Gdk, "Display")
            or Gdk.Display.get_default() is None
        )
        self._headless = is_headless

        if self._headless:
            # Safe stub initialization without native GObject C instantiation
            return

        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12, **kwargs)
        self._build_ui()

    def _resolve_city_name(self, tz_name: str) -> str:
        info = self.tz_manager.get_timezone_info(tz_name)
        if info and info.get("city"):
            return info["city"]
        return tz_name.split("/")[-1].replace("_", " ")

    def _build_ui(self) -> None:
        """Constructs the GTK4 UI widgets."""
        # Top search container
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.search_entry = Gtk.SearchEntry(
            placeholder_text="Buscar cidade (ex: São Paulo, New York, Paris)...",
            hexpand=True,
        )
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_search_activated)
        search_box.append(self.search_entry)
        self.append(search_box)

        # Map display container
        self.overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        self.map_picture = Gtk.Picture.new_for_filename(str(get_world_map_asset_path()))
        self.map_picture.set_can_shrink(True)
        self.map_picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.overlay.set_child(self.map_picture)

        # Pin marker label/icon
        self.pin_label = Gtk.Label(label="📍")
        self.pin_label.add_css_class("title-1")
        self.pin_label.set_halign(Gtk.Align.START)
        self.pin_label.set_valign(Gtk.Align.START)
        self.overlay.add_overlay(self.pin_label)

        # Map click gesture
        click_gesture = Gtk.GestureClick.new()
        click_gesture.connect("released", self._on_map_clicked)
        self.map_picture.add_controller(click_gesture)

        self.append(self.overlay)

        # Bottom info label
        self.status_label = Gtk.Label(
            label=f"Fuso Selecionado: {self._selected_timezone} ({self._selected_city})",
            halign=Gtk.Align.CENTER,
        )
        self.status_label.add_css_class("heading")
        self.append(self.status_label)

        # Sync initial pin position
        self._update_pin_position()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text().strip()
        if len(query) >= 3:
            match = self.tz_manager.find_timezone(query)
            if match:
                self.set_selected_timezone(match, update_entry=False)

    def _on_search_activated(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text().strip()
        match = self.tz_manager.find_timezone(query)
        if match:
            self.set_selected_timezone(match, update_entry=False)

    def _on_map_clicked(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        widget_w = self.map_picture.get_width()
        widget_h = self.map_picture.get_height()
        if widget_w <= 0 or widget_h <= 0:
            return

        x_pct = (x / float(widget_w)) * 100.0
        y_pct = (y / float(widget_h)) * 100.0
        nearest_tz = self.tz_manager.percent_to_timezone(x_pct, y_pct)
        if nearest_tz:
            self.set_selected_timezone(nearest_tz, update_entry=True)

    def _update_pin_position(self) -> None:
        if self._headless:
            return
        pct = self.tz_manager.timezone_to_percent(self._selected_timezone)
        if pct and hasattr(self, "pin_label"):
            x_pct, y_pct = pct
            widget_w = self.map_picture.get_width() or 557
            widget_h = self.map_picture.get_height() or 373
            pin_x = int((x_pct / 100.0) * widget_w) - 12
            pin_y = int((y_pct / 100.0) * widget_h) - 24
            self.pin_label.set_margin_start(max(0, pin_x))
            self.pin_label.set_margin_top(max(0, pin_y))

    def get_selected_timezone(self) -> str:
        """Returns current selected timezone identifier."""
        return self._selected_timezone

    def get_selected_city(self) -> str:
        """Returns current selected city name."""
        return self._selected_city

    def set_selected_timezone(self, tz_name: str, update_entry: bool = True) -> bool:
        """Sets the active timezone and notifies subscribers."""
        if not tz_name:
            return False

        info = self.tz_manager.get_timezone_info(tz_name)
        self._selected_timezone = tz_name
        self._selected_city = self._resolve_city_name(tz_name)

        if not self._headless:
            city_info = f" ({self._selected_city})" if self._selected_city else ""
            if hasattr(self, "status_label"):
                self.status_label.set_label(f"Fuso Selecionado: {self._selected_timezone}{city_info}")
            if update_entry and hasattr(self, "search_entry"):
                self.search_entry.set_text(self._selected_city or tz_name)
            self._update_pin_position()

        for cb in self._callbacks:
            try:
                cb(self._selected_timezone)
            except Exception:
                pass

        return True

    def connect_timezone_changed(self, callback: Callable[[str], None]) -> None:
        """Registers a callback invoked whenever the selected timezone changes."""
        self._callbacks.append(callback)


# Alias for backward and forward compatibility
TimezoneMapWidget = TimezonePickerWidget
