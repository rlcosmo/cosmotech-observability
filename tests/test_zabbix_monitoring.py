"""Regressions for Zabbix 8 preprocessing and safe configuration updates."""
import importlib.util
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

spec = importlib.util.spec_from_file_location('monitoring_config', Path(__file__).parents[1]/'ops/zabbix-monitoring/configure_monitoring.py')
monitoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitoring)


def test_existing_item_keeps_identity_and_normalizes_required_preprocessing_fields():
    z = monitoring.Zabbix.__new__(monitoring.Zabbix)
    z.api = Mock(side_effect=[[{'itemid': 'existing'}], {'itemids': ['existing']}])
    result = z.item('host', 'safe.key', 'Test', type=18, master_itemid='master',
                    preprocessing=[{'type': 12, 'params': '$.value'}])
    assert result == 'existing'
    operation, payload = z.api.call_args.args
    assert operation == 'item.update' and 'hostid' not in payload
    assert payload['preprocessing'][0]['error_handler'] == 0
    assert payload['preprocessing'][0]['error_handler_params'] == ''


def test_api_error_redacts_known_credentials():
    z = monitoring.Zabbix.__new__(monitoring.Zabbix)
    z.token, z.protected = None, ['private-value']
    response = BytesIO(json.dumps({'error': {'code': -1, 'data': 'Invalid private-value'}}).encode())
    with patch.object(monitoring.urllib.request, 'urlopen', return_value=response), pytest.raises(RuntimeError) as error:
        z.api('item.create', {})
    assert 'private-value' not in str(error.value)
    assert '<redacted>' in str(error.value)


def load_discovery():
    import sys
    directory = Path(__file__).parents[1]/'ops/zabbix-monitoring'
    module_spec = importlib.util.spec_from_file_location('discovery_config', directory/'configure_discovery.py')
    module = importlib.util.module_from_spec(module_spec)
    with patch.object(sys, 'path', [str(directory), *sys.path]):
        module_spec.loader.exec_module(module)
    return module


def test_backup_role_signature_fix_is_bounded_and_idempotent():
    discovery = load_discovery()
    original = "AWS.request('GET', AWS.params.sts_region, 'sts', AWS.prepareParams(payload))"
    fixed = discovery.fix_backup_script(original)
    assert "AWS.request('GET', '/', AWS.params.sts_region" in fixed
    assert discovery.fix_backup_script(fixed) == fixed
    ordinary = "AWS.request('GET', region, 'ec2', params)"
    assert discovery.fix_backup_script(ordinary) == ordinary


def test_native_http_discovery_avoids_ip_and_duplicate_name_failures():
    discovery = load_discovery()
    calls = []

    def api(method, params):
        calls.append((method, params))
        if method == 'template.get':
            return [{'templateid': 'aws'}] if params['filter']['host'] == 'AWS by HTTP' else []
        if method == 'discoveryrule.get':
            return [{'itemid': 'rule', 'key_': 'aws.ec2.discovery', 'type': '18', 'parameters': []}]
        if method == 'hostprototype.get':
            return [{'hostid': 'prototype', 'host': '{#AWS.EC2.INSTANCE.ID}',
                     'name': 'EC2 - {#AWS.EC2.INSTANCE.NAME}', 'custom_interfaces': '1'}]
        return {}

    z = Mock()
    z.api.side_effect = api
    discovery.repair_aws_template_defaults(z, 'cloud-group')
    payload = next(params for method, params in calls if method == 'hostprototype.update')
    assert payload['custom_interfaces'] == 0
    assert '{#AWS.EC2.INSTANCE.ID}' in payload['name']
    assert payload['groupLinks'] == [{'groupid': 'cloud-group'}]


def test_optional_vault_fields_preserve_transform_error_semantics():
    discovery = load_discovery()
    original = [{'type': '12', 'params': '$.LockDate', 'error_handler': '0', 'error_handler_params': ''},
                {'type': '15', 'params': 'null', 'error_handler': '2', 'error_handler_params': 'Not locked'},
                {'type': '21', 'params': 'return value;', 'error_handler': '0', 'error_handler_params': ''}]
    result = discovery.optional_preprocessing(original)
    assert result[0]['error_handler'] == result[1]['error_handler'] == 1
    assert result[2] == original[2]
    assert original[0]['error_handler'] == '0'


def test_optional_vault_reconciliation_preserves_api_failure_visibility():
    discovery = load_discovery()
    z = Mock()
    z.api.side_effect = [[{'hostid': 'vault', 'parentTemplates': [{'name': 'AWS Backup Vault by HTTP'}]}],
                         [{'lastvalue': json.dumps({'error': 'AccessDenied'})}]]
    discovery.configure_optional_vault_items(z)
    assert all(call.args[0] != 'item.update' for call in z.api.call_args_list)


def test_optional_vault_reconciliation_reenables_configured_fields_only():
    discovery = load_discovery()
    z = Mock()
    z.api.side_effect = [[{'hostid': 'vault', 'parentTemplates': [{'name': 'AWS Backup Vault by HTTP'}]}],
                         [{'lastvalue': json.dumps({'BackupVaultName': 'test', 'MinRetentionDays': 7})}],
                         [{'itemid': 'min', 'key_': 'aws.backup_vault.retention.min', 'status': '1'},
                          {'itemid': 'max', 'key_': 'aws.backup_vault.retention.max', 'status': '0'}], {}, {}]
    discovery.configure_optional_vault_items(z)
    updates = [call.args[1] for call in z.api.call_args_list if call.args[0] == 'item.update']
    assert updates == [{'itemid': 'min', 'status': 0}, {'itemid': 'max', 'status': 1}]
