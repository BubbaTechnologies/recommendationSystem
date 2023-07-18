FROM python:3.11

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src /app

EXPOSE 403

ARG DB_USERNAME
ENV DB_USERNAME ${DB_USERNAME}

ARG DB_PASSWORD
ENV DB_PASSWORD ${DB_PASSWORD}

ARG DB_ADDR_READER
ENV DB_ADDR_READER ${DB_ADDR_READER}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "403"]