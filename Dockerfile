FROM python:3.11

WORKDIR /app

COPY src/ .
COPY src/models ./models/
COPY src/fastModels ./fastModels
COPY src/modin/ ./modin

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

ARG DB_USERNAME
ENV DB_USERNAME ${DB_USERNAME}

ARG DB_PASSWORD
ENV DB_PASSWORD ${DB_PASSWORD}

ARG DB_ADDR_READER
ENV DB_ADDR_READER ${DB_ADDR_READER}

ARG DB_PORT
ENV DB_PORT ${DB_PORT}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]