FROM python:3.12 as builder

WORKDIR /app

COPY requirements.lock /app
RUN pip3 install -r requirements.lock


FROM python:3.12-slim as service
ENV PYTHON_VERSION 3.12

RUN apt-get update  \
    && apt-get install -y pngquant \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages

WORKDIR /service

COPY app /service/app
COPY run.py /service