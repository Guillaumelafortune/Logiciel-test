"""
Module pour le chargement des données depuis les bases de données PostgreSQL.
Contient toutes les fonctions de chargement de données extraites de main2.py
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import date
import re
import os


def get_db_connection_string(database_name):
    """
    Retourne la chaîne de connexion à la base de données selon l'environnement.
    
    En production (Railway): Utilise DATABASE_URL_<nom>
    En développement (local): Utilise Tailscale (100.73.238.42)
    
    Args:
        database_name: Nom de la base ('simulation', 'economic', 'analysis')
    
    Returns:
        str: Chaîne de connexion PostgreSQL
    """
    # Vérifier si on est en production (Railway définit RAILWAY_ENVIRONMENT)
    is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('FLASK_ENV') == 'production'
    
    if is_production:
        # En production, chercher une variable d'environnement spécifique
        env_var_name = f"DATABASE_URL_{database_name.upper()}"
        db_url = os.environ.get(env_var_name)
        
        # Fallback: si une seule DATABASE_URL est définie, l'utiliser pour toutes
        if not db_url:
            db_url = os.environ.get('DATABASE_URL')
        
        if db_url:
            # Correction pour certains providers (postgres:// -> postgresql://)
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            return db_url
    
    # Configuration locale par défaut (Tailscale)
    return f"postgresql://postgres:4845@100.73.238.42:5432/{database_name}"


def clean_percentage_value(value):
    """
    Nettoie une valeur de pourcentage (ex: "4.69%" -> 4.69)
    Amélioration pour gérer différents formats de données
    """
    if value is None or value == '':
        return 0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Si c'est une chaîne
    if isinstance(value, str):
        # Enlever le symbole % et les espaces
        cleaned = value.replace('%', '').strip()
        
        # Gérer le cas où on a des virgules comme séparateur décimal
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            # Essayer d'extraire les nombres avec regex
            numbers = re.findall(r'\d+\.?\d*', cleaned)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    return 0
            return 0
    
    return 0


def load_tax_rates_particulier():
    """Charge les taux d'imposition pour les particuliers"""
    engine = create_engine(
        get_db_connection_string('economic'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM "particulier".impot_federal_particulier ORDER BY id'
    tax_df = pd.read_sql(query, engine)
    
    # Vérifier si les taux fédéraux sont présents et à jour
    federal_df = tax_df[tax_df['province'] == 'fédéral']
    if federal_df.empty:
        # Ajouter les taux fédéraux manuellement s'ils ne sont pas présents
        federal_rates = [
            {'id': 1000, 'province': 'fédéral', 'tranche': 'sur la partie de votre revenu imposable qui est de 57 375 $ ou moins, plus', 'taux_marginal': '15 %'},
            {'id': 1001, 'province': 'fédéral', 'tranche': 'sur la partie de votre revenu imposable dépassant 57 375 $ jusqu\'à 114 750 $, plus', 'taux_marginal': '20,5 %'},
            {'id': 1002, 'province': 'fédéral', 'tranche': 'sur la partie de votre revenu imposable dépassant 114 750 $ jusqu\'à 177 882 $, plus', 'taux_marginal': '26 %'},
            {'id': 1003, 'province': 'fédéral', 'tranche': 'sur la partie de votre revenu imposable dépassant 177 882 $ jusqu\'à 253 414 $, plus', 'taux_marginal': '29 %'},
            {'id': 1004, 'province': 'fédéral', 'tranche': 'sur la partie de votre revenu imposable dépassant 253 414 $', 'taux_marginal': '33 %'},
        ]
        federal_df = pd.DataFrame(federal_rates)
        tax_df = pd.concat([tax_df, federal_df], ignore_index=True)
        print("Taux fédéraux ajoutés manuellement car absents de la base de données.")
        
    return tax_df


def load_tax_rates_entreprise():
    """Charge les taux d'imposition pour les entreprises"""
    engine = create_engine(
        get_db_connection_string('economic'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM entreprise.impot_federal_placement ORDER BY id'
    return pd.read_sql(query, engine)


def load_immeubles():
    """Charge les immeubles actifs (données les plus récentes)"""
    try:
        engine = create_engine(
            get_db_connection_string('simulation'),
            connect_args={"client_encoding": "utf8"}
        )
        # Prendre les données les plus récentes
        query = """
        SELECT * FROM immeuble.immeuble_pmml 
        WHERE date_scrape = (SELECT MAX(date_scrape) FROM immeuble.immeuble_pmml)
        """
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Erreur lors du chargement des immeubles: {e}")
        return pd.DataFrame()  # Retourne un DataFrame vide en cas d'erreur


def load_immeubles_history(selected_date: date):
    """Charge les immeubles historiques pour une date donnée"""
    try:
        engine = create_engine(
            get_db_connection_string('simulation'),
            connect_args={"client_encoding": "utf8"}
        )
        date_str = selected_date.strftime('%Y-%m-%d')
        query = f"SELECT * FROM immeuble.immeuble_pmml WHERE date_scrape = '{date_str}'"
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Erreur lors du chargement des immeubles historiques: {e}")
        return pd.DataFrame()  # Retourne un DataFrame vide en cas d'erreur


def load_schl_rates_plex():
    """Charge les taux SCHL pour les plex (5 unités et moins) - Données intégrées"""
    # Données directement intégrées dans le code (source: all.assurance_pret_schl_plex)
    data = {
        'id': [1, 2, 3, 4, 5, 6, 7],
        'rapport_pret_valeur': [
            '65 % ou moins',
            '65,01 à 75 %',
            '75,01 à 80 %',
            '80,01 à 85 %',
            '85,01 à 90 %',
            '90,01 à 95 %',
            '90,01 à 95 % avec une mise de fonds non traditionnelle'
        ],
        'prime_montant_total': [
            '0,60 %',
            '1,70 %',
            '2,40 %',
            '2,80 %',
            '3,10 %',
            '4,00 %',
            '4,50 %'
        ]
    }
    return pd.DataFrame(data)


def load_schl_rates_multi_logement():
    """Charge les taux SCHL pour les multi-logements (6 unités et plus) - Données intégrées"""
    # Données directement intégrées dans le code (source: all.assurance_pret_schl_multi_logement)
    data = {
        'id': [1, 2, 3, 4, 5],
        'rapport_pret_valeur': ['<=65%', '<=70%', '<=75%', '<=80%', '<=85%'],
        'prime_montant_total_egi_met': [2.60, 2.85, 3.35, 4.35, 5.35],
        'prime_montant_total_egi_not_met': [3.25, 3.75, 4.25, 5.00, 6.00]
    }
    return pd.DataFrame(data)


def load_schl_rates():
    """Cette fonction n'est plus utilisée car nous avons load_schl_rates_plex et load_schl_rates_multi_logement"""
    # Rediriger vers load_schl_rates_plex par défaut
    return load_schl_rates_plex()


def load_app_parameters():
    """Charge les paramètres de configuration de l'application depuis la base de données"""
    engine = create_engine(
        get_db_connection_string('simulation'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM configuration.app_parameters'
    params_df = pd.read_sql(query, engine)
    
    # Convertir en dictionnaire pour un accès facile
    params = {}
    for _, row in params_df.iterrows():
        params[row['parameter_name']] = row['parameter_value']
    
    return params


def load_acquisition_costs():
    """Charge les coûts d'acquisition depuis la base de données"""
    engine = create_engine(
        get_db_connection_string('simulation'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM configuration.acquisition_costs'
    costs_df = pd.read_sql(query, engine)
    
    # Convertir en dictionnaire
    costs = {}
    for _, row in costs_df.iterrows():
        costs[row['cost_type']] = {
            'fixed_amount': row['fixed_amount'],
            'percentage': row['percentage_of_price']
        }
    
    return costs


def load_adjustment_defaults():
    """Charge les valeurs d'ajustement par défaut pour les simulations"""
    engine = create_engine(
        get_db_connection_string('simulation'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM configuration.simulation_adjustments'
    adj_df = pd.read_sql(query, engine)
    
    # Convertir en dictionnaire
    adjustments = {}
    for _, row in adj_df.iterrows():
        adjustments[row['adjustment_type']] = row['default_value']
    
    return adjustments


def load_provinces():
    """Charge les provinces du Canada"""
    engine = create_engine(
        get_db_connection_string('analysis'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT province_id, province_name FROM id."Canada_Provinces_ID"'
    return pd.read_sql(query, engine)


def load_regions(province_id=None):
    """Charge les régions du Québec"""
    engine = create_engine(
        get_db_connection_string('analysis'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT region_id, region_nom, province_id FROM id."Province_Quebec_Regions_ID"'
    if province_id:
        query += f' WHERE province_id = {province_id}'
    return pd.read_sql(query, engine)


def load_secteurs(region_id=None):
    """Charge les secteurs d'une région"""
    engine = create_engine(
        get_db_connection_string('analysis'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT secteur_id, secteur_nom, region_id, region_nom FROM id."Province_Quebec_Regions_Secteurs_ID"'
    if region_id:
        query += f' WHERE region_id = {region_id}'
    return pd.read_sql(query, engine)


def load_quartiers(region_id=None):
    """Charge les quartiers d'une région"""
    engine = create_engine(
        get_db_connection_string('analysis'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT quartier_id, quartier_nom_fr, region_id, region_nom FROM id."Province_Quebec_Quartiers_ID"'
    if region_id:
        query += f' WHERE region_id = {region_id}'
    return pd.read_sql(query, engine)


def load_secteurs_recensement(region_id=None):
    """Charge les secteurs de recensement d'une région"""
    engine = create_engine(
        get_db_connection_string('analysis'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT secteur_rec_id, secteur_rec_code, region_id, region_nom FROM id."Province_Quebec_Secteurs_recensement_ID"'
    if region_id:
        query += f' WHERE region_id = {region_id}'
    return pd.read_sql(query, engine)


def load_taxe_bienvenue():
    """Charge les taux de taxe de bienvenue (mutation) depuis la base de données"""
    engine = create_engine(
        get_db_connection_string('economic'),
        connect_args={"client_encoding": "utf8"}
    )
    query = 'SELECT * FROM "all".taxe_bienvenue ORDER BY id'
    return pd.read_sql(query, engine)


def load_taxation_municipale():
    """Charge les taux de taxation municipale depuis la base de données"""
    try:
        engine = create_engine(
            get_db_connection_string('economic'),
            connect_args={"client_encoding": "utf8"}
        )
        query = 'SELECT * FROM "all".taxation_municipale'
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Erreur lors du chargement des taux de taxation municipale: {e}")
        return pd.DataFrame()


def load_taux_hypothecaires():
    """Charge les taux hypothécaires des banques depuis la base de données"""
    try:
        engine = create_engine(
            get_db_connection_string('economic'),
            connect_args={"client_encoding": "utf8"}
        )
        query = '''
            SELECT 
                banque_nom,
                taux_refinancement,
                taux_fixe_5ans,
                taux_variable_5ans,
                scrape_date
            FROM "all".taux_hypothecaires
            WHERE scrape_date = (SELECT MAX(scrape_date) FROM "all".taux_hypothecaires)
            ORDER BY banque_nom
        '''
        df = pd.read_sql(query, engine)
        engine.dispose()
        
        # Nettoyer les taux (utiliser la nouvelle fonction)
        for col in ['taux_refinancement', 'taux_fixe_5ans', 'taux_variable_5ans']:
            df[col] = df[col].apply(lambda x: clean_percentage_value(x) if pd.notna(x) and x != 'N/A' else None)
        
        return df
    except Exception as e:
        print(f"Erreur lors du chargement des taux hypothécaires: {e}")
        return pd.DataFrame()
