{'action': 'create',
 'data': {'task_id': 'ET-2026-000082', 'trigger_source': None, 'category': 'bmc', 'project_tag': 'universal',
          'repo_url': 'http://10.17.55.151:6600/litaiqing/bmc-case.git', 'branch': 'master', 'cases': [
         {'case_id': 'disk-universal-002',
          'script_path': 'tests/universal/disk/002_fw_upgrade_downgrade/test_fw_upgrade_downgrade.py',
          'script_name': 'test_fw_upgrade_downgrade.py',
          'parameters': {'target_ip': '10.17.150.220', 'ssh_username': 'root', 'ssh_password': '234234', 'ssh_port': 22,
                         'device_class': 'NVME', 'runtime_seconds': 600, 'power_cycle_count': 1, 'fw_image': '',
                         'bmc_ip': '10.17.150.220', 'bmc_username': 'ADMIN', 'bmc_password': '234',
                         'ipmi_interface': 'lanplus', 'allow_format': False, 'remote_work_dir': '/tmp'}}], 'files': {
         'fw_image': {
             'url': 'http://10.17.151.170:9000/attachments/attachments/182c6a8c-af67-4596-9908-dcbff7412946.drawio?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=admin%2F20260521%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260521T073039Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=7dc40b49043ed037b5c8530c5efb5cc0774b9b23cc3e9f8f09242cadcca74a38',
             'sha256': '8c64baf0bc1a78516c9a73754368ea448b57cca1958ce60f4374f2596aeddd4c'}},
          'pytest_options': {'log_debug': False, 'kafka_server': '10.17.154.252:9092', 'kafka_topic': 'dml-test-event',
                             'report_kafka': True, 'maxfail': '3', 'task_id': 'ET-2026-000082'}, 'timeout': 7200}}
