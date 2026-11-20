FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home gateway
COPY TEC-EPR-1.0.1-Regional-Customer-Guide.pdf TEC-EPR-1.0.1-Customer-Guide.pdf customer_help.py billing.py migrate_billing.py commercial_catalog.json customer_intake.py app.py init_db.py init_production.py entitlements.py mfa.py migrate_access.py appoint_admins.py onboarding.py onboarding_ui.py migrate_onboarding.py downloads.py download_policy.py release_101_config.py check_private_storage.py ui.py verify_downloaded_release.py ./
USER gateway
CMD ["sh", "-c", "uvicorn app:from_environment --factory --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]

RUN python -c "from pathlib import Path; names=['TEC-EPR-1.0.1-Customer-Guide.pdf','TEC-EPR-1.0.1-Regional-Customer-Guide.pdf']; assert all(Path(n).read_bytes().startswith(b'%PDF-') for n in names)"
