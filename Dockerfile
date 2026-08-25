FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      unzip tar ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 lab
USER lab
WORKDIR /home/lab

COPY --chown=lab:lab requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
ENV PATH=/home/lab/.local/bin:$PATH
