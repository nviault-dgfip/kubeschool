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

    def validate_lab(self, filepath, mock_states):
        with open(filepath, 'r') as f:
            lab = yaml.safe_load(f)

        def side_effect(kind, **kwargs):
            k = kind.lower()
            if k in mock_states:
                return [self.mock_resource_get(mock_states[k], namespaced=mock_states[k].get("_namespaced", True))]
            return []

        self.validator.dynamic_client.resources.search.side_effect = side_effect

        with patch.object(LabValidator, '_refresh_config', return_value=True):
            results = self.validator.validate_all(lab['validation_rules'], "mock-context")

        return results

    def test_l02_pod_bad_image(self):
        mock_states = {
            "pod": {
                "metadata": {"name": "nginx", "namespace": "mon-namespace"},
                "spec": {"containers": [{"image": "nginx:1.29.4"}]},
                "status": {"phase": "Running"}
            },
            "namespace": {
                "metadata": {"name": "mon-namespace"},
                "_namespaced": False
            }
        }
        results = self.validate_lab('labs/02-pod-bad-image.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l03_replicaset_bad(self):
        mock_states = {
            "replicaset": {
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
        }
        results = self.validate_lab('labs/03-replicaset-bad.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l04_deployment_bad_labels(self):
        mock_states = {
            "deployment": {
                "metadata": {"name": "nginx-deployment", "namespace": "mon-namespace"},
                "spec": {
                    "selector": {"matchLabels": {"app": "nginx-dp"}}
                },
                "status": {
                    "availableReplicas": 3
                }
            }
        }
        results = self.validate_lab('labs/04-deployment-bad-labels.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l05_pvc_bad_class(self):
        mock_states = {
            "persistentvolumeclaim": {
                "metadata": {"name": "mon-pvc-class", "namespace": "mon-namespace"},
                "spec": {
                    "storageClassName": "standard"
                },
                "status": {
                    "phase": "Bound"
                }
            }
        }
        results = self.validate_lab('labs/05-pvc-bad-class.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l06_cronjob_bad_schedule(self):
        mock_states = {
            "cronjob": {
                "metadata": {"name": "mon-cronjob", "namespace": "mon-namespace"},
                "spec": {
                    "schedule": "* * * * *"
                }
            }
        }
        results = self.validate_lab('labs/06-cronjob-bad-schedule.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l07_resource_quotas(self):
        mock_states = {
            "resourcequota": {
                "metadata": {"name": "quota-equipe", "namespace": "mon-namespace"},
                "spec": {"hard": {"requests.memory": "512Mi"}}
            },
            "deployment": {
                "metadata": {"name": "nginx-quota", "namespace": "mon-namespace"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "resources": {"requests": {"memory": "256Mi"}}
                            }]
                        }
                    }
                },
                "status": {"availableReplicas": 1}
            }
        }
        results = self.validate_lab('labs/07-resource-quotas.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l08_node_affinity(self):
        mock_states = {
            "pod": {
                "metadata": {"name": "nginx-paris", "namespace": "mon-namespace"},
                "spec": {
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [{
                                    "matchExpressions": [{"key": "zone"}]
                                }]
                            }
                        }
                    }
                },
                "status": {"phase": "Running"}
            }
        }
        results = self.validate_lab('labs/08-node-affinity.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l09_storage_subpath(self):
        mock_states = {
            "configmap": {
                "metadata": {"name": "nginx-config", "namespace": "mon-namespace"}
            },
            "pod": {
                "metadata": {"name": "nginx-custom", "namespace": "mon-namespace"},
                "spec": {
                    "containers": [{
                        "volumeMounts": [{"subPath": "nginx.conf"}]
                    }]
                },
                "status": {"phase": "Running"}
            }
        }
        results = self.validate_lab('labs/09-storage-subpath.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l10_service_selector(self):
        mock_states = {
            "pod": {
                "metadata": {"name": "web-server-pod", "namespace": "mon-namespace"}
            },
            "service": {
                "metadata": {"name": "web-service", "namespace": "mon-namespace"},
                "spec": {"selector": {"app": "web-server"}}
            },
            "endpoints": {
                "metadata": {"name": "web-service", "namespace": "mon-namespace"}
            }
        }
        results = self.validate_lab('labs/10-service-selector.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

    def test_l11_debug_challenge(self):
        mock_states = {
            "pod": {
                "metadata": {"name": "backend-db", "namespace": "mon-namespace"},
                "status": {"phase": "Running"}
            },
            "endpoints": {
                "metadata": {"name": "backend-service", "namespace": "mon-namespace"}
            },
            "deployment": {
                "metadata": {"name": "frontend-app", "namespace": "mon-namespace"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "resources": {"limits": {"memory": "64Mi"}}
                            }]
                        }
                    }
                },
                "status": {"availableReplicas": 2}
            }
        }
        results = self.validate_lab('labs/11-debug-challenge.yaml', mock_states)
        for r in results:
            self.assertTrue(r['success'], f"Rule failed: {r['rule']} - {r['message']}")

if __name__ == '__main__':
    unittest.main()
