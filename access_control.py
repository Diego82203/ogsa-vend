from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

import streamlit as st

DEFAULT_ITERATIONS = 260_000


def _cfg_to_dict(obj: Any) -> dict:
    try:
        return dict(obj)
    except Exception:
        return {}


def _pbkdf2(password: str, salt_hex: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()


def _verify(password: str, user_cfg: dict) -> bool:
    salt = str(user_cfg.get("salt", ""))
    expected = str(user_cfg.get("password_hash", ""))
    if not salt or not expected:
        return False
    iterations = int(user_cfg.get("iterations", DEFAULT_ITERATIONS))
    try:
        candidate = _pbkdf2(password, salt, iterations)
    except Exception:
        return False
    return hmac.compare_digest(candidate, expected)


def _load_users(mode: str) -> dict:
    # Preferred for deployment: store hashed user config in an environment secret.
    env_name = "OGSA_SELLER_USERS_JSON" if mode == "Vendedor" else "OGSA_MANAGER_USERS_JSON"
    raw = os.environ.get(env_name, "").strip()
    if raw:
        try:
            data = json.loads(raw)
            return {str(k).strip().lower(): dict(v) for k, v in data.items()}
        except Exception:
            pass

    section = "seller_users" if mode == "Vendedor" else "manager_users"
    try:
        data = _cfg_to_dict(st.secrets[section])
        return {str(k).strip().lower(): _cfg_to_dict(v) for k, v in data.items()}
    except Exception:
        return {}


def authenticate_access(mode: str) -> dict:
    """Closed access by email + password.

    Seller app maps each approved email to exactly one seller_code.
    OGSA_DEMO=1 bypasses auth only for local development.
    """
    if os.environ.get("OGSA_DEMO", "0") == "1":
        return {"username": "demo", "display_name": "Demo local", "seller_code": ""}

    users = _load_users(mode)
    role = "seller" if mode == "Vendedor" else "manager"
    state_key = f"ogsa_auth_{role}"

    if st.session_state.get(state_key):
        return dict(st.session_state[state_key])

    st.markdown("## Acceso OGSA")
    st.caption("Portal de vendedores" if mode == "Vendedor" else "Portal gerencial")
    if mode == "Vendedor":
        st.markdown(
            '<div style="margin:.15rem 0 1rem;"><a href="?portal=gerencial" target="_self" '
            'style="font-size:.86rem;font-weight:700;text-decoration:none;">Ingresar al dashboard gerencial →</a></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="margin:.15rem 0 1rem;"><a href="?portal=vendedores" target="_self" '
            'style="font-size:.86rem;font-weight:700;text-decoration:none;">← Volver al portal de vendedores</a></div>',
            unsafe_allow_html=True,
        )

    if not users:
        st.error("No hay usuarios configurados para este portal.")
        st.stop()

    with st.form(f"login_{role}", clear_on_submit=False):
        email = st.text_input("Correo").strip().lower()
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Ingresar", use_container_width=True)

    if submit:
        cfg = _cfg_to_dict(users.get(email, {}))
        if cfg and _verify(password, cfg):
            if mode == "Vendedor" and not str(cfg.get("seller_code", "")).strip():
                st.error("Este correo no tiene vendedor asignado.")
            else:
                session = {
                    "username": email,
                    "email": email,
                    "display_name": str(cfg.get("display_name", email)),
                    "seller_code": str(cfg.get("seller_code", "")).strip(),
                    "role": role,
                }
                st.session_state[state_key] = session
                st.rerun()
        else:
            st.error("Correo o contraseña incorrectos.")

    st.stop()


def render_logout() -> None:
    if st.button("Cerrar sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("ogsa_auth_"):
                del st.session_state[key]
        st.rerun()