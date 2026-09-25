FROM postgres:18

# Python und benötigte Pakete installieren
RUN apt-get update \
    && apt-get install -y python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# API
COPY api/ ./api/

# SQL-Skripte
COPY sql/ /docker-entrypoint-initdb.d/

# Startskript
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5432
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]