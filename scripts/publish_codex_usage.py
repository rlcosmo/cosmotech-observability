"""Publish only quota percentages/reset timestamps through a scoped STS role; no account credentials leave this host."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import selectors
import subprocess
import tempfile
import time
from pathlib import Path


def read_quota() -> dict:
    process = subprocess.Popen(['codex', 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, bufsize=1)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    def send(value: dict) -> None:
        process.stdin.write(json.dumps(value) + '\n')
        process.stdin.flush()

    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'cosmotech_quota_readonly', 'version': '1.0.0'}, 'capabilities': {'experimentalApi': True}}})
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if not selector.select(timeout=1):
                continue
            line = process.stdout.readline()
            if not line:
                break
            value = json.loads(line)
            if value.get('id') == 1:
                send({'method': 'initialized'})
                send({'id': 2, 'method': 'account/rateLimits/read'})
            if value.get('id') == 2:
                if 'error' in value:
                    raise RuntimeError('Codex quota unavailable for the current authenticated session')
                return sanitize(value['result'])
        raise TimeoutError('Codex quota RPC timed out')
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def sanitize(result: dict) -> dict:
    buckets = result.get('rateLimitsByLimitId') or {'codex': result.get('rateLimits')}
    clean = {'observed_at': int(time.time()), 'buckets': {}, 'token_balance_available': False}
    for name, bucket in buckets.items():
        if not bucket:
            continue
        windows = {}
        for window in ('primary', 'secondary'):
            value = bucket.get(window)
            if not value:
                continue
            percent = float(value['usedPercent'])
            if not 0 <= percent <= 100:
                raise ValueError('Invalid quota percentage')
            windows[window] = {'usedPercent': percent, 'resetsAt': int(value['resetsAt']),
                               'windowDurationMins': int(value['windowDurationMins'])}
        clean['buckets'][name] = windows
    if not clean['buckets']:
        raise ValueError('Quota windows unavailable')
    return clean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', default='arn:aws:iam::414053644145:role/cosmotech-codex-usage-publisher')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--daemon', action='store_true', help='Publish every five minutes while this authenticated workstation runs')
    args = parser.parse_args()
    if args.daemon:
        cache = Path.home() / '.cache/cosmotech-codex-usage'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (cache / 'publisher.lock').open('w') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            while True:
                result = subprocess.run(['python3', str(Path(__file__).resolve()), '--role', args.role], capture_output=True, check=False)
                print(json.dumps({'observed_at': int(time.time()), 'publisher_success': result.returncode == 0}), flush=True)
                time.sleep(300)
        return
    value = read_quota()
    if args.output:
        args.output.write_text(json.dumps(value))
        return
    credentials = json.loads(subprocess.check_output(['aws', 'sts', 'assume-role', '--role-arn', args.role,
        '--role-session-name', 'codex-quota-publisher', '--duration-seconds', '900'], text=True))['Credentials']
    env = {**os.environ, 'AWS_ACCESS_KEY_ID': credentials['AccessKeyId'],
           'AWS_SECRET_ACCESS_KEY': credentials['SecretAccessKey'], 'AWS_SESSION_TOKEN': credentials['SessionToken']}
    with tempfile.TemporaryDirectory(prefix='codex-quota-') as directory:
        path = Path(directory) / 'quota.json'
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        subprocess.run(['aws', '--region', 'us-east-1', 'ssm', 'put-parameter', '--name',
            '/cosmotech/monitoring/codex-usage', '--type', 'String', '--overwrite', '--value', 'file://' + str(path)],
            env=env, check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'published': True, 'observed_at': value['observed_at'], 'buckets': len(value['buckets'])}))


if __name__ == '__main__':
    main()
