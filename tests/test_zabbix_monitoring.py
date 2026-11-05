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
