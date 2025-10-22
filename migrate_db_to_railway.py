"""
Script de migration automatique de la base de données locale vers Railway
Copie les données de Tailscale (100.73.238.42) vers Railway
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur : {e.stderr}")
        return False

def export_databases():
    """Exporte les 3 bases de données locales"""
    print("\n" + "="*60)
    print("📦 EXPORT DES BASES DE DONNÉES LOCALES")
    print("="*60)
    
    databases = ['simulation', 'economic', 'analysis']
    export_dir = Path('db_exports')
    export_dir.mkdir(exist_ok=True)
    
    print(f"\n📁 Dossier d'export : {export_dir.absolute()}")
    
    success_count = 0
    for db in databases:
        output_file = export_dir / f"{db}.sql"
        command = f'pg_dump -h 100.73.238.42 -U postgres -d {db} --no-owner --no-privileges -f "{output_file}"'
        
        if run_command(command, f"Export de '{db}'"):
            file_size = output_file.stat().st_size / 1024  # KB
            print(f"   📄 Fichier : {output_file.name} ({file_size:.1f} KB)")
            success_count += 1
    
    if success_count == len(databases):
        print(f"\n🎉 Toutes les bases exportées avec succès !")
        return True
    else:
        print(f"\n⚠️ {len(databases) - success_count} base(s) non exportée(s)")
        return False

def import_to_railway(railway_url):
    """Importe les données vers Railway"""
    print("\n" + "="*60)
    print("🚀 IMPORT VERS RAILWAY")
    print("="*60)
    
    export_dir = Path('db_exports')
    databases = ['simulation', 'economic', 'analysis']
    
    success_count = 0
    for db in databases:
        sql_file = export_dir / f"{db}.sql"
        if not sql_file.exists():
            print(f"❌ Fichier {sql_file} introuvable")
            continue
        
        command = f'psql "{railway_url}" < "{sql_file}"'
        
        if run_command(command, f"Import de '{db}'"):
            success_count += 1
    
    if success_count == len(databases):
        print(f"\n🎉 Migration complète réussie !")
        print(f"\n✅ Votre application Railway peut maintenant accéder aux données")
        return True
    else:
        print(f"\n⚠️ {len(databases) - success_count} base(s) non importée(s)")
        return False

def main():
    """Fonction principale"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║     MIGRATION BASE DE DONNÉES - LOCAL → RAILWAY           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    print("Ce script va :")
    print("  1️⃣  Exporter vos 3 bases de données locales (Tailscale)")
    print("  2️⃣  Les importer vers votre base Railway")
    print()
    
    # Vérifier que pg_dump et psql sont installés
    print("🔍 Vérification des outils PostgreSQL...")
    
    try:
        subprocess.run('pg_dump --version', shell=True, capture_output=True, check=True)
        subprocess.run('psql --version', shell=True, capture_output=True, check=True)
        print("✅ PostgreSQL client installé")
    except:
        print("❌ ERREUR : PostgreSQL client non installé")
        print("\n📥 Installation requise :")
        print("   Téléchargez : https://www.postgresql.org/download/windows/")
        print("   Ou installez via : winget install PostgreSQL.PostgreSQL")
        return
    
    # Étape 1 : Export
    print("\n" + "-"*60)
    input("Appuyez sur ENTRÉE pour démarrer l'export...")
    
    if not export_databases():
        print("\n❌ Export échoué. Vérifiez que :")
        print("   - Tailscale est actif")
        print("   - La DB est accessible sur 100.73.238.42")
        print("   - Le mot de passe est correct (4845)")
        return
    
    # Étape 2 : Import
    print("\n" + "-"*60)
    print("\n📝 Configuration Railway")
    print("\nDans Railway, allez dans votre service PostgreSQL et copiez DATABASE_URL")
    print("Format : postgresql://postgres:PASSWORD@HOST:PORT/railway")
    print()
    
    railway_url = input("Collez DATABASE_URL de Railway : ").strip()
    
    if not railway_url:
        print("❌ URL vide. Migration annulée.")
        return
    
    print(f"\n🔗 URL Railway : {railway_url[:30]}...")
    confirm = input("\n✅ Confirmer l'import ? (oui/non) : ").strip().lower()
    
    if confirm not in ['oui', 'yes', 'o', 'y']:
        print("❌ Migration annulée")
        return
    
    if import_to_railway(railway_url):
        print("\n" + "="*60)
        print("🎉 MIGRATION TERMINÉE AVEC SUCCÈS !")
        print("="*60)
        print("\n📊 Prochaines étapes :")
        print("   1. Railway va redéployer automatiquement")
        print("   2. Attendez 2-3 minutes")
        print("   3. Testez votre app : elle aura accès aux immeubles !")
        print(f"\n🌐 URL : https://web-production-fe0aa.up.railway.app")
    else:
        print("\n⚠️ Certaines données n'ont pas été importées")
        print("Consultez les erreurs ci-dessus pour plus de détails")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Migration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue : {e}")
        import traceback
        traceback.print_exc()
    
    input("\n\nAppuyez sur ENTRÉE pour fermer...")

