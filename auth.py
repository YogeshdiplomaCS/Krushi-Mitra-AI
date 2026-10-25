
"""MySQL authentication helpers for Krushi Mitra AI."""
import hashlib
import hmac
import os
import re
import secrets
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    import mysql.connector as mysql_connector
except ImportError:
    mysql_connector = None

_VERIFICATION_DIR = Path(__file__).resolve().parent / "krushi_verification_component"

_verification_component = components.declare_component(
    "krushi_mitra_verification",
    path=str(_VERIFICATION_DIR),
)


def config_value(key, default=""):
    try:
        value = st.secrets.get(key, None)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(key, default)


def _firebase_config():
    return {
        "apiKey": config_value("FIREBASE_API_KEY"),
        "authDomain": config_value("FIREBASE_AUTH_DOMAIN"),
        "projectId": config_value("FIREBASE_PROJECT_ID"),
        "appId": config_value("FIREBASE_APP_ID"),
        "messagingSenderId": config_value("FIREBASE_MESSAGING_SENDER_ID"),
    }


def _firebase_ready():
    return all(_firebase_config().values())


def _verify_firebase_phone_token(id_token, expected_phone):
    api_key = config_value("FIREBASE_API_KEY")
    if not api_key or not id_token:
        return False

    try:
        response = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={api_key}",
            json={"idToken": id_token},
            timeout=12,
        )
        response.raise_for_status()
        users = response.json().get("users", [])

        if not users:
            return False

        actual = users[0].get("phoneNumber", "")
        return hmac.compare_digest(actual, expected_phone)

    except (requests.RequestException, ValueError, TypeError):
        return False


def _verify_google_recaptcha(token):
    secret = config_value("RECAPTCHA_SECRET_KEY")

    if not secret or not token:
        return False, "reCAPTCHA is not configured or has not been completed."

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": secret, "response": token},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            return True, "Verified"

        return False, "reCAPTCHA verification failed. Please complete it again."

    except (requests.RequestException, ValueError):
        return False, (
            "Could not verify reCAPTCHA. Check your internet connection and try again."
        )


def db_connection():
    if mysql_connector is None:
        raise RuntimeError(
            "MySQL driver missing. Run: "
            "python -m pip install mysql-connector-python"
        )

    return mysql_connector.connect(
        host=config_value("DB_HOST", "127.0.0.1"),
        port=int(config_value("DB_PORT", "3306")),
        user=config_value("DB_USER", "root"),
        password=config_value("DB_PASSWORD", ""),
        database=config_value("DB_NAME", "krushi_mitra_ai"),
        connection_timeout=5,
    )


def init_auth_db():
    connection = db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(254) NOT NULL UNIQUE,
                mobile VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                phone_verified TINYINT(1) NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        connection.commit()

    finally:
        cursor.close()
        connection.close()


def normalize_email(email):
    return (email or "").strip().lower()


def find_user_by_email(email):
    """Return non-sensitive account status only."""
    connection = db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, email FROM users WHERE email = %s LIMIT 1",
            (normalize_email(email),),
        )
        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        310_000,
    )
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        calculated = hash_password(
            password,
            bytes.fromhex(salt_hex),
        ).split("$", 1)[1]

        return hmac.compare_digest(calculated, digest_hex)

    except (ValueError, TypeError):
        return False


def create_user(full_name, email, mobile, password):
    connection = db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users
                (full_name, email, mobile, password_hash, phone_verified)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (
                full_name.strip(),
                normalize_email(email),
                mobile.strip(),
                hash_password(password),
            ),
        )
        connection.commit()
        return True, "Account created. You can now log in."

    except Exception as exc:
        if getattr(exc, "errno", None) == 1062:
            return False, (
                "This email is already registered. Please log in instead."
            )
        raise

    finally:
        cursor.close()
        connection.close()


def authenticate(email, password):
    connection = db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, full_name, email, mobile,
                   password_hash, phone_verified
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (normalize_email(email),),
        )

        user = cursor.fetchone()

        if user and verify_password(password, user["password_hash"]):
            user.pop("password_hash", None)
            return user

        return None

    finally:
        cursor.close()
        connection.close()


def _switch_to_login():
    st.session_state["auth_mode"] = "Login"
    st.session_state["login_email"] = st.session_state.get(
        "register_email", ""
    )


