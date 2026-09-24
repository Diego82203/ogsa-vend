from __future__ import annotations

import base64
import json
import lzma
import os
import sqlite3
import zlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dashboard.db"
PARTS_DIR = BASE_DIR / "data_parts"


def _apply_runtime_patch(db_path: Path) -> None:
    """Apply a private data patch supplied only through Railway environment variables."""
    raw_patch = os.environ.get("OGSA_RUNTIME_PATCH_B64", "").strip()
    if not raw_patch:
        parts = []
        for i in range(10):
            part = os.environ.get(f"OGSA_RUNTIME_PATCH_{i}", "")
            if not part:
                break
            parts.append(part)
        raw_patch = "".join(parts).strip()
    if not raw_patch:
        return

    try:
        payload = json.loads(zlib.decompress(base64.b64decode(raw_patch)).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("No se pudo leer el parche privado de datos.") from exc

    patch_id = str(payload.get("patch_id", "")).strip()
    columns = list(payload.get("columns", []))
    updates = list(payload.get("updates", []))
    if not patch_id or not columns or not updates:
        raise RuntimeError("El parche privado de datos está incompleto.")

    quoted_cols = ", ".join(f'"{c}"' for c in columns)
    placeholders = ",".join(["?"] * len(columns))

    with sqlite3.connect(db_path) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS runtime_patches ("
            "patch_id TEXT PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        if con.execute("SELECT 1 FROM runtime_patches WHERE patch_id=?", (patch_id,)).fetchone():
            return

        # Keep DIGAR document/customer identities isolated from OGSA historically.
        con.execute(
            "UPDATE sales SET invoice_no='DIGAR|' || invoice_no "
            "WHERE company='DIGAR' AND invoice_no IS NOT NULL AND invoice_no<>'' "
            "AND invoice_no NOT LIKE 'DIGAR|%'"
        )
        con.execute(
            "UPDATE sales SET customer_code='DIGAR|' || customer_code "
            "WHERE company='DIGAR' AND customer_code IS NOT NULL AND customer_code<>'' "
            "AND customer_code NOT LIKE 'DIGAR|%'"
        )

        for update in updates:
            company = str(update["company"]).upper()
            min_date = str(update["min_date"])
            max_date = str(update["max_date"])
            rows = list(update["rows"])
            if company not in {"OGSA", "DIGAR"}:
                raise RuntimeError("Empresa inválida en parche de datos.")
            con.execute(
                "DELETE FROM sales WHERE company=? AND invoice_date BETWEEN ? AND ?",
                (company, min_date, max_date),
            )
            con.executemany(
                f"INSERT INTO sales ({quoted_cols}) VALUES ({placeholders})",
                rows,
            )

        con.execute("INSERT INTO runtime_patches(patch_id) VALUES (?)", (patch_id,))
        con.commit()


def ensure_database() -> Path:
    """Materialize the encrypted SQLite base and apply a private incremental patch."""
    if not (DB_PATH.exists() and DB_PATH.stat().st_size > 1024 * 1024):
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

    _apply_runtime_patch(DB_PATH)
    return DB_PATH
