import unittest
from unittest.mock import MagicMock, patch
from validator import LabValidator

class TestLabValidator(unittest.TestCase):

    @patch('kubernetes.config.load_kube_config')
    @patch('kubernetes.dynamic.DynamicClient')
    def setUp(self, mock_dynamic, mock_kube_config):
        self.validator = LabValidator(context_name="test-context")
        self.validator.dynamic_client = MagicMock()

    def test_check_resource_exists_success(self):
        # Mocking dynamic client and resource
        mock_resource = MagicMock()
        mock_resource.namespaced = True
        self.validator.dynamic_client.resources.search.return_value = [mock_resource]

        rule = {"kind": "Pod", "name": "test-pod", "type": "resource_exists"}
        success, message = self.validator.check_resource_exists(rule)

        self.assertTrue(success)
        self.assertIn("trouvée", message)
        mock_resource.get.assert_called_with(name="test-pod", namespace="default")

    def test_check_resource_exists_failure(self):
        mock_resource = MagicMock()
        mock_resource.namespaced = True
        mock_resource.get.side_effect = Exception("Not found")
        self.validator.dynamic_client.resources.search.return_value = [mock_resource]

        rule = {"kind": "Pod", "name": "wrong-pod", "type": "resource_exists"}
        success, message = self.validator.check_resource_exists(rule)

        self.assertFalse(success)
        self.assertIn("introuvable", message)

    def test_check_jsonpath_success(self):
        mock_resource = MagicMock()
        mock_resource.namespaced = True
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {
            "metadata": {"labels": {"app": "apache"}},
            "spec": {"containers": [{"image": "httpd:2.4"}]}
        }
        mock_resource.get.return_value = mock_obj
        self.validator.dynamic_client.resources.search.return_value = [mock_resource]

        rule = {
            "kind": "Pod",
            "name": "my-pod",
            "path": "metadata.labels.app",
            "expected": "apache"
        }
        success, message = self.validator.check_jsonpath(rule)
        self.assertTrue(success)
        self.assertIn("Validation réussie", message)

    def test_check_jsonpath_failure(self):
        mock_resource = MagicMock()
        mock_resource.namespaced = True
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {
            "metadata": {"labels": {"app": "nginx"}}
        }
        mock_resource.get.return_value = mock_obj
        self.validator.dynamic_client.resources.search.return_value = [mock_resource]

        rule = {
            "kind": "Pod",
            "name": "my-pod",
            "path": "metadata.labels.app",
            "expected": "apache"
        }
        success, message = self.validator.check_jsonpath(rule)
        self.assertFalse(success)
        self.assertIn("est 'nginx', attendu 'apache'", message)

if __name__ == '__main__':
    unittest.main()
