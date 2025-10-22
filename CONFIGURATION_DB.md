# 🗄️ Configuration de la Base de Données

## 📊 **Problème Résolu**

Votre application utilise **3 bases de données PostgreSQL** accessibles localement via Tailscale :
- `simulation` - Données des immeubles et configurations
- `economic` - Données économiques (taux, taxes)
- `analysis` - Données géographiques (provinces, régions, quartiers)

**Solution:** Le code détecte automatiquement l'environnement et utilise les bonnes connexions.

## 🔄 **Comment ça Fonctionne**

### **En Développement (Local)**
- ✅ Utilise automatiquement Tailscale (`100.73.238.42`)
- ✅ Aucune configuration requise
- ✅ Fonctionne comme avant

### **En Production (Railway/Web)**
- ✅ Lit les variables d'environnement
- ✅ Se connecte à la DB cloud
- ✅ Bascule automatique

## 🚀 **Options de Configuration Production**

### **Option 1: Base de Données Railway (Recommandé)**

#### Étape 1: Créer une DB PostgreSQL sur Railway
1. Dans votre projet Railway, cliquer **"+ New Service"**
2. Sélectionner **"Database" → "PostgreSQL"**
3. Railway crée automatiquement la DB

#### Étape 2: Importer vos Données
```bash
# Depuis votre machine locale (avec Tailscale actif)
# Exporter vos données locales
pg_dump -h 100.73.238.42 -U postgres -d simulation > simulation.sql
pg_dump -h 100.73.238.42 -U postgres -d economic > economic.sql
pg_dump -h 100.73.238.42 -U postgres -d analysis > analysis.sql

# Importer vers Railway (remplacer par votre URL Railway)
psql <DATABASE_URL_DE_RAILWAY> < simulation.sql
psql <DATABASE_URL_DE_RAILWAY> < economic.sql
psql <DATABASE_URL_DE_RAILWAY> < analysis.sql
```

#### Étape 3: Configurer Railway
Railway ajoute automatiquement `DATABASE_URL` dans vos variables d'environnement.

**C'est tout !** L'app utilisera automatiquement cette connexion.

---

### **Option 2: Bases Multiples (3 DB séparées)**

Si vous voulez conserver les 3 bases séparées :

1. **Créer 3 services PostgreSQL sur Railway**
2. **Configurer les variables d'environnement :**
   ```
   DATABASE_URL_SIMULATION=postgresql://user:pass@host:port/simulation
   DATABASE_URL_ECONOMIC=postgresql://user:pass@host:port/economic
   DATABASE_URL_ANALYSIS=postgresql://user:pass@host:port/analysis
   ```

Le code détectera automatiquement ces variables.

---

### **Option 3: Exposer votre DB Locale**

⚠️ **Attention : Risque de sécurité**

Si vous voulez garder votre DB locale accessible depuis Internet :

1. **Configurer PostgreSQL pour accepter les connexions externes**
2. **Ouvrir le port 5432 sur votre routeur**
3. **Utiliser un tunnel sécurisé (Tailscale Funnel ou ngrok)**

#### Avec Tailscale Funnel:
```bash
# Sur votre machine avec la DB
tailscale funnel 5432
```

Puis dans Railway, ajouter :
```
DATABASE_URL=postgresql://postgres:4845@<VOTRE_IP_PUBLIQUE>:5432/simulation
```

---

### **Option 4: Tunnel Tailscale sur Railway (Avancé)**

Installer Tailscale dans le conteneur Railway (nécessite Docker personnalisé).

---

## ✅ **Configuration Recommandée**

Pour simplicité et sécurité, utilisez **Option 1** :
- ✅ Une seule DB Railway
- ✅ Importez toutes vos données
- ✅ Gratuit pour commencer
- ✅ Backups automatiques
- ✅ Haute disponibilité

## 🔍 **Variables d'Environnement**

L'application détecte automatiquement l'environnement :

| Variable | Description |
|----------|-------------|
| `RAILWAY_ENVIRONMENT` | Défini automatiquement par Railway |
| `FLASK_ENV=production` | Force le mode production |
| `DATABASE_URL` | URL principale (utilisée pour toutes les DB) |
| `DATABASE_URL_SIMULATION` | URL spécifique (optionnel) |
| `DATABASE_URL_ECONOMIC` | URL spécifique (optionnel) |
| `DATABASE_URL_ANALYSIS` | URL spécifique (optionnel) |

## 🧪 **Test de Connexion**

Pour tester la configuration DB :

```python
python config_db.py
```

Cela affichera la connexion détectée et testera l'accès.

## 📞 **Dépannage**

### Erreur: "No results found" après déploiement
- ✅ Vérifier que `DATABASE_URL` est définie dans Railway
- ✅ Vérifier que les données sont bien importées
- ✅ Consulter les logs Railway pour voir les erreurs de connexion

### Ça fonctionne localement mais pas en production
- ✅ L'app utilise Tailscale en local (normal)
- ✅ En production, elle cherche `DATABASE_URL`
- ✅ Vérifier les variables d'environnement dans Railway

### Erreur de connexion PostgreSQL
- ✅ Vérifier le format de l'URL : `postgresql://` (pas `postgres://`)
- ✅ Le code corrige automatiquement, mais vérifier quand même
