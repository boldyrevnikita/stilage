FROM python:3.10-alpine

RUN apk update && \
    apk add --no-cache build-base geos-dev && \
    python3 -m pip install --upgrade pip


WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD python3.10 -u app.py
