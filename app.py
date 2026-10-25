import json
from io import BytesIO
import requests
import pandas as pd
import streamlit as st
from auth import render_auth_gate

# Optional online text-to-speech (no API key; internet required)
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# Optional speech recognition for Streamlit microphone recordings
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

from ai_service import chat_with_ai, analyze_image

# Voice input uses Streamlit's built-in microphone recorder (st.audio_input).
VOICE_AVAILABLE = hasattr(st, "audio_input") and SPEECH_RECOGNITION_AVAILABLE

# Optional GPS
try:
    from streamlit_geolocation import streamlit_geolocation
    GPS_AVAILABLE = True
except ImportError:
    GPS_AVAILABLE = False

# Optional interactive map
try:
    import folium
    from streamlit_folium import st_folium
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Krushi Mitra AI",
    page_icon="🌱",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --farm-deep: #14532d;
        --farm-green: #16a34a;
        --farm-soft: #e8f3e5;
        --farm-bg: #f5f9f3;
        --farm-border: #dce9d8;
        --farm-text: #183323;
    }

    .stApp {
        background: radial-gradient(circle at 8% 0%, #edf7e9 0, transparent 30%), var(--farm-bg);
        color: var(--farm-text);
    }

    [data-testid="stHeader"] { background: rgba(245, 249, 243, 0.88); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e8f3e5 0%, #f2f8ef 100%);
        border-right: 1px solid #d4e5d0;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #345642; }
    [data-testid="stSidebar"] h1 {
        color: var(--farm-deep);
        font-size: 1.45rem;
        letter-spacing: -0.5px;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 0.42rem 0.55rem;
        border-radius: 10px;
        transition: background 0.18s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: #d8ead3; }

    .block-container {
        padding-top: 1.7rem;
        padding-bottom: 3rem;
        max-width: 1440px;
    }

    h1, h2, h3 { color: var(--farm-deep); letter-spacing: -0.35px; }
    h2 { margin-top: 0.5rem; }
    [data-testid="stCaptionContainer"] { color: #597261; }

    .hero {
        position: relative;
        overflow: hidden;
        padding: clamp(24px, 4vw, 38px);
        border-radius: 24px;
        color: white;
        background: linear-gradient(118deg, #104526 0%, #168344 58%, #35b565 100%);
        box-shadow: 0 12px 28px rgba(20, 83, 45, 0.15);
        margin: 0 0 26px 0;
        border: 1px solid rgba(255,255,255,0.22);
    }
    .hero::after {
        content: "";
        position: absolute;
        width: 210px;
        height: 210px;
        border-radius: 50%;
        right: -58px;
        top: -95px;
        background: rgba(255,255,255,0.09);
        box-shadow: -78px 135px 0 12px rgba(255,255,255,0.055);
        pointer-events: none;
    }
    .hero h1 {
        color: white;
        margin: 0 0 8px 0;
        font-size: clamp(1.65rem, 3vw, 2.25rem);
        line-height: 1.2;
        font-weight: 800;
        position: relative;
        z-index: 1;
    }
    .hero p {
        color: rgba(255,255,255,0.91);
        font-size: 1.02rem;
        margin: 0;
        line-height: 1.6;
        max-width: 760px;
        position: relative;
        z-index: 1;
    }

    .info-card {
        height: 100%;
        min-height: 150px;
        background: linear-gradient(145deg, #ffffff 0%, #f8fcf6 100%);
        padding: 22px;
        border-radius: 18px;
        border: 1px solid var(--farm-border);
        box-shadow: 0 5px 16px rgba(25, 72, 39, 0.045);
        margin-bottom: 14px;
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }
    .info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(25, 72, 39, 0.09);
    }
    .info-card h3 { margin: 0 0 10px 0; font-size: 1.12rem; }
    .info-card p { margin: 0; color: #526b5a; line-height: 1.65; }

    div.stButton > button, [data-testid="stDownloadButton"] button {
        border-radius: 12px;
        font-weight: 650;
        border: 1px solid #cfe2ca;
        transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
        min-height: 2.65rem;
    }
    div.stButton > button[kind="primary"], button[kind="primary"] {
        background: linear-gradient(110deg, #14532d, #16a34a);
        color: #ffffff;
        border: 0;
        box-shadow: 0 5px 12px rgba(22, 163, 74, 0.16);
    }
    div.stButton > button:hover, [data-testid="stDownloadButton"] button:hover {
        transform: translateY(-1px);
        border-color: #78b883;
        box-shadow: 0 7px 16px rgba(20, 83, 45, 0.12);
    }

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input {
        border-radius: 12px;
        border-color: #d4e5d0;
        background: #ffffff;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        border-radius: 11px;
        border-color: #d4e5d0;
    }
    [data-testid="stFileUploader"] section {
        background: #fbfef9;
        border: 1px dashed #a9cba4;
        border-radius: 16px;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--farm-border);
        border-radius: 14px;
        background: rgba(255,255,255,0.72);
        overflow: hidden;
    }
    [data-testid="stTabs"] [role="tab"] { font-weight: 650; }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: var(--farm-deep);
        border-bottom-color: var(--farm-green);
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--farm-border);
        border-radius: 15px;
        padding: 14px 16px;
        box-shadow: 0 4px 12px rgba(25, 72, 39, 0.04);
    }
    [data-testid="stAlert"] { border-radius: 13px; }
    [data-testid="stChatMessage"] {
        border: 1px solid #e0ebdc;
        border-radius: 16px;
        padding: 12px 16px;
        margin-bottom: 10px;
        background: rgba(255,255,255,0.82);
    }
    [data-testid="stChatInput"] textarea { border-radius: 14px; }
    hr { border-color: #dce9d8; }

    @media (max-width: 700px) {
        .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
        .hero { border-radius: 18px; padding: 23px 20px; }
        .info-card { padding: 17px; border-radius: 15px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# LANGUAGES
# AI output and voice use the selected language.
# All application menus and labels remain in English.
# ---------------------------------------------------------

LANGUAGES = {
    "Kannada": {
        "ai": "Kannada",
        "voice": "kn-IN",
    },
    "English": {
        "ai": "English",
        "voice": "en-IN",
    },
    "Hindi": {
        "ai": "Hindi",
        "voice": "hi-IN",
    },
    "Telugu": {
        "ai": "Telugu",
        "voice": "te-IN",
    },
    "Tamil": {
        "ai": "Tamil",
        "voice": "ta-IN",
    },
}


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

defaults = {
    "messages": [],
    "language": "Kannada",
    "weather_coords": None,
    "weather_place": "",
    "weather_search_results": [],
    "weather_search_label": "",
    "last_answer": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Require account login before showing the farming application.
if not render_auth_gate():
    st.stop()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.title("🌱 Krushi Mitra AI")
    st.caption("Your smart farming companion")
    current_user = st.session_state.get("auth_user", {})
    if current_user:
        st.caption(f"👤 {current_user.get('full_name', 'Farmer')}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.pop("auth_user", None)
            st.session_state.messages = []
            st.rerun()

    selected_language = st.selectbox(
        "🌐 Output Language",
        list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(
            st.session_state.language
        ),
    )

    st.session_state.language = selected_language

    language = LANGUAGES[selected_language]["ai"]
    voice_language = LANGUAGES[selected_language]["voice"]

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "💬 AI Chat",
            "🖼️ Crop Image Analysis",
            "🌦️ Weather",
            "📊 Market Prices",
            "ℹ️ About",
        ],
    )

    st.divider()

    if st.button("🗑️ Clear Chat", width="stretch"):
        st.session_state.messages = []
        st.session_state.last_answer = ""
        st.rerun()

    st.caption("Made for smarter farming 🌾")


# ---------------------------------------------------------
# COMMON FUNCTIONS
# ---------------------------------------------------------

def show_hero(title, subtitle):
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def speak_text(text, lang, key="read_aloud"):
    """Offer on-demand speech so network TTS does not slow every AI reply."""
    if not text:
        return

    language_codes = {
        "kn-IN": "kn", "en-IN": "en", "hi-IN": "hi",
        "te-IN": "te", "ta-IN": "ta",
    }
    language_code = language_codes.get(lang, "kn")

    if not GTTS_AVAILABLE:
        st.info("For online voice playback, install gTTS: pip install gTTS")
        return

    if st.button("🔊 Generate / Play voice", key=key):
        try:
            with st.spinner("Generating audio…"):
                audio_buffer = BytesIO()
                gTTS(text=str(text), lang=language_code, slow=False).write_to_fp(audio_buffer)
                audio_buffer.seek(0)
            st.audio(audio_buffer.getvalue(), format="audio/mp3")
        except Exception as error:
            st.error("Voice generation failed. Check your internet connection and try again.")
            print(f"TTS error: {error}")


def transcribe_recording(audio_file, language_code):
    """Convert a recorded WAV clip to text with a bounded network timeout."""
    if audio_file is None:
        return ""
    if not SPEECH_RECOGNITION_AVAILABLE:
        st.error("Voice input needs SpeechRecognition. Run: pip install SpeechRecognition")
        return ""
    try:
        recognizer = sr.Recognizer()
        recognizer.operation_timeout = 12
        with sr.AudioFile(BytesIO(audio_file.getvalue())) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data, language=language_code)
    except sr.UnknownValueError:
        st.warning("I could not understand that recording. Speak clearly and try again.")
    except sr.RequestError as error:
        st.error(f"Speech recognition service is unavailable: {error}")
    except Exception as error:
        st.error(f"Could not process the recording: {error}")
    return ""


# ---------------------------------------------------------
# WEATHER FUNCTIONS
# Open-Meteo requires no API key.
# ---------------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def search_place(place_name):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={
            "name": place_name,
            "count": 10,
            "language": "en",
            "format": "json",
            "countryCode": "IN",
        },
        timeout=20,
    )

    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        return []

    return results


@st.cache_data(ttl=300, show_spinner=False)
def get_weather(latitude, longitude):
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "daily": (
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max"
            ),
            "forecast_days": 5,
            "timezone": "auto",
        },
        timeout=25,
    )

    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Weather service returned an unexpected response.")
    if body.get("error"):
        reason = body.get("reason", "Weather service reported an error.")
        raise ValueError(str(reason))
    return body


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Heavy rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}


def display_weather(latitude, longitude, place_label):
    try:
        with st.spinner("Loading weather and 5-day forecast..."):
            body = get_weather(latitude, longitude)

        current = body.get("current", {})
        daily = body.get("daily", {})

        if not current:
            st.error("Weather data is unavailable.")
            return

        st.subheader(f"📍 Weather for {place_label}")

        st.caption(
            f"Latitude: {latitude:.5f} | "
            f"Longitude: {longitude:.5f} | "
            f"Local time: {current.get('time', 'N/A')}"
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "🌡️ Temperature",
            f"{current.get('temperature_2m', 'N/A')} °C",
        )

        col2.metric(
            "🤗 Feels Like",
            f"{current.get('apparent_temperature', 'N/A')} °C",
        )

        col3.metric(
            "💧 Humidity",
            f"{current.get('relative_humidity_2m', 'N/A')}%",
        )

        col4, col5, col6 = st.columns(3)

        col4.metric(
            "🌤️ Conditions",
            WEATHER_CODES.get(
                current.get("weather_code"),
                "Unknown",
            ),
        )

        col5.metric(
            "💨 Wind Speed",
            f"{current.get('wind_speed_10m', 'N/A')} km/h",
        )

        col6.metric(
            "🌧️ Precipitation",
            f"{current.get('precipitation', 'N/A')} mm",
        )

        forecast = []

        dates = daily.get("time", [])

        for index, forecast_date in enumerate(dates):
            codes = daily.get("weather_code", [])
            minimums = daily.get("temperature_2m_min", [])
            maximums = daily.get("temperature_2m_max", [])
            rain = daily.get(
                "precipitation_probability_max", []
            )

            code = codes[index] if index < len(codes) else None
            low = minimums[index] if index < len(minimums) else None
            high = maximums[index] if index < len(maximums) else None
            chance = rain[index] if index < len(rain) else None

            forecast.append({
                "Date": forecast_date,
                "Conditions": WEATHER_CODES.get(code, "Unknown"),
                "Min °C": low,
                "Max °C": high,
                "Rain Chance %": chance,
            })

        st.subheader("📅 5-Day Forecast")

        if forecast:
            st.dataframe(
                pd.DataFrame(forecast),
                width="stretch",
                hide_index=True,
            )

        st.info(
            "Weather is a model-based estimate for the selected "
            "coordinates. Local conditions can vary across a farm."
        )

    except requests.RequestException as error:
        st.error(f"Could not connect to the weather service: {error}")
    except (ValueError, KeyError, TypeError) as error:
        st.error(f"Could not read weather data: {error}")


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

if page == "🏠 Dashboard":
    show_hero(
        "🌱 Welcome to Krushi Mitra AI",
        "Smart farming assistance, crop insights and agricultural information.",
    )

    st.subheader("What would you like to do today?")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="info-card">
                <h3>💬 AI Farming Assistant</h3>
                <p>Ask agricultural questions and receive AI answers
                in your selected output language.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="info-card">
                <h3>🖼️ Crop Image Analysis</h3>
                <p>Upload or take a crop photo for AI-assisted analysis.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Available Tools")

    col1, col2, col3 = st.columns(3)

    col1.markdown("### 🌦️ Weather")
    col1.write("Location-based weather and a 5-day forecast.")

    col2.markdown("### 📊 Market Prices")
    col2.write("Explore reported wholesale market prices.")

    col3.markdown("### 🎙️ Voice")
    col3.write("Ask by voice and listen to AI responses.")


# ---------------------------------------------------------
# AI CHAT
# ---------------------------------------------------------

elif page == "💬 AI Chat":
    show_hero(
        "💬 AI Farming Assistant",
        f"AI responses will be in {language}.",
    )

    for message_index, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                speak_text(
                    message["content"],
                    voice_language,
                    key=f"chat_voice_{message_index}",
                )

    voice_text = None

    with st.expander("🎙️ Voice input — record your question"):
        st.caption(f"Recording language: {selected_language}. Click the microphone, speak, then stop recording.")
        if hasattr(st, "audio_input"):
            recorded_audio = st.audio_input(
                "Record a farming question",
                sample_rate=16000,
                key=f"audio_input_{voice_language}",
            )
            if recorded_audio is not None:
                st.audio(recorded_audio, format="audio/wav")
                if st.button("📝 Convert recording to text", key=f"transcribe_{voice_language}", type="primary"):
                    with st.spinner("Recognizing speech…"):
                        voice_text = transcribe_recording(recorded_audio, voice_language)
                    if voice_text:
                        st.session_state["pending_voice_text"] = voice_text
                        st.success("Recognized: " + voice_text)
                        st.rerun()
        else:
            st.warning("Your Streamlit version does not support audio_input. Update Streamlit: pip install --upgrade streamlit")
        if not SPEECH_RECOGNITION_AVAILABLE:
            st.caption("Install voice input support in the PyCharm terminal: pip install SpeechRecognition")

    prompt = st.chat_input(
        "Type your farming question here..."
    )

    pending_voice = st.session_state.pop("pending_voice_text", None)
    if pending_voice:
        prompt = pending_voice

    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Preparing your answer..."):
                result = chat_with_ai(
                    st.session_state.messages,
                    language=language,
                )

            answer = result.get(
                "answer",
                "The AI could not provide an answer.",
            )

            if result.get("success"):
                st.markdown(answer)
                st.session_state.last_answer = answer
            else:
                st.error(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
        })


