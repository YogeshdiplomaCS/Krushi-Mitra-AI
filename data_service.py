import requests
from functools import lru_cache

TIMEOUT = (10, 45)

# Keyless public APIs:
# Market data: Mandi API
# Weather data: Open-Meteo


@lru_cache(maxsize=32)
def _mandi_get(endpoint, params_key=()):
    """Fetch and cache Mandi API data for a short time."""
    params = dict(params_key)
    response = requests.get(
        f"https://mandi-api.onrender.com/v1/{endpoint.lstrip('/')}",
        params=params,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    if not isinstance(result, dict):
        raise ValueError("Unexpected Mandi API response format.")

    if result.get("success") is False:
        error = result.get("message") or result.get("error") or "Unknown API error"
        raise ValueError(str(error))

    data = result.get("data", [])
    if not isinstance(data, list):
        raise ValueError("Unexpected Mandi API data format.")

    return data


def _fetch_mandi(endpoint, params=None):
    """Convert request parameters into a hashable cache key."""
    return _mandi_get(endpoint, tuple(sorted((params or {}).items())))


def get_market_prices(state="Karnataka", commodity=None, district=None, market=None):
    """
    Return agricultural market prices using the keyless Mandi API.

    The response structure is kept compatible with the previous data service:
    {'success': bool, 'data': list, 'message': str}
    """
    if not state or not str(state).strip():
        return {
            "success": False,
            "data": [],
            "message": "Select a state to search market prices.",
        }

    params = {"state": str(state).strip()}
    if market and str(market).strip():
        params["market"] = str(market).strip()
    if commodity and str(commodity).strip():
        params["commodity"] = str(commodity).strip()

    try:
        records = _fetch_mandi("prices", params)

        # The API filters can be partial-text matches. Apply exact local filters
        # where the requested field exists in each returned record.
        if district:
            wanted_district = str(district).strip().casefold()
            records = [
                row for row in records
                if wanted_district in str(
                    row.get("district") or row.get("District") or ""
                ).casefold()
            ]

        if market:
            wanted_market = str(market).strip().casefold()
            records = [
                row for row in records
                if wanted_market in str(
                    row.get("market") or row.get("Market") or ""
                ).casefold()
            ]

        if commodity:
            wanted_commodity = str(commodity).strip().casefold()
            records = [
                row for row in records
                if wanted_commodity in str(
                    row.get("commodity") or row.get("Commodity") or ""
                ).casefold()
            ]

        return {
            "success": True,
            "data": records,
            "message": (
                f"Received {len(records)} market records."
                if records
                else "No market records found for the selected filters."
            ),
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "data": [],
            "message": "Market API timed out. Please try again later.",
        }
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        return {
            "success": False,
            "data": [],
            "message": f"Mandi API HTTP {status}. Please try again later.",
        }
    except (requests.exceptions.RequestException, ValueError) as error:
        return {
            "success": False,
            "data": [],
            "message": f"Market API request failed: {error}",
        }


@lru_cache(maxsize=64)
def _geocode_city(city):
    """Resolve a city or town name to latitude and longitude."""
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()
    locations = result.get("results") or []

    if not locations:
        return None

    place = locations[0]
    return {
        "name": place.get("name", city),
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
    }


def get_weather(city):
    """Return current weather from Open-Meteo without requiring an API key."""
    if not city or not str(city).strip():
        return {
            "success": False,
            "data": {},
            "message": "Enter a city or town name.",
        }

    city = str(city).strip()

    try:
        place = _geocode_city(city)
        if not place:
            return {
                "success": False,
                "data": {},
                "message": f"Could not find '{city}'. Check the spelling or try a nearby town.",
            }

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "apparent_temperature,is_day,precipitation,"
                    "weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        current = result.get("current") or {}

        if not current:
            return {
                "success": False,
                "data": {},
                "message": "Weather provider returned no current conditions.",
            }

        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }

        code = current.get("weather_code")
        return {
            "success": True,
            "data": {
                "city": place["name"],
                "country": place["country"],
                "temperature": current.get("temperature_2m"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "description": weather_codes.get(code, "Conditions unavailable"),
                "wind_speed": current.get("wind_speed_10m"),
                "precipitation": current.get("precipitation"),
                "time": current.get("time"),
            },
            "message": "Current weather data retrieved successfully from Open-Meteo.",
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "data": {},
            "message": "Weather request timed out. Please try again later.",
        }
    except requests.exceptions.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        return {
            "success": False,
            "data": {},
            "message": f"Weather API HTTP {status}. Please try again later.",
        }
    except (requests.exceptions.RequestException, ValueError, KeyError, TypeError) as error:
        return {
            "success": False,
            "data": {},
            "message": f"Weather request failed: {error}",
        }
