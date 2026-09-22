FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV OGSA_DEMO=0
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["sh", "-c", "streamlit run app_vendedores.py --server.address=0.0.0.0 --server.port=${PORT:-8080} --server.headless=true"]