# ---------------------------------------------------------
# CROP IMAGE ANALYSIS
# ---------------------------------------------------------

elif page == "🖼️ Crop Image Analysis":
    show_hero(
        "🖼️ Crop Image Analysis",
        "Upload a crop image or take a photo using your camera.",
    )

    upload_tab, camera_tab = st.tabs([
        "📁 Upload Photo",
        "📷 Take Photo",
    ])

    uploaded_image = None

    with upload_tab:
        file_image = st.file_uploader(
            "Choose a crop or leaf image",
            type=["jpg", "jpeg", "png", "webp"],
            key="crop_upload",
        )

        if file_image is not None:
            uploaded_image = file_image

    with camera_tab:
        camera_image = st.camera_input(
            "Take a crop or leaf photo",
            key="crop_camera",
        )

        if camera_image is not None:
            uploaded_image = camera_image

    question = st.text_area(
        "What would you like to know?",
        placeholder="Example: What symptoms are visible on this leaf?",
    )

    if uploaded_image is not None:
        st.image(
            uploaded_image,
            caption="Selected crop image",
            width="stretch",
        )

        if st.button("🔍 Analyze Image", type="primary"):
            image_bytes = uploaded_image.getvalue()

            if len(image_bytes) > 8 * 1024 * 1024:
                st.error("Image is too large. Choose an image under 8 MB.")

            else:
                with st.spinner("Analyzing image with AI..."):
                    result = analyze_image(
                        image_bytes=image_bytes,
                        mime_type=(
                            uploaded_image.type or "image/jpeg"
                        ),
                        question=question,
                        language=language,
                    )

                answer = result.get(
                    "answer",
                    "Image analysis could not be completed.",
                )

                if result.get("success"):
                    st.subheader("AI Analysis")
                    st.markdown(answer)
                    speak_text(answer, voice_language, key="image_voice")
                else:
                    st.error(answer)

    st.warning(
        "AI image analysis is not a confirmed crop diagnosis. "
        "Consult a local agricultural expert before treating crops."
    )


