FROM python:3.11

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src /app

EXPOSE 80

ARG SERVER_USERNAME
ENV SERVER_USERNAME ${SERVER_USERNAME}

ARG SERVER_PASSWORD
ENV SERVER_PASSWORD ${SERVER_PASSWORD}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]