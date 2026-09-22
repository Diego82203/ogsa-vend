from __future__ import annotations

import lzma
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dashboard.db"
PARTS_DIR = BASE_DIR / "data_parts"


def ensure_database() -> Path:
    """Materialize the encrypted pilot SQLite database at runtime.

    The repository only contains Fernet-encrypted, XZ-compressed chunks. The
    decryption key is supplied by Railway as OGSA_DB_KEY and is never committed.
    """
    if DB_PATH.exists() and DB_PATH.stat().st_size > 1024 * 1024:
        return DB_PATH

    key = os.environ.get("OGSA_DB_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta la variable segura OGSA_DB_KEY.")

    parts = sorted(PARTS_DIR.glob("dashboard.db.xz.enc.part*"))
    if not parts:
        raise RuntimeError("No se encontraron los bloques cifrados de datos.")

    token = b"".join(p.read_bytes() for p in parts)
    try:
        compressed = Fernet(key.encode("ascii")).decrypt(token)
    except (InvalidToken, ValueError) as exc:
        raise RuntimeError("No se pudo descifrar la base de datos.") from exc

    tmp = DB_PATH.with_suffix(".db.tmp")
    tmp.write_bytes(lzma.decompress(compressed))
    os.replace(tmp, DB_PATH)
    return DB_PATH