# Guide de création de nouveaux Labs pour KubeSchool

Ce document contient les spécifications techniques et le prompt nécessaire pour générer automatiquement de nouveaux exercices (labs) pour la plateforme KubeSchool.

---

## 1. Format des fichiers

Un lab KubeSchool est composé de deux fichiers :

### A. Le fichier de définition du lab (`labs/<nom-du-lab>.yaml`)
Ce fichier définit les instructions pour l'apprenant et les règles de validation automatique.

```yaml
id: "LXX" # ID unique du lab (ex: L02)
title: "Titre du Lab"
level: "Débutant | Intermédiaire | Avancé"
objectives: |
  - Premier objectif
  - Deuxième objectif
images:
  - "image-docker:tag" # Liste des images nécessaires pour le lab (pour pré-chargement)
instructions: |
  1. Première étape...
  2. Deuxième étape...
validation_rules:
  - name: "Nom affiché du test"
    type: "resource_exists"
    kind: "Pod" # ou Deployment, Service, Role, NetworkPolicy, etc.
    api_version: "v1" # Optionnel, déduit automatiquement pour les types standards
    name: "nom-de-la-ressource"
    namespace: "default" # Optionnel

  - name: "Vérification d'un paramètre spécifique"
    type: "jsonpath_assert"
    kind: "Pod"
    name: "nom-du-pod"
    path: "spec.containers[0].image" # Chemin JSONPath (sans le $)
    expected: "nginx:latest"
```

### B. Le fichier de solution (`trainer/solutions/<nom-du-lab>-solution.yaml`)
Il s'agit d'un fichier Manifest Kubernetes standard (ou plusieurs séparés par `---`) qui permet de valider la faisabilité de l'exercice.

---

## 2. Exemples de règles de validation (JSONPath)

Voici des exemples de chemins JSONPath courants pour différents thèmes :

- **Ressources (CPU/Mémoire) :** `spec.containers[0].resources.limits.cpu`
- **PVC :** `spec.resources.requests.storage`
- **NetworkPolicy :** `spec.ingress[0].from[0].podSelector.matchLabels.role`
- **RBAC (Role) :** `rules[0].verbs[0]` (ex: "get")
- **Labels :** `metadata.labels.app`
- **Affinité :** `spec.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[0].matchExpressions[0].key`

---

## 3. Prompt de génération (Meta-Prompt)

Copiez-collez le texte ci-dessous dans un LLM (GPT-4, Claude 3.5 Sonnet, etc.) pour créer votre lab.

```markdown
# PROMPT DE CRÉATION DE LAB KUBESCHOOL

Tu es un expert Kubernetes et un ingénieur pédagogique. Ta mission est de créer un nouveau lab pour la plateforme KubeSchool.

## CONTEXTE DU LAB
- Niveau des stagiaires : [INDIQUER LE NIVEAU ICI, ex: Débutant]
- Objectifs pédagogiques : [INDIQUER LES OBJECTIFS ICI, ex: Comprendre les PVC et le stockage persistant]
- Plan de formation / Thème : [INDIQUER LE THÈME OU LE PLAN ICI]
- Nom suggéré pour le lab : [INDIQUER LE NOM ICI]

## TRAVAIL À RÉALISER
Génère deux blocs de code distincts :

1. **Le fichier YAML du lab** (à placer dans `labs/`) :
   - Utilise un ID logique (ex: L02).
   - Reprend les objectifs pédagogiques fournis.
   - Rédige des instructions claires et progressives en français.
   - Définit des `validation_rules` robustes utilisant `resource_exists` et `jsonpath_assert`.
   - Inclus l'attribut `api_version` dans les règles pour les types complexes (RBAC, NetworkPolicy, etc.).

2. **Le fichier YAML de solution** (à placer dans `trainer/solutions/`) :
   - Manifest Kubernetes complet et fonctionnel permettant de réussir tous les tests du lab.

## EXEMPLE DE RÉFÉRENCE (Few-Shot)
ID: L01
Titre: Premier pas avec les Pods
Instructions:
  1. Créez un Pod nommé 'my-apache-pod'
  2. Image 'httpd:2.4'
  3. Label 'app: apache'
Validation:
  - type: resource_exists, kind: Pod, name: my-apache-pod
  - type: jsonpath_assert, kind: Pod, name: my-apache-pod, path: spec.containers[0].image, expected: httpd:2.4

Réponds uniquement en générant les deux blocs de code YAML.
```
