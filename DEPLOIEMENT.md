# 🚀 Guide de Déploiement - Application Simulation Immobilière

## 📋 Prérequis
- Compte GitHub (gratuit)
- Compte Railway/Render (gratuit)
- Code source dans un repository Git

## 🎯 Méthode Recommandée : Railway

### Étape 1: Préparer le Code
✅ **FAIT** - Tous les fichiers sont prêts :
- `Procfile` - Configuration du serveur
- `railway.json` - Configuration Railway
- `runtime.txt` - Version Python
- `requirements.txt` - Dépendances
- `main2.py` modifié pour la production

### Étape 2: Créer un Repository GitHub
```bash
# Dans votre dossier d'application
git init
git add .
git commit -m "Initial commit - App Simulation PMML"
git branch -M main
git remote add origin https://github.com/VOTRE_USERNAME/app-simulation-pmml.git
git push -u origin main
```

### Étape 3: Déployer sur Railway

1. **Aller sur Railway** : https://railway.app
2. **Se connecter avec GitHub**
3. **Cliquer sur "New Project"**
4. **Sélectionner "Deploy from GitHub repo"**
5. **Choisir votre repository**
6. **Railway détectera automatiquement que c'est une app Python**

### Étape 4: Configurer la Base de Données

1. **Dans Railway, cliquer sur "+ New Service"**
2. **Sélectionner "Database" → "PostgreSQL"**
3. **Railway créera automatiquement une DB**
4. **Copier l'URL de connexion (DATABASE_URL)**

### Étape 5: Variables d'Environnement

Dans Railway, aller dans **Settings → Environment** et ajouter :
```
DATABASE_URL=postgresql://... (fournie par Railway)
FLASK_ENV=production
PORT=8080
```

## 🌐 Alternative : Render

### Déploiement sur Render
1. **Aller sur Render** : https://render.com
2. **Connecter GitHub**
3. **Créer un "Web Service"**
4. **Configurer :**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main2.py`
   - Environment: Python 3.11

## ⚙️ Configuration de Production

### Variables d'Environnement Nécessaires
```bash
PORT=8080                    # Port du serveur (automatique sur Railway/Render)
FLASK_ENV=production         # Mode production
DATABASE_URL=postgresql://... # URL de la base de données
```

### Optimisations Déjà Appliquées
- ✅ Port dynamique depuis `$PORT`
- ✅ Mode debug désactivé en production
- ✅ Host configuré pour `0.0.0.0`
- ✅ Gestion des erreurs améliorée

## 🔧 Dépannage

### Problèmes Courants
1. **Erreur de dépendances** : Vérifier `requirements.txt`
2. **Erreur de DB** : Vérifier `DATABASE_URL`
3. **Port binding** : Railway/Render gèrent automatiquement

### Logs
- **Railway** : Onglet "Deployments" → Voir les logs
- **Render** : Onglet "Logs"

## 📊 Coûts Estimés

### Railway (Recommandé)
- **Gratuit** : $5 de crédit/mois
- **Pro** : $20/mois pour plus de ressources

### Render
- **Gratuit** : Limitations de CPU/mémoire
- **Starter** : $7/mois

## 🎉 Résultat Final

Après déploiement, votre app sera disponible sur :
- **Railway** : `https://votre-app.up.railway.app`
- **Render** : `https://votre-app.onrender.com`

## 📞 Support

En cas de problème :
1. Vérifier les logs de déploiement
2. Tester localement avec les mêmes variables d'environnement
3. Contacter le support de la plateforme choisie
