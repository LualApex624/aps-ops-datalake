# Image Superset + pilote Postgres (l'image officielle n'embarque aucun pilote)
FROM apache/superset:4.1.1
USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.10
USER superset
