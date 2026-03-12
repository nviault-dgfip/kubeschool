import yaml
import unittest
from unittest.mock import MagicMock, patch
from learner.validator import LabValidator

class TestLabsLogic(unittest.TestCase):
    def setUp(self):
        # Patch load_kube_config to avoid connection errors during initialization
        self.patcher = patch('kubernetes.config.load_kube_config')
        self.mock_load_config = self.patcher.start()

        # Initialize the validator with a dummy context
        self.validator = LabValidator(context_name="mock-context")
        self.validator.dynamic_client = MagicMock()

    def tearDown(self):
        self.patcher.stop()

    def mock_resource_get(self, mock_obj_dict, namespaced=True):
        """Helper to create a mocked Kubernetes resource returning a specific state."""
        mock_resource = MagicMock()
        mock_resource.namespaced = namespaced
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = mock_obj_dict
        mock_resource.get.return_value = mock_obj
        return mock_resource

    def test_l02_pod_bad_image(self):
        with open('labs/02-pod-bad-image.yaml', 'r') as f:
            lab = yaml.safe_load(f)

        # Successful state: Pod Running with correct image
        success_state = {
            "metadata": {"name": "nginx", "namespace": "mon-namespace"},
            "spec": {"containers": [{"image": "nginx:1.29.4"}]},
            "status": {"phase": "Running"}
        }

        mock_pod_res = self.mock_resource_get(success_state)
        mock_ns_res = self.mock_resource_get({"metadata": {"name": "mon-namespace"}}, namespaced=False)

        def side_effect(kind, **kwargs):
            k = kind.lower()
            if k == "pod": return [mock_pod_res]
            if k == "namespace": return [mock_ns_res]
            return []

        self.validator.dynamic_client.resources.search.side_effect = side_effect

        # Bypass connection check
        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l03_replicaset_bad(self):
        with open('labs/03-replicaset-bad.yaml', 'r') as f:
            lab = yaml.safe_load(f)

        success_state = {
            "metadata": {"name": "nginx-rs", "namespace": "mon-namespace"},
            "spec": {
                "replicas": 3,
                "selector": {"matchLabels": {"app": "mon-nginx-rs"}}
            },
            "status": {
                "replicas": 3,
                "readyReplicas": 3
            }
        }

        mock_rs_res = self.mock_resource_get(success_state)
        self.validator.dynamic_client.resources.search.return_value = [mock_rs_res]

        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l04_deployment_bad_labels(self):
        with open('labs/04-deployment-bad-labels.yaml', 'r') as f:
            lab = yaml.safe_load(f)

        success_state = {
            "metadata": {"name": "nginx-deployment", "namespace": "mon-namespace"},
            "spec": {
                "selector": {"matchLabels": {"app": "nginx-dp"}}
            },
            "status": {
                "availableReplicas": 3
            }
        }

        mock_deploy_res = self.mock_resource_get(success_state)
        self.validator.dynamic_client.resources.search.return_value = [mock_deploy_res]

        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l05_pvc_bad_class(self):
        with open('labs/05-pvc-bad-class.yaml', 'r') as f:
            lab = yaml.safe_load(f)

        success_state = {
            "metadata": {"name": "mon-pvc-class", "namespace": "mon-namespace"},
            "spec": {
                "storageClassName": "standard"
            },
            "status": {
                "phase": "Bound"
            }
        }

        mock_pvc_res = self.mock_resource_get(success_state)
        self.validator.dynamic_client.resources.search.return_value = [mock_pvc_res]

        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l06_cronjob_bad_schedule(self):
        with open('labs/06-cronjob-bad-schedule.yaml', 'r') as f:
            lab = yaml.safe_load(f)

        success_state = {
            "metadata": {"name": "mon-cronjob", "namespace": "mon-namespace"},
            "spec": {
                "schedule": "* * * * *"
            }
        }

        mock_cj_res = self.mock_resource_get(success_state)
        self.validator.dynamic_client.resources.search.return_value = [mock_cj_res]

        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

if __name__ == '__main__':
    unittest.main()
