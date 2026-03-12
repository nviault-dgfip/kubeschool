import json
from kubernetes import client, config, dynamic
from jsonpath_ng import jsonpath, parse

class LabValidator:
    def __init__(self, context_name="kind-kind"):
        # On charge la config du cluster Kind
        self._refresh_config(context_name)

    def _refresh_config(self, context_name):
        try:
            config.load_kube_config(context=context_name)
            self.api_client = client.ApiClient()
            self.dynamic_client = dynamic.DynamicClient(self.api_client)
            return True
        except Exception:
            self.api_client = None
            self.dynamic_client = None
            return False

    def validate_all(self, rules, context_name):
        """Prend une liste de règles issues du YAML et retourne les résultats."""
        if not self._refresh_config(context_name):
            return [{"rule": "Connection", "success": False, "message": f"Impossible de se connecter au cluster {context_name}"}]

        results = []
        for rule in rules:
            rule_type = rule.get("type")
            success = False
            message = ""

            try:
                if rule_type == "resource_exists":
                    success, message = self.check_resource_exists(rule)
                elif rule_type == "jsonpath_assert":
                    success, message = self.check_jsonpath(rule)
                else:
                    message = f"Type de règle inconnu : {rule_type}"
            except Exception as e:
                message = f"Erreur lors de l'exécution du test : {str(e)}"

            results.append({"rule": rule.get("name", rule_type), "success": success, "message": message})

        return results

    def _get_resource(self, kind, api_version=None):
        """Récupère la ressource dynamiquement."""
        if api_version:
            return self.dynamic_client.resources.get(api_version=api_version, kind=kind)
        else:
            # Fallback pour les types courants si api_version n'est pas fourni
            fallbacks = {
                "pod": ("v1", "Pod"),
                "service": ("v1", "Service"),
                "namespace": ("v1", "Namespace"),
                "configmap": ("v1", "ConfigMap"),
                "secret": ("v1", "Secret"),
                "persistentvolumeclaim": ("v1", "PersistentVolumeClaim"),
                "deployment": ("apps/v1", "Deployment"),
                "statefulset": ("apps/v1", "StatefulSet"),
                "daemonset": ("apps/v1", "DaemonSet"),
                "ingress": ("networking.k8s.io/v1", "Ingress"),
                "networkpolicy": ("networking.k8s.io/v1", "NetworkPolicy"),
                "role": ("rbac.authorization.k8s.io/v1", "Role"),
                "clusterrole": ("rbac.authorization.k8s.io/v1", "ClusterRole"),
                "rolebinding": ("rbac.authorization.k8s.io/v1", "RoleBinding"),
                "clusterrolebinding": ("rbac.authorization.k8s.io/v1", "ClusterRoleBinding"),
            }
            if kind.lower() in fallbacks:
                api_v, k = fallbacks[kind.lower()]
                return self.dynamic_client.resources.get(api_version=api_v, kind=k)

            # Recherche générique
            return self.dynamic_client.resources.get(kind=kind)

    def check_resource_exists(self, rule):
        kind = rule["kind"]
        name = rule["name"]
        ns = rule.get("namespace", "default")
        api_version = rule.get("api_version")

        try:
            resource = self._get_resource(kind, api_version)
            if resource.namespaced:
                resource.get(name=name, namespace=ns)
            else:
                resource.get(name=name)
            return True, f"Ressource {kind}/{name} trouvée."
        except Exception as e:
            return False, f"Ressource {kind}/{name} introuvable ou erreur : {str(e)}"

    def check_jsonpath(self, rule):
        kind = rule["kind"]
        name = rule["name"]
        ns = rule.get("namespace", "default")
        path = rule["path"]
        expected = rule["expected"]
        api_version = rule.get("api_version")

        try:
            resource = self._get_resource(kind, api_version)
            if resource.namespaced:
                obj = resource.get(name=name, namespace=ns)
            else:
                obj = resource.get(name=name)

            # Conversion de l'objet K8s en dictionnaire JSON
            obj_dict = obj.to_dict()

            # Utilisation de jsonpath-ng pour extraire la valeur
            jsonpath_expr = parse(path)
            matches = [match.value for match in jsonpath_expr.find(obj_dict)]

            if not matches:
                return False, f"Chemin {path} non trouvé dans l'objet."

            actual_value = matches[0]
            if str(actual_value) == str(expected):
                return True, f"Validation réussie : {path} == {expected}"
            else:
                return False, f"Échec : {path} est '{actual_value}', attendu '{expected}'"
        except Exception as e:
            return False, f"Erreur : {str(e)}"
