import os
import sys
import yaml
import httpx
import subprocess
import json
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from validator import LabValidator

console = Console()

# --- CONFIGURATION ---
CONFIG_FILE = Path.home() / ".kubeschool.json"
DEFAULT_CLUSTER_NAME = "kubeschool-cluster"

class KubeSchoolCLI:
    def __init__(self):
        self.config = self.load_config()
        self.username = self.config.get("username", os.getenv("USER", "apprenant"))
        self.server_ip = self.config.get("server_ip", "127.0.0.1")
        self.server_url = f"http://{self.server_ip}:8000/report"
        self.cluster_name = DEFAULT_CLUSTER_NAME
        self.validator = LabValidator(context_name=f"kind-{self.cluster_name}")

    def load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                "username": self.username,
                "server_ip": self.server_ip
            }, f, indent=4)

    def configure(self, username=None, server_ip=None):
        if username:
            self.username = username
        if server_ip:
            self.server_ip = server_ip
        self.save_config()
        console.print(f"[green]Configuration mise à jour : Utilisateur={self.username}, Serveur={self.server_ip}[/green]")

    def run_shell(self, cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)

    def start_lab(self, lab_file):
        if not os.path.exists(lab_file):
            console.print(f"[red]Erreur : Le fichier {lab_file} n'existe pas.[/red]")
            return

        with open(lab_file, 'r') as f:
            lab_data = yaml.safe_load(f)

        console.print(Panel(f"[bold blue]Démarrage du Lab : {lab_data['title']}[/bold blue]"))

        # 1. Vérifier/Créer le cluster Kind
        check_cluster = self.run_shell(f"kind get clusters | grep {self.cluster_name}")
        if check_cluster.returncode != 0:
            with console.status("[bold green]Création du cluster Kind (cela peut prendre 1 min)..."):
                res = self.run_shell(f"kind create cluster --name {self.cluster_name}")
                if res.returncode != 0:
                    console.print(f"[red]Erreur lors de la création du cluster : {res.stderr}[/red]")
                    return

        # 2. Pré-chargement des images
        images = lab_data.get('images', [])
        if images:
            with Progress() as progress:
                task = progress.add_task("[cyan]Pré-chargement des images...", total=len(images))
                for img in images:
                    progress.console.print(f"Chargement de {img}...")
                    self.run_shell(f"docker pull {img}")
                    self.run_shell(f"kind load docker-image {img} --name {self.cluster_name}")
                    progress.update(task, advance=1)

        console.print(f"\n[bold yellow]Instructions :[/bold yellow]\n{lab_data['instructions']}")
        console.print(f"\n[grey]Utilisez 'kubectl' pour réaliser l'exercice. Une fois fini, lancez la vérification.[/grey]")
        console.print(f"[bold cyan]Commande de vérification :[/bold cyan] python3 kubeschool.py check {lab_file}")

    def check_lab(self, lab_file):
        if not os.path.exists(lab_file):
            console.print(f"[red]Erreur : Le fichier {lab_file} n'existe pas.[/red]")
            return

        with open(lab_file, 'r') as f:
            lab_data = yaml.safe_load(f)

        with console.status("[bold cyan]Vérification de votre travail..."):
            results = self.validator.validate_all(lab_data['validation_rules'], context_name=f"kind-{self.cluster_name}")

        # Calcul du score
        success_count = sum(1 for r in results if r.get('success'))
        total_count = len(results)
        score = int((success_count / total_count) * 100) if total_count > 0 else 0
        is_passed = score == 100

        # Affichage des résultats
        table = Table(title=f"Résultats : {lab_data['title']}")
        table.add_column("Test", style="cyan")
        table.add_column("Résultat", style="bold")
        table.add_column("Message", style="italic")
        for r in results:
            res_str = "[green]OK[/green]" if r.get('success') else "[red]FAIL[/red]"
            table.add_row(r['rule'], res_str, r.get('message', ''))
        console.print(table)

        if is_passed:
            console.print("[bold green]Félicitations ! Vous avez réussi tous les tests. 🚀[/bold green]")
        else:
            console.print(f"[bold yellow]Score : {score}%. Continuez vos efforts ![/bold yellow]")

        # Envoi au serveur
        payload = {
            "username": self.username,
            "lab_id": lab_data['id'],
            "status": is_passed,
            "score": score,
            "details": results
        }

        try:
            httpx.post(self.server_url, json=payload, timeout=5.0)
            console.print("[italic green]Score envoyé au formateur avec succès ![/italic green]")
        except Exception as e:
            console.print(f"[yellow]Attention : Impossible de joindre le serveur formateur à {self.server_url} ({e})[/yellow]")

def main():
    cli = KubeSchoolCLI()
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/bold red]")
        console.print("  python3 kubeschool.py config --user <nom> --server <IP>")
        console.print("  python3 kubeschool.py start <fichier_lab.yaml>")
        console.print("  python3 kubeschool.py check <fichier_lab.yaml>")
        return

    command = sys.argv[1]

    if command == "config":
        parser = argparse.ArgumentParser()
        parser.add_argument("--user", help="Nom du stagiaire")
        parser.add_argument("--server", help="IP du serveur formateur")
        args = parser.parse_args(sys.argv[2:])
        cli.configure(username=args.user, server_ip=args.server)

    elif command == "start":
        if len(sys.argv) < 3:
            console.print("[red]Veuillez spécifier un fichier lab.[/red]")
        else:
            cli.start_lab(sys.argv[2])

    elif command == "check":
        if len(sys.argv) < 3:
            console.print("[red]Veuillez spécifier un fichier lab.[/red]")
        else:
            cli.check_lab(sys.argv[2])
    else:
        console.print(f"[red]Commande inconnue : {command}[/red]")

if __name__ == "__main__":
    main()
