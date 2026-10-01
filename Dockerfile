FROM python:3.12-slim AS simulation

ARG UID=1000
ARG GID=1000

# libgomp1 et libglib2.0-0 sont exiges par le binaire OpenTTD >= 15 (verifie sur 15.3 : sans eux
# le binaire sort en 127, "libgomp.so.1: cannot open shared object file"). Le binaire 13.4 n'en
# avait pas besoin ; les ajouter est purement additif et ne change rien aux campagnes 13.4.
RUN apt-get update && apt-get install -y --no-install-recommends \
      unzip tar ca-certificates libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GID} lab && useradd -m -u ${UID} -g ${GID} lab
# Keep image dependencies outside the persistent /home/lab cache mount.
RUN python -m venv /opt/venv && chown -R ${UID}:${GID} /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONNOUSERSITE=1
USER lab
WORKDIR /home/lab

COPY --chown=lab:lab requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

# Dependances de modelisation, dans une couche separee : requirements.txt (simulation) reste
# inchange, donc sa couche de cache survit a l'ajout/mise a jour des dependances ML.
FROM simulation AS ml
COPY --chown=lab:lab requirements-ml.txt .
RUN python -m pip install --no-cache-dir -r requirements-ml.txt
