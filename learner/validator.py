import json
from kubernetes import client, config
from jsonpath_ng import jsonpath, parse

class LabValidator:
    def __init__(self, context_name="kind-kind"):
        # On charge la config du cluster Kind
        try:
            config.load_kube_config(context=context_name)
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.custom_objects = client.CustomObjectsApi()
            self.api_client = client.ApiClient()
        except Exception as e:
            # We don't want to crash here if the cluster doesn't exist yet
            self.apps_v1 = None
            self.core_v1 = None
            self.custom_objects = None
            self.api_client = None

    def _refresh_config(self, context_name):
        try:
            config.load_kube_config(context=context_name)
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.custom_objects = client.CustomObjectsApi()
            self.api_client = client.ApiClient()
            return True
        except:
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

    def check_resource_exists(self, rule):
        kind = rule["kind"].lower()
        name = rule["name"]
        ns = rule.get("namespace", "default")

        try:
            if kind == "pod":
                self.core_v1.read_namespaced_pod(name, ns)
            elif kind == "deployment":
                self.apps_v1.read_namespaced_deployment(name, ns)
            elif kind == "service":
                self.core_v1.read_namespaced_service(name, ns)
            elif kind == "namespace":
                self.core_v1.read_namespace(name)
            else:
                return False, f"Kind '{kind}' non supporté pour 'resource_exists'"
            return True, f"Ressource {kind}/{name} trouvée."
        except Exception as e:
            return False, f"Ressource {kind}/{name} introuvable ou erreur : {str(e)}"

    def check_jsonpath(self, rule):
        kind = rule["kind"].lower()
        name = rule["name"]
        ns = rule.get("namespace", "default")
        path = rule["path"]
        expected = rule["expected"]

        try:
            if kind == "pod":
                obj = self.core_v1.read_namespaced_pod(name, ns)
            elif kind == "deployment":
                obj = self.apps_v1.read_namespaced_deployment(name, ns)
            elif kind == "service":
                obj = self.core_v1.read_namespaced_service(name, ns)
            else:
                return False, f"Kind '{kind}' non supporté pour 'jsonpath_assert'"

            # Conversion de l'objet K8s en dictionnaire JSON
            obj_dict = self.api_client.sanitize_for_serialization(obj)

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
