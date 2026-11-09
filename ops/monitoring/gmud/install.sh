#!/usr/bin/env bash
set -Eeuo pipefail
source_dir="${1:?validated staged source required}"
root=/opt/cosmotech/gmud-observer
install -d -m 0755 "$root/src" "$root/scripts" /var/lib/cosmotech-gmud-observer
install -m 0644 "$source_dir/src/gmud_metrics.py" "$root/src/"
install -m 0644 "$source_dir/scripts/collect_gmud_metrics.py" "$root/scripts/"
install -m 0644 "$source_dir/ops/monitoring/gmud/cosmotech-gmud-observer.service" /etc/systemd/system/
install -m 0644 "$source_dir/ops/monitoring/gmud/cosmotech-gmud-observer.timer" /etc/systemd/system/
install -m 0644 "$source_dir/ops/monitoring/gmud/nginx-gmud.conf" /etc/nginx/snippets/cosmotech-gmud-metrics.conf
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/nginx/conf.d/cosmotech-itsm-public.conf');s=p.read_text();line='    include /etc/nginx/snippets/cosmotech-gmud-metrics.conf;'
if line not in s:
 if s.count('    listen 8088 default_server;')!=1:raise SystemExit('Expected one private metrics server')
 b=p.with_suffix('.before-gmud-observer');b.write_text(s);b.chmod(0o600)
 p.write_text(s.replace('    listen 8088 default_server;','    listen 8088 default_server;\n'+line,1))
PY
if ! nginx -t; then
 cp /etc/nginx/conf.d/cosmotech-itsm-public.before-gmud-observer /etc/nginx/conf.d/cosmotech-itsm-public.conf
 exit 1
fi
systemctl daemon-reload
systemctl start cosmotech-gmud-observer.service
systemctl enable --now cosmotech-gmud-observer.timer
systemctl reload nginx