def render_auth_gate():
    """Render authentication screen with server-verified CAPTCHA and phone OTP."""

    if st.session_state.get("auth_user"):
        return True

    st.markdown("""
    <style>
      .auth-wrap {
          max-width: 1080px;
          margin: 1vh auto 0;
      }
      .auth-hero {
          background: linear-gradient(
              125deg, #103d25, #168344 62%, #55c878
          );
          color: #fff;
          padding: clamp(24px, 4vw, 38px);
          border-radius: 24px;
          margin-bottom: 22px;
          box-shadow: 0 15px 35px #14532d20;
      }
      .auth-hero h1 {
          color: #fff;
          margin: 0 0 8px;
          font-size: clamp(1.8rem, 4vw, 2.6rem);
          letter-spacing: -.03em;
      }
      .auth-hero p {
          color: #edfff1;
          margin: 0;
          line-height: 1.7;
      }
      .auth-card {
          background: linear-gradient(180deg, #ffffff, #f7fff8);
          border: 1px solid #d8ead9;
          border-radius: 22px;
          padding: clamp(16px, 3vw, 26px);
          box-shadow: 0 10px 32px #164e2b0d;
      }
      .auth-small {
          font-size: .78rem;
          color: #607665;
      }
      div[data-testid="stTextInput"] input {
          border-radius: 11px;
          min-height: 44px;
      }
      div.stButton > button,
      div[data-testid="stFormSubmitButton"] button {
          border-radius: 11px;
          font-weight: 650;
          min-height: 2.7rem;
      }
      div[role="radiogroup"] {
          gap: 10px;
      }
    </style>

    <div class="auth-wrap">
      <div class="auth-hero">
        <h1>🌱 Krushi Mitra AI</h1>
        <p>
          Your smart farming companion — crop guidance, weather insights
          and market information in one place.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([0.92, 1.08], gap="large")

    with left:
        st.markdown(
            '<div class="auth-card">',
            unsafe_allow_html=True,
        )
        st.markdown("### 🌾 Grow smarter, every day")
        st.write(
            "Sign in to continue to your personal farming assistant."
        )
        st.markdown(
            "- 🌱 AI crop and farming guidance\n"
            "- 🌦️ Weather and location insights\n"
            "- 📊 Agricultural market prices\n"
            "- 🖼️ Crop image analysis"
        )
        st.success("Your farming tools in one place.")
        st.markdown(
            '<p class="auth-small">🔒 Passwords are stored using '
            'salted PBKDF2 hashing. Phone OTP and CAPTCHA are checked '
            'by their providers.</p></div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            '<div class="auth-card">',
            unsafe_allow_html=True,
        )

        # Fixed: use a non-empty label for accessibility.
        mode = st.radio(
            "Choose authentication mode",
            ["Login", "Create account"],
            horizontal=True,
            key="auth_mode",
            label_visibility="collapsed",
        )

        if mode == "Login":
            st.subheader("Welcome back 👋")

            email = st.text_input(
                "Email address",
                placeholder="you@example.com",
                key="login_email",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
            )

            site_key = config_value("RECAPTCHA_SITE_KEY")
            captcha_result = None

            if site_key:
                captcha_result = _verification_component(
                    mode="captcha",
                    siteKey=site_key,
                    nonce=st.session_state.get("captcha_nonce", "login"),
                    key="login_captcha_component",
                    default=None,
                )
            else:
                st.warning(
                    "Login CAPTCHA needs RECAPTCHA_SITE_KEY and "
                    "RECAPTCHA_SECRET_KEY in your local secrets file."
                )

            if st.button(
                "🔐 Login securely",
                type="primary",
                use_container_width=True,
                key="login_submit",
            ):
                normalized_email = normalize_email(email)

                if not normalized_email or not password:
                    st.warning(
                        "Enter both your email address and password."
                    )

                elif not re.fullmatch(
                    r"[^@\s]+@[^@\s]+\.[^@\s]+",
                    normalized_email,
                ):
                    st.warning("Enter a valid email address.")

                elif (
                    not site_key
                    or not config_value("RECAPTCHA_SECRET_KEY")
                ):
                    st.error(
                        "Configure the Google reCAPTCHA site key and "
                        "secret key before enabling login."
                    )

                elif (
                    not isinstance(captcha_result, dict)
                    or captcha_result.get("type") != "captcha"
                    or not captcha_result.get("token")
                ):
                    st.error(
                        "Complete the reCAPTCHA checkbox before logging in."
                    )

                else:
                    captcha_ok, captcha_message = (
                        _verify_google_recaptcha(
                            captcha_result.get("token", "")
                        )
                    )

                    if not captcha_ok:
                        st.error(captcha_message)

                    else:
                        try:
                            init_auth_db()
                            user = authenticate(
                                normalized_email,
                                password,
                            )

                            if user:
                                st.session_state.auth_user = user
                                st.session_state.messages = []
                                st.session_state.pop(
                                    "login_password",
                                    None,
                                )
                                st.success(
                                    f"Welcome back, {user['full_name']}!"
                                )
                                st.rerun()

                            else:
                                st.error(
                                    "Email or password is incorrect. "
                                    "Please try again."
                                )

                        except Exception as exc:
                            st.error(
                                "Could not connect to MySQL. Start MySQL "
                                "in XAMPP and check your database settings."
                            )
                            st.caption(str(exc))

            st.caption(
                "Use the same email and password you registered with."
            )

        else:
            st.subheader("Create your account 🌱")

            full_name = st.text_input(
                "Full name",
                placeholder="Your name",
                key="register_full_name",
            )
            email = st.text_input(
                "Email address",
                placeholder="you@example.com",
                key="register_email",
            )
            mobile = st.text_input(
                "Mobile number with country code",
                placeholder="+91XXXXXXXXXX",
                key="register_mobile",
            )
            password = st.text_input(
                "Create password",
                type="password",
                placeholder="At least 8 characters",
                key="register_password",
            )
            confirm = st.text_input(
                "Confirm password",
                type="password",
                key="register_confirm",
            )

            if not _firebase_ready():
                st.warning(
                    "Phone OTP needs your Firebase Web App settings. "
                    "Add them to .streamlit/secrets.toml; the registration "
                    "button stays disabled until configured."
                )
                phone_result = None

            else:
                phone_result = _verification_component(
                    mode="phone",
                    phone=mobile.strip(),
                    firebaseConfig=_firebase_config(),
                    nonce=st.session_state.get(
                        "phone_otp_nonce",
                        "register",
                    ),
                    key="register_phone_otp_component",
                    default=None,
                )

            verified_phone = ""

            if (
                isinstance(phone_result, dict)
                and phone_result.get("type") == "phone_verified"
            ):
                result_phone = str(
                    phone_result.get("phoneNumber", "")
                )

                if (
                    _verify_firebase_phone_token(
                        str(phone_result.get("idToken", "")),
                        result_phone,
                    )
                    and result_phone == mobile.strip()
                ):
                    verified_phone = result_phone
                    st.success(
                        "✅ Mobile number verified. "
                        "You can create your account."
                    )

                else:
                    st.error(
                        "Phone verification could not be validated "
                        "by Firebase. Please verify the number again."
                    )

            if st.button(
                "🌱 Create verified account",
                type="primary",
                use_container_width=True,
                key="register_submit",
            ):
                normalized_email = normalize_email(email)

                if not all([
                    full_name.strip(),
                    normalized_email,
                    mobile.strip(),
                    password,
                    confirm,
                ]):
                    st.warning("Please fill in all fields.")

                elif not re.fullmatch(
                    r"[^@\s]+@[^@\s]+\.[^@\s]+",
                    normalized_email,
                ):
                    st.warning("Enter a valid email address.")

                elif len(password) < 8:
                    st.warning(
                        "Use a password with at least 8 characters."
                    )

                elif password != confirm:
                    st.warning("Passwords do not match.")

                elif not re.fullmatch(
                    r"\+[1-9]\d{7,14}",
                    mobile.strip(),
                ):
                    st.warning(
                        "Enter the mobile number in international format, "
                        "e.g. +91XXXXXXXXXX."
                    )

                elif not verified_phone:
                    st.error(
                        "Verify your mobile number with the SMS OTP "
                        "before creating an account."
                    )

                else:
                    try:
                        init_auth_db()
                        existing = find_user_by_email(normalized_email)

                        if existing:
                            st.info(
                                "This email is already registered. "
                                "Switch to Login and sign in."
                            )

                        else:
                            success, message = create_user(
                                full_name,
                                normalized_email,
                                verified_phone,
                                password,
                            )

                            if success:
                                st.success(
                                    "Account created successfully! "
                                    "Switch to Login to continue."
                                )
                                st.session_state["auth_mode"] = "Login"
                                st.session_state["login_email"] = (
                                    normalized_email
                                )
                                st.rerun()

                            else:
                                st.warning(message)

                    except Exception as exc:
                        st.error(
                            "Could not save the account. Check XAMPP "
                            "MySQL and database settings."
                        )
                        st.caption(str(exc))

        st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Security: phone OTP is verified by Firebase; "
        "login CAPTCHA is verified on the server by Google."
    )

    return False
