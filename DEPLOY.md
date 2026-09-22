# OGSA Vendedores — Deploy

Aplicación de producción: `app_vendedores.py`.

Variables obligatorias del hosting:
- `OGSA_DEMO=0`
- `OGSA_SELLER_USERS_JSON=<JSON secreto de usuarios autorizados>`

No subir `.streamlit/secrets.toml` ni `OGSA_SELLER_USERS_JSON.txt` al repositorio.

Comando de inicio equivalente:
`streamlit run app_vendedores.py --server.address=0.0.0.0 --server.port=$PORT --server.headless=true`