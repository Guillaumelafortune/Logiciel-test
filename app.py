import os
from main2 import app

# Configuration pour la production
if __name__ == "__main__":
    # Récupérer le port depuis les variables d'environnement (Railway, Render, Heroku)
    port = int(os.environ.get('PORT', 8080))
    
    # Déterminer si on est en mode debug
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    
    print(f"🚀 Démarrage de l'application en mode {'DEBUG' if debug else 'PRODUCTION'}")
    print(f"🌐 Port: {port}")
    
    # Démarrer l'application
    app.run(
        debug=debug, 
        host='0.0.0.0', 
        port=port
    )
