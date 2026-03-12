# KubeSchool - Plateforme Learning by Doing Kubernetes

KubeSchool est une solution légère pour déployer des labs Kubernetes sur des postes locaux (Ubuntu 24.04) via Kind, avec un suivi centralisé pour le formateur.

## 🚀 Démarrage Rapide

### 👨‍🏫 Pour le Formateur (Serveur de Monitoring)
1. Naviguez dans le dossier trainer :
   ```bash
   cd trainer
   ```
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancez le serveur :
   ```bash
   python3 server.py
   ```
4. Notez votre adresse IP (ex: `192.168.1.15`) pour la donner aux stagiaires. Le dashboard est accessible sur `http://localhost:8000`.

### 🎓 Pour l'Apprenant (Poste Stagiaire)
1. Naviguez dans le dossier learner :
   ```bash
   cd learner
   ```
2. Installez l'environnement :
   ```bash
   bash installer.sh
   ```
3. Activez l'environnement virtuel et configurez votre identité :
   ```bash
   source .venv/bin/activate
   python3 kubeschool.py config --user "VotreNom" --server <IP_FORMATEUR>
   ```
4. Démarrez un lab :
   ```bash
   python3 kubeschool.py start ../labs/01-intro-pod.yaml
   ```
5. Une fois l'exercice terminé avec `kubectl`, vérifiez votre travail :
   ```bash
   python3 kubeschool.py check ../labs/01-intro-pod.yaml
   ```

## 📂 Structure du Projet
- `labs/` : Définitions des exercices (YAML).
- `learner/` : Outils pour les stagiaires (CLI, Validator).
- `trainer/` : Outils pour le formateur (Dashboard, Solutions).
- `docs/` : Documentation détaillée.

## 📖 Documentation
- [Dossier d'Architecture](docs/architecture.md)
- [Guide d'Installation](docs/install-guide.md)
- [Dépannage](docs/troubleshooting.md)
