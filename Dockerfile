# Stage 1: 构建阶段
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.org/simple/ -r requirements.txt

# Stage 2: 运行阶段
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY app.py .
COPY modules/ modules/
COPY history.csv market_state.json memory.json threshold_config.json ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
