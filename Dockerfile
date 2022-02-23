FROM python:3.8 as builder

WORKDIR /app

COPY requirements.txt /app
RUN pip3 install -r requirements.txt


FROM python:3.8-slim as service
ENV PYTHON_VERSION 3.8

RUN apt update  \
    && apt install -y pngquant \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages

COPY app /service/app
COPY run.py /service

ENTRYPOINT ["python", "/service/run.py"]