# ---------------------------------------------------------
# WEATHER
# ---------------------------------------------------------

elif page == "🌦️ Weather":
    show_hero(
        "🌦️ Precision Farm Weather",
        "Choose your farm location using GPS, a place name, or the map.",
    )

    location_mode = st.radio(
        "Choose Location Method",
        [
            "📍 Use Device GPS",
            "🔎 Enter Place Name",
            "🗺️ Select on Map",
        ],
        horizontal=True,
    )

    if location_mode == "📍 Use Device GPS":
        st.write(
            "Allow browser location permission to use your current coordinates."
        )

        if GPS_AVAILABLE:
            gps = streamlit_geolocation()

            if (
                isinstance(gps, dict)
                and gps.get("latitude") is not None
                and gps.get("longitude") is not None
            ):
                latitude = float(gps["latitude"])
                longitude = float(gps["longitude"])

                st.success(
                    f"GPS received: {latitude:.5f}, {longitude:.5f}"
                )

                if st.button(
                    "🌦️ Get Weather at My Location",
                    type="primary",
                ):
                    st.session_state.weather_coords = (
                        latitude,
                        longitude,
                    )
                    st.session_state.weather_place = "Device GPS"

            else:
                st.info(
                    "Allow location access in your browser, "
                    "or use the place-name and map options."
                )

        else:
            st.warning(
                "GPS is unavailable. Install streamlit-geolocation "
                "or use the other location methods."
            )

    elif location_mode == "🔎 Enter Place Name":
        # Keep geocoding results in session state so the selection remains
        # visible after Streamlit reruns the script.
        with st.form("place_search_form"):
            place_name = st.text_input(
                "Town, village, or farm area",
                placeholder="e.g. Chamarajanagar, Mysuru",
            )
            find_place = st.form_submit_button(
                "🔎 Search Location",
                type="primary",
            )

        if find_place:
            if not place_name.strip():
                st.warning("Enter a town, village, or farm area.")
            else:
                try:
                    with st.spinner("Searching for your location..."):
                        found_places = search_place(place_name.strip())
                    st.session_state.weather_search_results = found_places
                    st.session_state.weather_search_label = place_name.strip()
                    if not found_places:
                        st.warning("Location not found. Try a nearby town or a different spelling.")
                except requests.RequestException as error:
                    st.session_state.weather_search_results = []
                    st.error(f"Location search failed: {error}. You can use the map or enter coordinates instead.")
                except (ValueError, TypeError) as error:
                    st.session_state.weather_search_results = []
                    st.error(f"Could not read the location search response: {error}")

        found_places = st.session_state.get("weather_search_results", [])
        if found_places:
            options = [
                f"{item.get('name', 'Unknown')}, {item.get('admin1', '')}, {item.get('country', '')}".strip(", ")
                for item in found_places
            ]
            chosen_index = next(
                (i for i, item in enumerate(found_places)
                 if str(item.get("admin1", "")).casefold() == "karnataka"),
                0,
            )
            selected_place = st.selectbox(
                "Confirm matching location",
                options,
                index=chosen_index,
                key="selected_geocoded_place",
            )
            selected_index = options.index(selected_place)
            selected_data = found_places[selected_index]
            st.caption("Weather will be fetched for the selected place coordinates.")
            if st.button("🌦️ Load Weather for This Place", type="primary", key="load_named_place_weather"):
                st.session_state.weather_coords = (
                    float(selected_data["latitude"]),
                    float(selected_data["longitude"]),
                )
                st.session_state.weather_place = selected_place
                st.rerun()

    elif location_mode == "🗺️ Select on Map":
        st.caption(
            "Click on the map to select your farm location. "
            "You can also enter latitude and longitude manually."
        )

        default_lat = 12.3375
        default_lon = 76.1020
        clicked = None

        if MAP_AVAILABLE:
            farm_map = folium.Map(
                location=[default_lat, default_lon],
                zoom_start=9,
                control_scale=True,
            )

            folium.Marker(
                [default_lat, default_lon],
                tooltip="Map center",
            ).add_to(farm_map)

            map_result = st_folium(
                farm_map,
                height=400,
                key="farm_weather_map",
            )

            if isinstance(map_result, dict):
                clicked = map_result.get("last_clicked")

        else:
            st.warning(
                "Interactive map is unavailable. Install folium "
                "and streamlit-folium."
            )

        map_lat = float(clicked["lat"]) if clicked else default_lat
        map_lon = float(clicked["lng"]) if clicked else default_lon

        col1, col2 = st.columns(2)

        with col1:
            latitude = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=map_lat,
                format="%.5f",
            )

        with col2:
            longitude = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=map_lon,
                format="%.5f",
            )

        if clicked:
            st.success(
                f"Map location: {map_lat:.5f}, {map_lon:.5f}"
            )

        if st.button(
            "🌦️ Get Weather for Selected Coordinates",
            type="primary",
        ):
            st.session_state.weather_coords = (
                float(latitude),
                float(longitude),
            )
            st.session_state.weather_place = "Selected farm coordinates"

    if st.session_state.weather_coords:
        latitude, longitude = st.session_state.weather_coords

        display_weather(
            latitude,
            longitude,
            st.session_state.weather_place or "Selected location",
        )

    st.caption(
        "Weather source: Open-Meteo. GPS needs browser permission "
        "and HTTPS or localhost. Forecasts are estimates, not "
        "guarantees for every part of a farm."
    )


