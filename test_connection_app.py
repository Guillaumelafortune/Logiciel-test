"""
Test si l'app peut se connecter a Railway et charger les immeubles
"""

import sys
sys.path.insert(0, 'filter')
sys.path.insert(0, 'functions')

import os
os.environ['RAILWAY_ENVIRONMENT'] = 'production'
os.environ['DATABASE_URL'] = 'postgresql://postgres:xJEaLcUQRAxBLRpKggzRqStrsuDbRjnX@turntable.proxy.rlwy.net:11722/railway'

from filter.data_loading import load_immeubles

print("\n" + "="*70)
print("  TEST CONNEXION APPLICATION -> RAILWAY")
print("="*70)

try:
    print("\n  [TEST] Chargement des immeubles comme dans l'app...")
    df = load_immeubles()
    
    if df.empty:
        print("\n  [PROBLEME] DataFrame vide!")
        print("  L'application ne trouve pas les immeubles.")
        print("\n  CAUSE POSSIBLE:")
        print("    - La fonction load_immeubles() cherche peut-etre")
        print("      une table avec un nom different")
        print("    - Ou une colonne 'date_scrape' specifique")
    else:
        print(f"\n  [SUCCES] {len(df)} immeubles charges!")
        print("\n  Exemples:")
        for i, row in df.head(3).iterrows():
            print(f"    - {row.get('address', row.get('adresse', 'N/A'))}")
    
except Exception as e:
    print(f"\n  [ERREUR] {e}")
    import traceback
    traceback.print_exc()
    
    print("\n  DIAGNOSTIC:")
    print("    L'application ne peut pas se connecter a Railway")
    print("    ou la structure de la table ne correspond pas.")

print("\n" + "="*70)
print()

