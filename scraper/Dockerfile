# Scraper-only image for the scheduled catalog refresh.
#
# Lives outside the repository root on purpose: a root Dockerfile would make
# Railway build the WEB service with it and break the deploy. The web service
# keeps using nixpacks with the Procfile.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first so the browser layer is cached across code changes.
COPY requirements.txt requirements-scraper.txt ./
RUN pip install --no-cache-dir -r requirements-scraper.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# The cron service overrides this with the schedule; the command must finish.
CMD ["python", "-m", "jobs.refresh_catalog"]
