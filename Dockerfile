FROM python:3.12-slim

ARG UID=1000
ARG GID=1000

# libgomp1 et libglib2.0-0 sont exiges par le binaire OpenTTD >= 15 (verifie sur 15.3 : sans eux
# le binaire sort en 127, "libgomp.so.1: cannot open shared object file"). Le binaire 13.4 n'en
# avait pas besoin ; les ajouter est purement additif et ne change rien aux campagnes 13.4.
RUN apt-get update && apt-get install -y --no-install-recommends \
      unzip tar ca-certificates libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${GID} lab && useradd -m -u ${UID} -g ${GID} lab
USER lab
WORKDIR /home/lab

COPY --chown=lab:lab requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Dependances de modelisation, dans une couche separee : requirements.txt (simulation) reste
# inchange, donc sa couche de cache survit a l'ajout/mise a jour des dependances ML.
COPY --chown=lab:lab requirements-ml.txt .
RUN pip install --user --no-cache-dir -r requirements-ml.txt

ENV PATH=/home/lab/.local/bin:$PATH
