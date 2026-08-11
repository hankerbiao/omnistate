#!/bin/sh

set -eu

echo "[docker-init] validating MongoDB runtime configuration"
python scripts/migrations/migrate_runtime_config_to_db.py \
  --base "${CONFIG_PATH}" \
  --environment "${DML_ENV:-production}" \
  --metadata-only

echo "[docker-init] synchronizing MongoDB indexes"
python scripts/init/sync_indexes.py

echo "[docker-init] synchronizing workflow configuration"
python scripts/init/sync_workflow.py

echo "[docker-init] synchronizing RBAC roles"
python scripts/init/sync_rbac.py

if [ -n "${DML_ADMIN_PASSWORD:-}" ]; then
  echo "[docker-init] synchronizing administrator"
  set -- \
    scripts/init/create_user.py \
    --user-id "${DML_ADMIN_USER_ID:-admin}" \
    --username "${DML_ADMIN_USERNAME:-系统管理员}" \
    --password-env DML_ADMIN_PASSWORD \
    --roles ADMIN \
    --upsert

  if [ -n "${DML_ADMIN_EMAIL:-}" ]; then
    set -- "$@" --email "${DML_ADMIN_EMAIL}"
  fi

  python "$@"
else
  echo "[docker-init] DML_ADMIN_PASSWORD is unset; administrator synchronization skipped"
fi

echo "[docker-init] completed"

