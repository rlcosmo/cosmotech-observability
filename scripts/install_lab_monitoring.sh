#!/usr/bin/env bash
set -Eeuo pipefail
source_dir="${1:?staged source directory required}"
install -d -m 0755 /opt/cosmotech/monitoring /var/lib/cosmotech-monitoring /etc/nginx/snippets
install -m 0644 "$source_dir/lab_monitoring.py" /opt/cosmotech/monitoring/lab_monitoring.py
install -m 0644 "$source_dir/cosmotech-monitoring.service" /etc/systemd/system/
install -m 0644 "$source_dir/cosmotech-monitoring.timer" /etc/systemd/system/
install -m 0644 "$source_dir/nginx-metrics.conf" /etc/nginx/snippets/cosmotech-lab-metrics.conf
python3 - <<'PY'
from pathlib import Path
path = Path('/etc/nginx/conf.d/cosmotech-itsm-public.conf')
original = path.read_text()
include = '    include /etc/nginx/snippets/cosmotech-lab-metrics.conf;'
if include not in original:
    if original.count('    listen 8088 default_server;') != 1:
        raise SystemExit('Expected exactly one existing private default server')
    backup = path.with_suffix('.before-lab-monitoring')
    if not backup.exists():
        backup.write_text(original)
    path.write_text(original.replace('    listen 8088 default_server;', '    listen 8088 default_server;\n' + include, 1))
PY
if ! nginx -t; then
  cp /etc/nginx/conf.d/cosmotech-itsm-public.before-lab-monitoring /etc/nginx/conf.d/cosmotech-itsm-public.conf
  exit 1
fi
systemctl reload nginx
systemctl daemon-reload
systemctl enable --now cosmotech-monitoring.timer
systemctl start --no-block cosmotech-monitoring.service
printf '%s\n' 'Collector scheduled; existing application services preserved.'
