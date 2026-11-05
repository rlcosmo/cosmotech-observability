import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

spec = importlib.util.spec_from_file_location("lab_monitoring", Path(__file__).parents[1] / "src/lab_monitoring.py")
monitoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitoring)


def test_costs_keep_credits_refunds_and_gross_separate_and_merge_pages():
    def group(record_type, amount):
        return {"Keys": ["Amazon S3", record_type], "Metrics": {"UnblendedCost": {"Amount": amount, "Unit": "USD"}}}

    def day(groups):
        return {"TimePeriod": {"Start": "2026-11-01"}, "Estimated": True, "Groups": groups}

    samples = monitoring.cost_samples({"ResultsByTime": [
        day([group("Usage", "10.12"), group("Credit", "-3.01")]),
        day([group("Usage", "0.08"), group("Refund", "-0.20")]),
    ]})
    assert "lab_aws_cost_mtd_gross_usd 10.20" in samples
    assert "lab_aws_cost_mtd_credits_applied_usd 3.01" in samples
    assert "lab_aws_cost_mtd_net_usd 6.99" in samples
    assert samples.count('lab_aws_cost_daily_usd{date="2026-11-01"} 10.20') == 1


def test_missing_credit_balance_is_not_rendered_as_zero():
    with (patch.object(monitoring, "aws", return_value={"accountPlanType": "PAID"}),
          pytest.raises(ValueError, match="unavailable")):
        monitoring.collect_credits()


def test_eks_tags_exclude_nodes_without_relying_on_names():
    assert monitoring.is_eks_node({"Tags": [{"Key": "eks:cluster-name", "Value": "lab"}]})
    assert not monitoring.is_eks_node({"Tags": [{"Key": "Name", "Value": "cosmotech-itsm-dev"}]})


def test_metric_labels_cannot_inject_another_sample():
    sample = monitoring.metric("test", 1, tool='a"\nb')
    assert "\n" not in sample
    assert '\\n' in sample


def test_failed_host_probe_preserves_service_name_but_never_cached_up():
    payload = {'observed_at': 10, 'services': [{'application': 'Zabbix', 'service': 'server',
        'manager': 'docker compose', 'repair': 'docker compose up -d server', 'status': 1, 'state': 'running'}]}
    samples = monitoring.host_samples(payload, 'i-test', 'zabbix', 0)
    status = next(s for s in samples if s.startswith('lab_ec2_application_service_status'))
    assert 'app_service="server"' in status
    assert status.endswith(' -1')
    assert any('state="probe unavailable"' in s for s in samples)


def test_down_service_and_disk_usage_are_reported_with_host_identity():
    payload = {'observed_at': 10, 'services': [{'application': 'Zabbix', 'service': 'server',
        'manager': 'docker compose', 'repair': 'docker compose up -d server', 'status': 0, 'state': 'exited'}],
        'filesystems': [{'mountpoint': '/', 'device': '/dev/root', 'filesystem': 'ext4',
        'size_bytes': 1000, 'used_bytes': 900, 'available_bytes': 100, 'used_percent': 90}]}
    samples = monitoring.host_samples(payload, 'i-test', 'zabbix', 1)
    assert next(s for s in samples if s.startswith('lab_ec2_application_service_status')).endswith(' 0')
    assert next(s for s in samples if s.startswith('lab_ec2_filesystem_used_percent')).endswith(' 90')


def test_zabbix_counts_keep_acknowledged_but_exclude_resolved_suppressed_and_disabled():
    def problem(event, severity, **extra):
        return {'eventid': event, 'objectid': 't', 'severity': str(severity), 'clock': '100',
                'name': 'Service "api" unavailable\nsecond line', **extra}
    problems = [problem('1', 5, acknowledged='1'), problem('2', 4), problem('3', 2, suppressed='1'),
                problem('4', 3, r_eventid='9'), problem('1', 5), {**problem('5', 3), 'objectid': 'disabled'}]
    triggers = [{'triggerid': 't', 'hosts': [{'host': 'api', 'name': 'Orders API'}]}]
    samples = monitoring.zabbix_problem_samples(problems, triggers)
    counts = [s for s in samples if s.startswith('lab_zabbix_problem_count')]
    assert any('severity_name="Disaster"' in s and s.endswith(' 1') for s in counts)
    assert any('severity_name="High"' in s and s.endswith(' 1') for s in counts)
    assert any('severity_name="Warning"' in s and s.endswith(' 0') for s in counts)
    active = [s for s in samples if s.startswith('lab_zabbix_problem_active')]
    assert len(active) == 2 and any('acknowledged="1"' in s for s in active)
    assert all('\n' not in s for s in active)


def test_zabbix_failed_api_cannot_be_rendered_as_zero(monkeypatch):
    monkeypatch.setattr(monitoring, 'aws', lambda *args: {'SecretString': '{"api_token":"private",'
        '"api_url":"https://zabbix.cosmotechsolutions.com.br/api_jsonrpc.php","token_expires_at":9999999999}'})
    with (patch.object(monitoring, 'zabbix_request', side_effect=RuntimeError('API unavailable')),
          pytest.raises(RuntimeError, match='API unavailable')):
        monitoring.collect_zabbix_problems()


def test_command_center_rejects_write_api_calls():
    with pytest.raises(ValueError, match='read-only'):
        monitoring.zabbix_request('private', 'event.acknowledge', {})
