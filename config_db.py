"""
Configuration de la base de données pour la production
Ce script aide à configurer la connexion DB selon l'environnement
"""
import os
from sqlalchemy import create_engine

def get_database_url():
    """
    Retourne l'URL de la base de données selon l'environnement
    """
    # En production, Railway/Render fournissent DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Correction pour certains providers qui utilisent postgres:// au lieu de postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    
    # Configuration locale par défaut
    return "postgresql://username:password@localhost:5432/immo_simulation"

def create_db_engine():
    """
    Crée l'engine de base de données avec les bonnes configurations
    """
    database_url = get_database_url()
    
    # Configuration pour la production
    engine_kwargs = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_pre_ping': True,  # Vérification des connexions
        'pool_recycle': 300,    # Recyclage des connexions après 5min
    }
    
    return create_engine(database_url, **engine_kwargs)

if __name__ == "__main__":
    print("🔍 Configuration de la base de données...")
    db_url = get_database_url()
    print(f"📊 URL de la DB: {db_url[:30]}...")
    
    try:
        engine = create_db_engine()
        # Test de connexion
        with engine.connect() as conn:
            print("✅ Connexion à la base de données réussie!")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