# ---------------------------------------------------------
# MARKET PRICES
# ---------------------------------------------------------

elif page == "📊 Market Prices":
    show_hero(
        "📊 Mandi Price Explorer",
        "Explore available agricultural wholesale price records.",
    )

    MANDI_BASE = "https://mandi-api.onrender.com/v1"

    def mandi_get(endpoint, params=None):
        response = requests.get(
            f"{MANDI_BASE}/{endpoint}",
            params=params or {},
            timeout=35,
        )

        response.raise_for_status()
        body = response.json()

        if body.get("success") is not True:
            raise RuntimeError(
                "The market price service returned an error."
            )

        return body.get("data", [])

    def get_name(item, *keys):
        if isinstance(item, str):
            return item.strip()

        if isinstance(item, dict):
            for key in keys:
                value = item.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()

        return ""

    try:
        with st.spinner("Loading available states..."):
            states_data = mandi_get("states")

        states = sorted({
            get_name(item, "state", "name")
            for item in states_data
            if get_name(item, "state", "name")
        })

        if not states:
            st.warning("No supported states were returned.")
        else:
            state = st.selectbox("Select State", states)

            with st.spinner("Loading markets..."):
                market_data = mandi_get(
                    "markets",
                    {"state": state},
                )

            market_rows = []

            for item in market_data:
                market_name = get_name(
                    item, "market", "market_name", "name"
                )
                district_name = get_name(
                    item, "district", "district_name"
                )

                if market_name:
                    market_rows.append({
                        "market": market_name,
                        "district": district_name,
                    })

            districts = sorted({
                row["district"]
                for row in market_rows
                if row["district"]
            })

            if not districts:
                st.warning(
                    "District names were not returned by the API. "
                    "Try another state or check the API service."
                )
            else:
                district = st.selectbox(
                    "Select District",
                    districts,
                )

                markets = sorted({
                    row["market"]
                    for row in market_rows
                    if row["district"] == district
                })

                if markets:
                    market = st.selectbox(
                        "Select Market / Mandi",
                        markets,
                    )

                    with st.spinner("Loading available crops..."):
                        crops_data = mandi_get(
                            "commodities",
                            {
                                "state": state,
                                "market": market,
                            },
                        )

                    crops = sorted({
                        get_name(item, "commodity", "name")
                        for item in crops_data
                        if get_name(item, "commodity", "name")
                    })

                    if crops:
                        crop = st.selectbox(
                            "Select Crop",
                            crops,
                        )

                        if st.button(
                            "🔎 Search Market Prices",
                            type="primary",
                        ):
                            with st.spinner(
                                "Fetching market price records..."
                            ):
                                records = mandi_get(
                                    "prices",
                                    {
                                        "state": state,
                                        "market": market,
                                        "commodity": crop,
                                    },
                                )

                            df = pd.DataFrame(records)

                            if df.empty:
                                st.warning(
                                    "No price records found for this selection."
                                )
                            else:
                                # Filter exact matches when fields exist.
                                for column, value in [
                                    ("market", market),
                                    ("district", district),
                                    ("commodity", crop),
                                ]:
                                    if column in df.columns:
                                        df = df[
                                            df[column]
                                            .astype(str)
                                            .str.strip()
                                            .str.casefold()
                                            == value.strip().casefold()
                                        ]

                                if df.empty:
                                    st.warning(
                                        "No matching records found."
                                    )
                                else:
                                    if "arrival_date" in df.columns:
                                        df = df.sort_values(
                                            "arrival_date",
                                            ascending=False,
                                            na_position="last",
                                        )

                                    st.subheader(f"🌾 {crop}")
                                    st.caption(
                                        f"{market}, {district}, {state}"
                                    )

                                    latest = df.iloc[0]

                                    def price(value):
                                        try:
                                            if pd.isna(value):
                                                return "N/A"
                                            return f"₹{float(value):,.0f}"
                                        except (ValueError, TypeError):
                                            return "N/A"

                                    col1, col2, col3 = st.columns(3)

                                    col1.metric(
                                        "Minimum Price",
                                        price(latest.get("min_price")),
                                    )
                                    col2.metric(
                                        "Maximum Price",
                                        price(latest.get("max_price")),
                                    )
                                    col3.metric(
                                        "Modal Price",
                                        price(latest.get("modal_price")),
                                    )

                                    st.subheader("Detailed Price Records")
                                    st.dataframe(
                                        df,
                                        width="stretch",
                                        hide_index=True,
                                    )

                                    st.download_button(
                                        "⬇️ Download CSV Report",
                                        data=df.to_csv(
                                            index=False
                                        ).encode("utf-8"),
                                        file_name="krushi_mitra_prices.csv",
                                        mime="text/csv",
                                    )

                                    st.caption(
                                        "Always check the arrival date. "
                                        "These records are not guaranteed "
                                        "to be live selling offers."
                                    )
                    else:
                        st.warning(
                            "No crops were returned for this market."
                        )
                else:
                    st.warning(
                        "No markets were found for this district."
                    )

    except requests.RequestException as error:
        st.error(f"Could not connect to the Mandi API: {error}")
    except (ValueError, RuntimeError, KeyError) as error:
        st.error(f"Could not load market data: {error}")


# ---------------------------------------------------------
# ABOUT
# ---------------------------------------------------------

elif page == "ℹ️ About":
    show_hero(
        "ℹ️ About Krushi Mitra AI",
        "A lightweight agricultural assistance application.",
    )

    st.markdown(
        """
        ### Features

        - AI agricultural chat
        - Typed and voice questions
        - AI crop image analysis
        - Photo upload and camera capture
        - GPS, place-name and map-based weather
        - Five-day weather forecast
        - Mandi market price records
        - Multilingual AI text and voice output

        ### Important

        AI answers and crop image analysis may be incorrect.
        Consult a qualified local agricultural expert before
        making important crop treatment decisions.

        ### Privacy

        Chat messages and uploaded images may be sent to your
        configured AI provider when you request AI assistance.
        Do not upload sensitive personal information.
        
        ### Developed_By : 
                Team Coding_Ninjas...
        """
    )
