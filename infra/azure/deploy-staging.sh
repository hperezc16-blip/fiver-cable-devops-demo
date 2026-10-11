#!/usr/bin/env bash
# ============================================================================
# Fiver Cable - Despliegue de Staging en Azure
#   Azure Container Registry  -> imágenes de los 4 microservicios
#   Azure Database for PostgreSQL (Flexible Server) -> fivercable_db (4 esquemas)
#   Azure Container Apps      -> ms_auth, ms_catalogo, ms_pedidos, ms_pagos
# Idempotente: se puede ejecutar en cada despliegue. Lo ejecuta el pipeline
# (AzureCLI@2) o manualmente con "az login" previo.
# Las claves de PostgreSQL y el secreto JWT se generan en cada despliegue y
# solo viven como secretos del pipeline y de Container Apps.
# ============================================================================
set -euo pipefail

PG_ADMIN_PASSWORD="Fc$(openssl rand -hex 12)A9"
JWT_SECRET_STAGING="$(openssl rand -hex 32)"
echo "##vso[task.setsecret]$PG_ADMIN_PASSWORD"
echo "##vso[task.setsecret]$JWT_SECRET_STAGING"

LOCATION="${AZ_LOCATION:-}"
RG="${AZ_RESOURCE_GROUP:-rg-fivercable-staging}"
SUFIJO="${AZ_SUFIJO:-umg2026}"
ACR="acrfivercable${SUFIJO}"
PG_SERVER="pg-fivercable-${SUFIJO}"
PG_ADMIN="fiveradmin"
DB_NAME="fivercable_db"
ACA_ENV="cae-fivercable-staging"
IMAGE_TAG="${IMAGE_TAG:-latest}"
MAX_REPLICAS="${ACA_MAX_REPLICAS:-2}"
POOL_MIN_SIZE="${DB_POOL_MIN_SIZE:-1}"
POOL_MAX_SIZE="${DB_POOL_MAX_SIZE:-5}"
POOL_TIMEOUT="${DB_POOL_TIMEOUT_SECONDS:-10}"

if ! [[ "$MAX_REPLICAS" =~ ^[1-9][0-9]*$ ]]; then
  echo "ACA_MAX_REPLICAS debe ser un entero positivo" >&2
  exit 1
fi

echo "==> Registro de proveedores de recursos"
for ns in Microsoft.App Microsoft.OperationalInsights Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL; do
  az provider register -n "$ns" --wait -o none
done

# Las suscripciones Azure for Students limitan las regiones permitidas por política.
if [ -z "$LOCATION" ]; then
  PERMITIDAS=$(az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o tsv 2>/dev/null | tr '\t' '\n' | sort -u)
  for cand in eastus2 centralus southcentralus westus2 eastus westus3 canadacentral brazilsouth mexicocentral; do
    if [ -z "$PERMITIDAS" ] || echo "$PERMITIDAS" | grep -qx "$cand"; then LOCATION="$cand"; break; fi
  done
  [ -z "$LOCATION" ] && LOCATION=$(echo "$PERMITIDAS" | head -1)
fi
echo "Región seleccionada: $LOCATION"

echo "==> Grupo de recursos $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" -o none

echo "==> Azure Container Registry $ACR"
az acr show -n "$ACR" -g "$RG" -o none 2>/dev/null || \
  az acr create -n "$ACR" -g "$RG" --sku Basic --admin-enabled true -o none
ACR_SERVER=$(az acr show -n "$ACR" --query loginServer -o tsv)
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query "passwords[0].value" -o tsv)

echo "==> PostgreSQL Flexible Server $PG_SERVER"
if ! az postgres flexible-server show -n "$PG_SERVER" -g "$RG" -o none 2>/dev/null; then
  az postgres flexible-server create -n "$PG_SERVER" -g "$RG" -l "$LOCATION" \
    --admin-user "$PG_ADMIN" --admin-password "$PG_ADMIN_PASSWORD" \
    --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 \
    --public-access 0.0.0.0 --yes -o none
else
  az postgres flexible-server update -g "$RG" -n "$PG_SERVER" --admin-password "$PG_ADMIN_PASSWORD" -o none
fi
# La base se crea aparte para que el script sea idempotente si falló a mitad
# (Azure CLI reciente usa --name para la base de datos)
if ! az postgres flexible-server db show -g "$RG" -s "$PG_SERVER" --name "$DB_NAME" -o none 2>/dev/null; then
  az postgres flexible-server db create -g "$RG" -s "$PG_SERVER" --name "$DB_NAME" -o none
fi
PG_HOST=$(az postgres flexible-server show -n "$PG_SERVER" -g "$RG" --query fullyQualifiedDomainName -o tsv)

