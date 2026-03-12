# Guide de Correction - Lab L11 : Le Grand Défi du Debug

Ce guide détaille les étapes de résolution pour le lab de synthèse L11.

## 1. Préparation de l'environnement
Le CLI nettoie automatiquement le namespace au démarrage.
```bash
kubectl create namespace mon-namespace
```
Appliquez le quota (512Mi max) :
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota-equipe
  namespace: mon-namespace
spec:
  hard:
    requests.memory: "512Mi"
```

---

## 2. Dépannage du Backend (Redis)
### Problème : Le Pod reste en 'Pending' ou 'ErrImagePull'
**Diagnostic :**
- `kubectl describe pod backend-db -n mon-namespace`
- Vous verrez deux erreurs :
  1. `0/1 nodes are available: 1 node(s) didn't match Pod's node affinity/selector.` (Car zone=lyon n'existe pas)
  2. `Failed to pull image "redis:7.9.9": rpc error: code = NotFound` (Tag inexistant)

**Correction (`backend-db.yaml`) :**
- Changez `zone: lyon` par `zone: paris`.
- Changez `image: redis:7.9.9` par `redis:7.2`.
- Réduisez `requests.memory` à `128Mi` pour passer sous le quota de 512Mi.

---

## 3. Dépannage du Service Backend
### Problème : Le service n'a pas d'Endpoints
**Diagnostic :**
- `kubectl get endpoints backend-service -n mon-namespace` (Affiche `<none>`)
- `kubectl get pod --show-labels -n mon-namespace`

**Correction (`backend-service.yaml`) :**
- Le sélecteur du service cherche `app: database`, mais le pod a le label `app: redis-db`.
- Modifiez le `spec.selector` du Service pour mettre `app: redis-db`.

---

## 4. Dépannage du Frontend (Nginx)
### Problème : Les Pods ne sont pas créés ou crash (OOMKilled)
**Diagnostic :**
- `kubectl describe deployment frontend-app -n mon-namespace`
- Vous verrez : `selector does not match template labels`.

**Correction (`frontend-deploy.yaml`) :**
- Harmonisez les labels : assurez-vous que `spec.selector.matchLabels.app` est identique à `spec.template.metadata.labels.app` (utilisez `web-ui`).
- Augmentez `limits.memory` à `64Mi` car `10Mi` est trop faible pour Nginx et causera un `OOMKilled`.

---

## 5. Validation Finale
Lancez la commande :
```bash
python3 kubeschool.py check labs/11-debug-challenge.yaml
```
Tous les tests doivent passer au vert.