# Permitir al agente del pipeline ejecutar el script SQL y los smoke tests
AGENT_IP=$(curl -s https://api.ipify.org)
az postgres flexible-server firewall-rule create -g "$RG" -s "$PG_SERVER" \
  --name agente-pipeline --start-ip-address "$AGENT_IP" --end-ip-address "$AGENT_IP" -o none

DATABASE_URL="postgresql://${PG_ADMIN}:${PG_ADMIN_PASSWORD}@${PG_HOST}:5432/${DB_NAME}?sslmode=require"

echo "==> Script de base de datos (Entregable 8)"
if ! psql "$DATABASE_URL" -tAc "SELECT to_regclass('usuarios_db.clientes')" | grep -q clientes; then
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/init/01_schema.sql -f db/init/02_seed.sql
else
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/init/01_schema.sql   # objetos idempotentes
fi

echo "==> Construir y publicar imágenes en ACR (tag $IMAGE_TAG)"
az acr login -n "$ACR"
for svc in auth catalogo pedidos pagos; do
  docker build -t "$ACR_SERVER/fivercable/ms_${svc}:${IMAGE_TAG}" -f "docker/Dockerfile.${svc}" .
  docker push "$ACR_SERVER/fivercable/ms_${svc}:${IMAGE_TAG}"
done

echo "==> Entorno de Azure Container Apps $ACA_ENV"
az extension add --name containerapp --upgrade -y -o none 2>/dev/null || true
az containerapp env show -n "$ACA_ENV" -g "$RG" -o none 2>/dev/null || \
  az containerapp env create -n "$ACA_ENV" -g "$RG" -l "$LOCATION" -o none

desplegar() {  # $1=servicio $2=puerto $3=variables extra
  local app="ms-$1"
  local envs="DATABASE_URL=secretref:database-url JWT_SECRET=secretref:jwt-secret PORT=$2 DB_POOL_MIN_SIZE=$POOL_MIN_SIZE DB_POOL_MAX_SIZE=$POOL_MAX_SIZE DB_POOL_TIMEOUT_SECONDS=$POOL_TIMEOUT $3"
  if az containerapp show -n "$app" -g "$RG" -o none 2>/dev/null; then
    az containerapp secret set -n "$app" -g "$RG" \
      --secrets database-url="$DATABASE_URL" jwt-secret="$JWT_SECRET_STAGING" -o none
    az containerapp update -n "$app" -g "$RG" \
      --image "$ACR_SERVER/fivercable/ms_$1:$IMAGE_TAG" \
      --min-replicas 0 --max-replicas "$MAX_REPLICAS" --set-env-vars $envs -o none
  else
    az containerapp create -n "$app" -g "$RG" --environment "$ACA_ENV" \
      --image "$ACR_SERVER/fivercable/ms_$1:$IMAGE_TAG" \
      --registry-server "$ACR_SERVER" --registry-username "$ACR_USER" --registry-password "$ACR_PASS" \
      --target-port "$2" --ingress external --min-replicas 0 --max-replicas "$MAX_REPLICAS" \
      --cpu 0.25 --memory 0.5Gi \
      --secrets database-url="$DATABASE_URL" jwt-secret="$JWT_SECRET_STAGING" \
      --env-vars $envs -o none
  fi
  az containerapp show -n "$app" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv
}

AUTH_FQDN=$(desplegar auth 3000 "")
CAT_FQDN=$(desplegar catalogo 3001 "")
PED_FQDN=$(desplegar pedidos 3002 "")
PAG_FQDN=$(desplegar pagos 3003 "AUTH_PUBLIC_URL=https://${AUTH_FQDN} CATALOGO_PUBLIC_URL=https://${CAT_FQDN} PEDIDOS_PUBLIC_URL=https://${PED_FQDN}")

echo "==> Limitar CORS de los servicios al portal web"
for svc in auth catalogo pedidos; do
  az containerapp update -n "ms-${svc}" -g "$RG" \
    --set-env-vars "CORS_ORIGINS=https://${PAG_FQDN}" -o none
done

echo "==> Verificación de salud"
for f in "$AUTH_FQDN" "$CAT_FQDN" "$PED_FQDN" "$PAG_FQDN"; do
  for i in $(seq 1 20); do
    if curl -fsS "https://$f/health" | grep -q '"estado":"OK"'; then echo "OK  https://$f"; break; fi
    sleep 6
    [ "$i" = 20 ] && { echo "FALLÓ https://$f/health"; exit 1; }
  done
done

# Variables para los smoke tests del pipeline
echo "##vso[task.setvariable variable=AUTH_URL]https://${AUTH_FQDN}"
echo "##vso[task.setvariable variable=CATALOGO_URL]https://${CAT_FQDN}"
echo "##vso[task.setvariable variable=PEDIDOS_URL]https://${PED_FQDN}"
echo "##vso[task.setvariable variable=PAGOS_URL]https://${PAG_FQDN}"
echo "##vso[task.setvariable variable=STAGING_DATABASE_URL;issecret=true]${DATABASE_URL}"
echo "Portal de cobro en campo: https://${PAG_FQDN}/portal"
