"""
Module d'analyse géographique pour l'application Dash
Corrigé pour fonctionner avec la structure réelle de la base de données
"""

import pandas as pd
import numpy as np
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import binascii
from shapely.geometry import shape, Point
import geopandas as gpd
from shapely import wkb, wkt
from typing import Optional, Dict, Any, Tuple, List
import datetime

# Configuration de la base de données PostgreSQL
DB_CONFIG = {
    "dbname": "analysis",
    "user": "postgres",
    "password": "4845",
    "host": "100.73.238.42"
}

# Schémas de la base de données (alignés avec recherche.py)
SCHEMA_MAPPING = "id"  # Tables de référence et géographiques

# ============================================================================
# GESTION DE LA BASE DE DONNÉES
# ============================================================================

@contextmanager
def get_connection_context():
    """Gestionnaire de contexte pour la connexion à la base de données PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None):
    """
    Exécute une requête SQL et retourne les résultats sous forme d'un DataFrame pandas
    """
    with get_connection_context() as conn:
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {e}"
            print(error_msg)
            return pd.DataFrame()

def execute_query_dict(query, params=None):
    """Exécute une requête et retourne les résultats sous forme de dictionnaire."""
    df = execute_query(query, params)
    return df.to_dict('records') if not df.empty else []

def execute_query_no_cache(query, params=None):
    """
    Alias pour execute_query - exécute une requête SQL sans cache
    """
    return execute_query(query, params)

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES GÉOGRAPHIQUES
# ============================================================================

def create_geodataframe_local(df, geometry_col='geo_zone'):
    """Convertit un DataFrame avec une colonne géométrie en GeoDataFrame."""
    if df.empty or geometry_col not in df.columns:
        return gpd.GeoDataFrame()
    
    try:
        # Essayer directement de créer un GeoDataFrame
        gdf = gpd.GeoDataFrame(df, geometry=geometry_col)
        # Vérifier si la conversion a réussi
        if not df.empty and gdf.geometry.iloc[0] is None:
            raise ValueError("La géométrie doit être convertie")
    except:
        # Convertir manuellement les géométries
        def convert_to_geometry(geo_data):
            if geo_data is None:
                return None
            
            # Si c'est une string
            if isinstance(geo_data, str):
                # Essayer WKT d'abord
                try:
                    return wkt.loads(geo_data)
                except:
                    pass
                
                # Essayer comme données hexadécimales
                try:
                    return wkb.loads(binascii.unhexlify(geo_data))
                except:
                    pass
                
                # Essayer comme JSON
                try:
                    geo_json = json.loads(geo_data)
                    if geo_json.get('type') in ['Polygon', 'MultiPolygon', 'Point', 'LineString']:
                        return shape(geo_json)
                except:
                    pass
            
            # Si c'est des bytes
            elif isinstance(geo_data, bytes):
                try:
                    return wkb.loads(geo_data)
                except:
                    pass
            
            return None
        
        df['geometry'] = df[geometry_col].apply(convert_to_geometry)
        df = df[df['geometry'].notna()]
        
        if not df.empty:
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
        else:
            return gpd.GeoDataFrame()
    
    # Définir le système de coordonnées
    gdf.crs = "EPSG:4326"
    return gdf

def get_quebec_regions_geo():
    """Récupère les données géographiques des régions du Québec"""
    query = f"""
    SELECT region_id, region_nom, geo_zone
    FROM "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID"
    """
    df = execute_query(query)
    if not df.empty:
        gdf = create_geodataframe_local(df, 'geo_zone')
        return gdf
    return gpd.GeoDataFrame()

def get_quebec_sectors_geo():
    """Récupère les données géographiques des secteurs du Québec"""
    query = f"""
    SELECT secteur_id, secteur_nom, region_nom, region_id, geo_zone
    FROM "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID"
    """
    df = execute_query(query)
    if not df.empty:
        gdf = create_geodataframe_local(df, 'geo_zone')
        return gdf
    return gpd.GeoDataFrame()

def get_quebec_quartiers_geo():
    """Récupère les données géographiques des quartiers du Québec"""
    query = f"""
    SELECT quartier_id, quartier_code, quartier_nom_fr, region_id, region_nom, province_id, geo_zone
    FROM "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID"
    """
    df = execute_query(query)
    if not df.empty:
        gdf = create_geodataframe_local(df, 'geo_zone')
        return gdf
    return gpd.GeoDataFrame()

def get_quebec_secteur_recensement_geo():
    """Récupère les données géographiques des secteurs de recensement du Québec"""
    query = f"""
    SELECT id as secteur_rec_id, secteur_code as secteur_rec_code, region_id, region_nom, geo_zone
    FROM "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID"
    """
    df = execute_query(query)
    if not df.empty:
        gdf = create_geodataframe_local(df, 'geo_zone')
        return gdf
    return gpd.GeoDataFrame()

# ============================================================================
# FONCTIONS UTILITAIRES POUR LA BASE DE DONNÉES
# ============================================================================

def list_available_tables():
    """Liste les tables disponibles dans le schéma."""
    try:
        query = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{SCHEMA_MAPPING}'
        ORDER BY table_name
        """
        df = execute_query(query)
        return df['table_name'].tolist() if not df.empty else []
    except Exception as e:
        print(f"Erreur lors de la récupération des tables: {e}")
        return []

def table_exists(table_name):
    """Vérifie si une table existe."""
    try:
        query = f"""
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_schema = '{SCHEMA_MAPPING}' 
        AND table_name = %s
        """
        df = execute_query(query, (table_name,))
        return not df.empty
    except Exception as e:
        print(f"Erreur lors de la vérification de l'existence de la table {table_name}: {e}")
        return False

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - REVENUS
# ============================================================================

def get_revenue_menage_by_province(year_range):
    """Récupère les données de revenu des ménages par province"""
    query = f"""
    SELECT p.province_name, i.annee, i.nombre, r.revenue_du_menage as dimension_value
    FROM "revenue_menage"."canada_provinces_revenue_menage" i
    JOIN "{SCHEMA_MAPPING}"."Canada_Provinces_ID" p ON i.province_id = p.province_id
    LEFT JOIN "{SCHEMA_MAPPING}"."revenue_menage" r ON i.revenue_menage_id = r.id
    WHERE i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY p.province_name, i.annee
    """
    return execute_query(query)

def get_revenue_menage_by_region(year_range):
    """Récupère les données de revenu des ménages par région"""
    query = f"""
    SELECT 
        r.region_id,
        r.region_nom,
        i.annee,
        i.nombre,
        rm.revenue_du_menage as dimension_value,
        rm.id as revenue_menage_id
    FROM 
        "revenue_menage"."province_quebec_regions_revenue_menage" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID" r ON i.region_id = r.region_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."revenue_menage" rm ON i.revenue_menage_id = rm.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        r.region_nom, i.annee
    """
    return execute_query(query)

def get_revenue_menage_by_sector(year_range):
    """Récupère les données de revenu des ménages par secteur"""
    query = f"""
    SELECT 
        s.secteur_id,
        s.secteur_nom,
        s.region_nom,
        i.annee,
        i.nombre,
        rm.revenue_du_menage as dimension_value,
        rm.id as revenue_menage_id
    FROM 
        "revenue_menage"."province_quebec_secteurs_revenue_menage" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID" s ON i.secteur_id = s.secteur_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."revenue_menage" rm ON i.revenue_menage_id = rm.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        s.secteur_nom, i.annee
    """
    return execute_query(query)

def get_revenue_menage_by_quartier(year_range):
    """Récupère les données de revenu des ménages par quartier"""
    query = f"""
    SELECT 
        i.quartier_id,
        i.quartier_code,
        i.region_id,
        q.region_nom,
        q.quartier_nom_fr,
        i.annee,
        i.nombre,
        r.revenue_du_menage as dimension_value
    FROM 
        "revenue_menage"."province_quebec_quartiers_revenue_menage" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID" q ON i.quartier_id = q.quartier_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."revenue_menage" r ON i.revenue_menage_id = r.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        q.quartier_nom_fr, i.annee
    """
    return execute_query(query)

def get_revenue_menage_by_secteur_recensement(year_range):
    """Récupère les données de revenu des ménages par secteur de recensement"""
    query = f"""
    SELECT 
        sr.id as secteur_rec_id,
        sr.secteur_code as secteur_rec_code,
        sr.region_id,
        sr.region_nom,
        i.annee,
        i.nombre,
        r.revenue_du_menage as dimension_value
    FROM 
        "revenue_menage"."province_quebec_secteur_recensement_revenue_menage" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" sr ON i.secteur_rec_id = sr.id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."revenue_menage" r ON i.revenue_menage_id = r.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        sr.secteur_code, i.annee
    """
    return execute_query(query)

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - ÂGE POPULATION
# ============================================================================

def get_age_population_by_province(year_range):
    """Récupère les données d'âge et population par province"""
    query = f"""
    SELECT p.province_name, i.annee, i.nombre, a.age_population as dimension_value
    FROM "age_population"."canada_provinces_age_population" i
    JOIN "{SCHEMA_MAPPING}"."Canada_Provinces_ID" p ON i.province_id = p.province_id
    LEFT JOIN "{SCHEMA_MAPPING}"."age_population" a ON i.age_population_id = a.id
    WHERE i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY p.province_name, i.annee
    """
    return execute_query(query)

def get_age_population_by_region(year_range):
    """Récupère les données d'âge et population par région"""
    query = f"""
    SELECT 
        r.region_id,
        r.region_nom,
        i.annee,
        i.nombre,
        a.age_population as dimension_value
    FROM 
        "age_population"."province_quebec_regions_age_population" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID" r ON i.region_id = r.region_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."age_population" a ON i.age_population_id = a.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        r.region_nom, i.annee
    """
    return execute_query(query)

def get_age_population_by_sector(year_range):
    """Récupère les données d'âge et population par secteur"""
    query = f"""
    SELECT 
        s.secteur_id,
        s.secteur_nom,
        s.region_nom,
        i.annee,
        i.nombre,
        a.age_population as dimension_value
    FROM 
        "age_population"."province_quebec_secteurs_age_population" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID" s ON i.secteur_id = s.secteur_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."age_population" a ON i.age_population_id = a.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        s.secteur_nom, i.annee
    """
    return execute_query(query)

def get_age_population_by_quartier(year_range):
    """Récupère les données d'âge et population par quartier"""
    query = f"""
    SELECT 
        q.quartier_id,
        q.quartier_code,
        q.quartier_nom_fr,
        q.region_nom,
        i.annee,
        i.nombre,
        a.age_population as dimension_value
    FROM 
        "age_population"."province_quebec_quartiers_age_population" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID" q ON i.quartier_id = q.quartier_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."age_population" a ON i.age_population_id = a.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        q.quartier_nom_fr, i.annee
    """
    return execute_query(query)

def get_age_population_by_secteur_recensement(year_range):
    """Récupère les données d'âge et population par secteur de recensement"""
    query = f"""
    SELECT 
        sr.id as secteur_rec_id,
        sr.secteur_code as secteur_rec_code,
        sr.region_nom,
        i.annee,
        i.nombre,
        a.age_population as dimension_value
    FROM 
        "age_population"."province_quebec_secteur_recensement_age_population" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" sr ON i.secteur_rec_id = sr.id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."age_population" a ON i.age_population_id = a.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        sr.secteur_code, i.annee
    """
    return execute_query(query)

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - ÉTAT LOGEMENT
# ============================================================================

def get_etat_logement_by_province(year_range, dimension_id):
    """Récupère les données d'état des logements par province"""
    query = f"""
    SELECT p.province_name, i.annee, i.nombre, e.etat_logement as dimension_value
    FROM "etat_logement"."canada_provinces_etat_logement" i
    JOIN "{SCHEMA_MAPPING}"."Canada_Provinces_ID" p ON i.province_id = p.province_id
    LEFT JOIN "{SCHEMA_MAPPING}"."etat_logement" e ON i.etat_logement_id = e.id
    WHERE i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY p.province_name, i.annee
    """
    return execute_query(query)

def get_etat_logement_by_region(year_range, dimension_id):
    """Récupère les données d'état des logements par région"""
    query = f"""
    SELECT 
        r.region_id,
        r.region_nom,
        i.annee,
        i.nombre,
        e.etat_logement as dimension_value
    FROM 
        "etat_logement"."province_quebec_regions_etat_logement" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID" r ON i.region_id = r.region_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."etat_logement" e ON i.etat_logement_id = e.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        r.region_nom, i.annee
    """
    return execute_query(query)

def get_etat_logement_by_sector(year_range, dimension_id):
    """Récupère les données d'état des logements par secteur"""
    query = f"""
    SELECT 
        s.secteur_id,
        s.secteur_nom,
        s.region_nom,
        i.annee,
        i.nombre,
        e.etat_logement as dimension_value
    FROM 
        "etat_logement"."province_quebec_secteurs_etat_logement" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID" s ON i.secteur_id = s.secteur_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."etat_logement" e ON i.etat_logement_id = e.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        s.secteur_nom, i.annee
    """
    return execute_query(query)

def get_etat_logement_by_quartier(year_range, dimension_id):
    """Récupère les données d'état des logements par quartier"""
    query = f"""
    SELECT 
        q.quartier_id,
        q.quartier_code,
        q.quartier_nom_fr,
        q.region_nom,
        i.annee,
        i.nombre,
        e.etat_logement as dimension_value
    FROM 
        "etat_logement"."province_quebec_quartiers_etat_logement" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID" q ON i.quartier_id = q.quartier_id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."etat_logement" e ON i.etat_logement_id = e.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        q.quartier_nom_fr, i.annee
    """
    return execute_query(query)

def get_etat_logement_by_secteur_recensement(year_range, dimension_id):
    """Récupère les données d'état des logements par secteur de recensement"""
    query = f"""
    SELECT 
        sr.id as secteur_rec_id,
        sr.secteur_code as secteur_rec_code,
        sr.region_nom,
        i.annee,
        i.nombre,
        e.etat_logement as dimension_value
    FROM 
        "etat_logement"."province_quebec_secteurs_recensement_etat_logement" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" sr ON i.secteur_rec_id = sr.id
    LEFT JOIN 
        "{SCHEMA_MAPPING}"."etat_logement" e ON i.etat_logement_id = e.id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        sr.secteur_code, i.annee
    """
    return execute_query(query)

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - WALKSCORE
# ============================================================================

def get_walkscore_by_region(date_range):
    """Récupère les données Walkscore par région"""
    query = f"""
    SELECT 
        region_id,
        region_nom,
        walkscore as walk_score,
        bike_score,
        transit_score,
        date
    FROM 
        "walkscore"."Province_Quebec_Regions_Walkscore"
    WHERE 
        date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
    ORDER BY 
        region_nom, date
    """
    return execute_query(query)

def get_walkscore_by_sector(date_range):
    """Récupère les données Walkscore par secteur"""
    query = f"""
    SELECT 
        secteur_id,
        secteur_nom,
        region_id,
        region_nom,
        walkscore as walk_score,
        bike_score,
        transit_score,
        date
    FROM 
        "walkscore"."Province_Quebec_Regions_Secteurs_Walkscore"
    WHERE 
        date BETWEEN '{date_range[0]}' AND '{date_range[1]}'
    ORDER BY 
        secteur_nom, date
    """
    return execute_query(query)

def get_walkscore_by_recensement(date_range):
    """Récupère les données Walkscore par secteur de recensement"""
    query = f"""
    SELECT 
        w.secteur_rec_code,
        w.region_nom,
        w.date_scrape as date,
        w.walkscore as walk_score,
        w.bike_score,
        w.transit_score
    FROM 
        "walkscore"."Province_Quebec_Secteur_recensement_walkscore" w
    WHERE 
        w.date_scrape BETWEEN '{date_range[0]}' AND '{date_range[1]}'
    ORDER BY 
        w.secteur_rec_code, w.date_scrape
    """
    return execute_query(query)

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - LOYER MOYEN (depuis recherche.py)
# ============================================================================

def get_loyer_moyen_by_province(schema_name, dimension_id, year_range):
    """Récupère les données de loyer moyen par province"""
    table_name = "canada_provinces_loyer_moyen"
    query = f"""
    SELECT 
        p.province_name,
        l.annee,
        l.loyer_moyen
    FROM 
        "{schema_name}"."{table_name}" l
    JOIN 
        "{SCHEMA_MAPPING}"."Canada_Provinces_ID" p ON l.province_id = p.province_id
    WHERE 
        l.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        p.province_name, l.annee
    """
    return execute_query(query)

def get_loyer_moyen_by_region(schema_name, dimension_id, year_range):
    """Récupère les données de loyer moyen par région"""
    table_name = "province_quebec_regions_loyer_moyen"
    query = f"""
    SELECT 
        r.region_nom,
        l.annee,
        l.loyer_moyen
    FROM 
        "{schema_name}"."{table_name}" l
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID" r ON l.region_id = r.region_id
    WHERE 
        l.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        r.region_nom, l.annee
    """
    return execute_query(query)

def get_loyer_moyen_by_sector(schema_name, dimension_id, year_range):
    """Récupère les données de loyer moyen par secteur"""
    table_name = "province_quebec_secteurs_loyer_moyen"
    query = f"""
    SELECT 
        s.secteur_nom,
        s.region_nom,
        l.annee,
        l.loyer_moyen
    FROM 
        "{schema_name}"."{table_name}" l
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID" s ON l.secteur_id = s.secteur_id
    WHERE 
        l.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        s.secteur_nom, l.annee
    """
    return execute_query(query)

def get_loyer_moyen_by_quartier(schema_name, dimension_id, year_range):
    """Récupère les données de loyer moyen par quartier"""
    table_name = "province_quebec_quartiers_loyer_moyen"
    query = f"""
    SELECT 
        q.quartier_nom_fr,
        q.region_nom,
        l.annee,
        l.loyer_moyen
    FROM 
        "{schema_name}"."{table_name}" l
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID" q ON l.quartier_id = q.quartier_id
    WHERE 
        l.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        q.quartier_nom_fr, l.annee
    """
    return execute_query(query)

def get_loyer_moyen_by_secteur_recensement(schema_name, dimension_id, year_range):
    """
    Récupère les loyers moyens par secteur de recensement pour un schéma, une dimension et une plage d'années donnés.
    """
    secteurs_query = f"""
    SELECT COUNT(*) FROM "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID"
    """
    secteurs_count = execute_query_no_cache(secteurs_query)
    if secteurs_count.iloc[0, 0] == 0:
        print("Aucun secteur de recensement trouvé pour la province du Québec")
        return pd.DataFrame()
        
    # Définir le nom de la table
    table_name = 'province_quebec_secteur_recensement_loyer_moyen'
    
    # Vérifier si la table existe
    check_query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = '{schema_name}' 
        AND table_name = '{table_name}'
    )
    """
    table_exists = execute_query_no_cache(check_query)
    if not table_exists.iloc[0, 0]:
        print(f"Table {schema_name}.{table_name} n'existe pas")
        return pd.DataFrame()
        
    # Vérifier s'il y a des données pour la plage d'années spécifiée
    count_query = f"""
    SELECT COUNT(*) as count 
    FROM "{schema_name}"."{table_name}"
    WHERE annee BETWEEN {year_range[0]} AND {year_range[1]}
    """
    count_df = execute_query_no_cache(count_query)
    if count_df.iloc[0, 0] == 0:
        print(f"Aucune donnée trouvée dans {schema_name}.{table_name} pour les années {year_range}")
        return pd.DataFrame()
    
    # Construire la requête en fonction du schéma et de la dimension
    if schema_name == "loyer_moyen_type_logement":
        query = f"""
        WITH dimension_values AS (
            SELECT id, type as dimension_value
            FROM "{SCHEMA_MAPPING}"."type_logement"
        )
        SELECT 
            s.id as secteur_rec_id,
            s.secteur_code as secteur_rec_code,
            i.region_id,
            s.region_nom,
            i.annee,
            i.loyer_moyen,
            COALESCE(d.dimension_value, 'Total') as dimension_value
        FROM 
            "{schema_name}"."{table_name}" i
        JOIN 
            "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
        LEFT JOIN 
            dimension_values d ON i.type_id = d.id
        WHERE 
            i.annee BETWEEN {year_range[0]} AND {year_range[1]}
        ORDER BY 
            s.region_nom, s.secteur_code, i.annee
        """
    elif schema_name == "loyer_moyen_par_taille_logement":
        query = f"""
        WITH dimension_values AS (
            SELECT id, taille_immeuble as dimension_value
            FROM "{SCHEMA_MAPPING}"."taille_immeuble"
        )
        SELECT 
            s.id as secteur_rec_id,
            s.secteur_code as secteur_rec_code,
            i.region_id,
            s.region_nom,
            i.annee,
            i.loyer_moyen,
            COALESCE(d.dimension_value, 'Total') as dimension_value
        FROM 
            "{schema_name}"."{table_name}" i
        JOIN 
            "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
        LEFT JOIN 
            dimension_values d ON i.taille_immeuble_id = d.id
        WHERE 
            i.annee BETWEEN {year_range[0]} AND {year_range[1]}
        ORDER BY 
            s.region_nom, s.secteur_code, i.annee
        """
    elif schema_name == "loyer_moyen_by_annees":
        query = f"""
        WITH dimension_values AS (
            SELECT id, annees_construction as dimension_value
            FROM "{SCHEMA_MAPPING}"."annees_construction"
        )
        SELECT 
            s.id as secteur_rec_id,
            s.secteur_code as secteur_rec_code,
            i.region_id,
            s.region_nom,
            i.annee,
            i.loyer_moyen,
            COALESCE(d.dimension_value, 'Total') as dimension_value
        FROM 
            "{schema_name}"."{table_name}" i
        JOIN 
            "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
        LEFT JOIN 
            dimension_values d ON i.annees_construction_id = d.id
        WHERE 
            i.annee BETWEEN {year_range[0]} AND {year_range[1]}
        ORDER BY 
            s.region_nom, s.secteur_code, i.annee
        """
    else:
        print(f"Schéma inconnu: {schema_name}")
        return pd.DataFrame()
    
    # Exécuter la requête
    df = execute_query(query)
    print(f"Récupération de {len(df)} lignes de données de loyer moyen pour les secteurs de recensement")
    return df

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES - TAUX D'INOCCUPATION
# ============================================================================

def get_inoccupation_rates_by_province(schema_name, dimension_id, year_range):
    """Récupère les taux d'inoccupation par province"""
    table_name = "canada_provinces_innoccupation"
    query = f"""
    SELECT 
        p.province_name,
        i.annee,
        i.taux_innoccupation
    FROM 
        "{schema_name}"."{table_name}" i
    JOIN 
        "{SCHEMA_MAPPING}"."Canada_Provinces_ID" p ON i.province_id = p.province_id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        p.province_name, i.annee
    """
    return execute_query(query)

def get_inoccupation_rates_by_region(schema_name, dimension_id, year_range):
    """Récupère les taux d'inoccupation par région"""
    table_name = "province_quebec_regions_innoccupation"
    query = f"""
    SELECT 
        r.region_nom,
        i.annee,
        i.taux_innoccupation
    FROM 
        "{schema_name}"."{table_name}" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_ID" r ON i.region_id = r.region_id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        r.region_nom, i.annee
    """
    return execute_query(query)

def get_inoccupation_rates_by_sector(schema_name, dimension_id, year_range):
    """Récupère les taux d'inoccupation par secteur"""
    table_name = "province_quebec_secteurs_innoccupation"
    query = f"""
    SELECT 
        s.secteur_nom,
        s.region_nom,
        i.annee,
        i.taux_innoccupation
    FROM 
        "{schema_name}"."{table_name}" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Regions_Secteurs_ID" s ON i.secteur_id = s.secteur_id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        s.secteur_nom, i.annee
    """
    return execute_query(query)

def get_inoccupation_rates_by_quartier(schema_name, dimension_id, year_range):
    """Récupère les taux d'inoccupation par quartier"""
    table_name = "province_quebec_quartiers_innoccupation"
    query = f"""
    SELECT 
        q.quartier_nom_fr,
        q.region_nom,
        i.annee,
        i.taux_innoccupation
    FROM 
        "{schema_name}"."{table_name}" i
    JOIN 
        "{SCHEMA_MAPPING}"."Province_Quebec_Quartiers_ID" q ON i.quartier_id = q.quartier_id
    WHERE 
        i.annee BETWEEN {year_range[0]} AND {year_range[1]}
    ORDER BY 
        q.quartier_nom_fr, i.annee
    """
    return execute_query(query)

def get_quebec_province_id():
    """Récupère l'ID de la province du Québec"""
    query = f"""
    SELECT province_id 
    FROM "{SCHEMA_MAPPING}"."Canada_Provinces_ID" 
    WHERE province_name = 'Quebec' OR province_name = 'Québec'
    """
    results = execute_query(query)
    if results.empty:
        print("Impossible de trouver l'ID de la province du Québec")
        return None
    return results['province_id'].iloc[0]

def get_dimension_table_name(dimension_id):
    """Retourne le nom de la table de dimension pour un ID donné"""
    dimension_tables = {
        'fourchette_prix_id': 'fourchettes_prix',
        'taille_immeuble_id': 'taille_immeuble',
        'type_id': 'type_logement',
        'annees_construction_id': 'annees_construction'
    }
    return dimension_tables.get(dimension_id, SCHEMA_MAPPING)

def get_dimension_column_name(schema_name):
    """Retourne le nom de la colonne de dimension pour un schéma donné"""
    dimension_cols = {
        'innoccupation_par_fourchette_loyer': 'fourchette_prix_id',
        'innoccupation_par_taille_logement': 'taille_immeuble_id',
        'innoccupation_type_logement': 'type_id',
        'innoccupation_by_annees': 'annees_construction_id'
    }
    return dimension_cols.get(schema_name, '')

def get_inoccupation_rates_by_secteur_recensement(schema_name, dimension_id, year_range):
    """
    Récupère les taux d'inoccupation par secteur de recensement pour un schéma, une dimension et une plage d'années donnés.
    """
    quebec_id = get_quebec_province_id()
    if not quebec_id:
        return pd.DataFrame()
        
    secteurs_query = f"""
    SELECT COUNT(*) FROM "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID"
    """
    secteurs_count = execute_query_no_cache(secteurs_query)
    if secteurs_count.iloc[0, 0] == 0:
        print("Aucun secteur de recensement trouvé pour la province du Québec")
        return pd.DataFrame()
        
    table_name = 'province_quebec_secteurs_recensement_innoccupation'
    check_query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = '{schema_name}' 
        AND table_name = '{table_name}'
    )
    """
    table_exists = execute_query_no_cache(check_query)
    if not table_exists.iloc[0, 0]:
        print(f"Table {schema_name}.{table_name} n'existe pas")
        return pd.DataFrame()
    
    count_query = f"""
    SELECT COUNT(*) as count 
    FROM "{schema_name}"."{table_name}"
    WHERE annee BETWEEN {year_range[0]} AND {year_range[1]}
    """
    count_df = execute_query_no_cache(count_query)
    if count_df.iloc[0, 0] == 0:
        print(f"Aucune donnée trouvée dans {schema_name}.{table_name} pour les années {year_range}")
        return pd.DataFrame()
    
    dimension_col = get_dimension_column_name(schema_name)
    if not dimension_col:
        dimension_col = dimension_id
        
    # Déterminer la table et la colonne descriptive de la dimension
    dimension_table = get_dimension_table_name(dimension_id)
    
    # Vérifier si la table de dimension existe
    dimension_table_query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = '{SCHEMA_MAPPING}' 
        AND table_name = '{dimension_table}'
    )
    """
    dimension_table_exists = execute_query_no_cache(dimension_table_query)
    
    # Si la table de dimension n'existe pas, utiliser une requête simplifiée
    if not dimension_table_exists.iloc[0, 0]:
        print(f"Table de dimension {SCHEMA_MAPPING}.{dimension_table} n'existe pas. Requête simplifiée utilisée.")
        query = f"""
        SELECT 
            s.id as secteur_rec_id,
            s.secteur_code as secteur_rec_code,
            s.region_nom,
            i.annee,
            i.taux_innoccupation,
            'Total' as dimension_value
        FROM 
            "{schema_name}"."{table_name}" i
        JOIN 
            "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
        WHERE 
            i.annee BETWEEN {year_range[0]} AND {year_range[1]}
        ORDER BY 
            s.region_nom, s.secteur_code, i.annee
        """
    else:
        # Requête avec jointure à la table de dimension
        if schema_name == "innoccupation_par_fourchette_loyer":
            query = f"""
            WITH dimension_values AS (
                SELECT id, fourchette_prix as dimension_value
                FROM "{SCHEMA_MAPPING}"."fourchettes_prix"
            )
            SELECT 
                s.id as secteur_rec_id,
                s.secteur_code as secteur_rec_code,
                s.region_nom,
                i.annee,
                i.taux_innoccupation,
                COALESCE(d.dimension_value, 'Total') as dimension_value
            FROM 
                "{schema_name}"."{table_name}" i
            JOIN 
                "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
            LEFT JOIN 
                dimension_values d ON i.fourchette_prix_id = d.id
            WHERE 
                i.annee BETWEEN {year_range[0]} AND {year_range[1]}
            ORDER BY 
                s.region_nom, s.secteur_code, i.annee
            """
        elif schema_name == "innoccupation_par_taille_logement":
            query = f"""
            WITH dimension_values AS (
                SELECT id, taille_immeuble as dimension_value
                FROM "{SCHEMA_MAPPING}"."taille_immeuble"
            )
            SELECT 
                s.id as secteur_rec_id,
                s.secteur_code as secteur_rec_code,
                s.region_nom,
                i.annee,
                i.taux_innoccupation,
                COALESCE(d.dimension_value, 'Total') as dimension_value
            FROM 
                "{schema_name}"."{table_name}" i
            JOIN 
                "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
            LEFT JOIN 
                dimension_values d ON i.taille_immeuble_id = d.id
            WHERE 
                i.annee BETWEEN {year_range[0]} AND {year_range[1]}
            ORDER BY 
                s.region_nom, s.secteur_code, i.annee
            """
        elif schema_name == "innoccupation_type_logement":
            query = f"""
            WITH dimension_values AS (
                SELECT id, type as dimension_value
                FROM "{SCHEMA_MAPPING}"."type_logement"
            )
            SELECT 
                s.id as secteur_rec_id,
                s.secteur_code as secteur_rec_code,
                s.region_nom,
                i.annee,
                i.taux_innoccupation,
                COALESCE(d.dimension_value, 'Total') as dimension_value
            FROM 
                "{schema_name}"."{table_name}" i
            JOIN 
                "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
            LEFT JOIN 
                dimension_values d ON i.type_id = d.id
            WHERE 
                i.annee BETWEEN {year_range[0]} AND {year_range[1]}
            ORDER BY 
                s.region_nom, s.secteur_code, i.annee
            """
        elif schema_name == "innoccupation_by_annees":
            query = f"""
            WITH dimension_values AS (
                SELECT id, annees_construction as dimension_value
                FROM "{SCHEMA_MAPPING}"."annees_construction"
            )
            SELECT 
                s.id as secteur_rec_id,
                s.secteur_code as secteur_rec_code,
                s.region_nom,
                i.annee,
                i.taux_innoccupation,
                COALESCE(d.dimension_value, 'Total') as dimension_value
            FROM 
                "{schema_name}"."{table_name}" i
            JOIN 
                "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
            LEFT JOIN 
                dimension_values d ON i.annees_construction_id = d.id
            WHERE 
                i.annee BETWEEN {year_range[0]} AND {year_range[1]}
            ORDER BY 
                s.region_nom, s.secteur_code, i.annee
            """
        else:
            print(f"Schéma {schema_name} non supporté pour les secteurs de recensement")
            query = f"""
            SELECT 
                s.id as secteur_rec_id,
                s.secteur_code as secteur_rec_code,
                s.region_nom,
                i.annee,
                i.taux_innoccupation,
                'Total' as dimension_value
            FROM 
                "{schema_name}"."{table_name}" i
            JOIN 
                "{SCHEMA_MAPPING}"."Province_Quebec_Secteurs_recensement_ID" s ON i.secteur_rec_id = s.id
            WHERE 
                i.annee BETWEEN {year_range[0]} AND {year_range[1]}
            ORDER BY 
                s.region_nom, s.secteur_code, i.annee
            """
    
    # Exécuter la requête
    df = execute_query(query)
    print(f"Récupération de {len(df)} lignes de données d'inoccupation pour les secteurs de recensement")
    return df

# ============================================================================
# FONCTIONS DE RÉCUPÉRATION DES DONNÉES STATISTIQUES COMPLÈTES
# ============================================================================

def get_zone_basic_info(zone_id, zone_name, geo_level):
    """
    Récupère les informations de base pour une zone géographique.
    Version simplifiée qui fonctionne avec la structure réelle de la base.
    """
    info = {
        'zone_id': zone_id,
        'zone_name': zone_name,
        'geo_level': geo_level,
        'has_data': True,
        'available_tables': list_available_tables()
    }
    
    return info

# ============================================================================
# FONCTION PRINCIPALE DE RECHERCHE PAR COORDONNÉES
# ============================================================================

def find_zone_for_coordinates(lat, lng, geo_level='Secteur de recensement'):
    """
    Trouve la zone géographique correspondant aux coordonnées données.
    
    Args:
        lat: Latitude
        lng: Longitude
        geo_level: Niveau géographique recherché
        
    Returns:
        Tuple (zone_id, zone_name) ou (None, None) si non trouvé
    """
    point = Point(lng, lat)  # GeoJSON utilise (longitude, latitude)
    
    # Cas spécial pour la province
    if geo_level == 'Province':
        return ('QC', 'Quebec')
    
    # Charger les données géographiques selon le niveau
    if geo_level == 'Région du Québec':
        gdf = get_quebec_regions_geo()
        if gdf.empty:
            return None, None
        
        # Identifier les colonnes disponibles
        id_col = 'region_id' if 'region_id' in gdf.columns else gdf.columns[0] if len(gdf.columns) > 0 else None
        name_col = 'region_name' if 'region_name' in gdf.columns else 'region_nom' if 'region_nom' in gdf.columns else gdf.columns[1] if len(gdf.columns) > 1 else id_col
        
    elif geo_level == 'Secteur du Québec':
        gdf = get_quebec_sectors_geo()
        if gdf.empty:
            return None, None
        
        id_col = 'secteur_id' if 'secteur_id' in gdf.columns else gdf.columns[0] if len(gdf.columns) > 0 else None
        name_col = 'secteur_name' if 'secteur_name' in gdf.columns else 'secteur_nom' if 'secteur_nom' in gdf.columns else gdf.columns[1] if len(gdf.columns) > 1 else id_col
        
    elif geo_level == 'Quartier du Québec':
        gdf = get_quebec_quartiers_geo()
        if gdf.empty:
            return None, None
        
        id_col = 'quartier_id' if 'quartier_id' in gdf.columns else gdf.columns[0] if len(gdf.columns) > 0 else None
        name_col = 'quartier_name' if 'quartier_name' in gdf.columns else 'quartier_nom_fr' if 'quartier_nom_fr' in gdf.columns else gdf.columns[1] if len(gdf.columns) > 1 else id_col
        
    else:  # Secteur de recensement
        # Pour les secteurs de recensement, on doit d'abord identifier la région
        region_result = find_zone_for_coordinates(lat, lng, 'Région du Québec')
        if not region_result or region_result[0] is None:
            # Si on ne trouve pas la région, essayer quand même
            gdf = get_quebec_secteur_recensement_geo()
        else:
            region_id, region_name = region_result
            gdf = get_quebec_secteur_recensement_geo()
            
            # Filtrer pour ne garder que les secteurs de la région identifiée
            if not gdf.empty and 'region_nom' in gdf.columns:
                gdf = gdf[gdf['region_nom'] == region_name]
            elif not gdf.empty and 'region_id' in gdf.columns:
                try:
                    gdf = gdf[gdf['region_id'] == int(region_id)]
                except:
                    pass
        
        if gdf.empty:
            return None, None
        
        id_col = 'secteur_recensement_id' if 'secteur_recensement_id' in gdf.columns else 'id' if 'id' in gdf.columns else gdf.columns[0] if len(gdf.columns) > 0 else None
        name_col = 'secteur_recensement_name' if 'secteur_recensement_name' in gdf.columns else 'secteur_code' if 'secteur_code' in gdf.columns else gdf.columns[1] if len(gdf.columns) > 1 else id_col
    
    if not id_col:
        return None, None
    
    # Vérifier dans quelle zone se trouve le point
    for idx, row in gdf.iterrows():
        try:
            # Vérifier que la géométrie existe et est valide
            if row.geometry is None:
                continue
            
            if not row.geometry.is_valid:
                # Essayer de réparer la géométrie
                try:
                    row.geometry = row.geometry.buffer(0)
                except:
                    continue
            
            if row.geometry.contains(point):
                try:
                    zone_id = str(row.get(id_col, idx))
                    zone_name = str(row.get(name_col, f"Zone {idx}"))
                    
                    # Pour les secteurs de recensement, ajouter l'information sur la région
                    if geo_level == 'Secteur de recensement' and 'region_nom' in row:
                        return (zone_id, f"{zone_name} ({row['region_nom']})")
                    else:
                        return (zone_id, zone_name)
                except Exception as e:
                    print(f"Erreur lors de l'extraction des données: {e}")
                    return (str(idx), f"Zone {idx}")
        except Exception as e:
            print(f"Erreur lors du test de contenance: {e}")
            continue
    
    return None, None

# ============================================================================
# FONCTION PRINCIPALE - get_all_info_for_zone CORRIGÉE
# ============================================================================

def get_all_info_for_zone(zone_id, zone_name, geo_level):
    """
    Récupère toutes les informations disponibles pour une zone spécifique.
    
    Args:
        zone_id: Identifiant de la zone
        zone_name: Nom de la zone
        geo_level: Niveau géographique
        
    Returns:
        Dictionnaire contenant toutes les informations disponibles
    """
    current_year = datetime.datetime.now().year
    info = {
        'id': zone_id,
        'nom': zone_name,
        'niveau': geo_level
    }
    
    # Déterminer la colonne géographique attendue
    if geo_level == 'Province':
        expected_geo_col = 'province_name'
        alt_geo_cols = ['province_nom', 'nom_province', 'nom']
    elif geo_level == 'Région du Québec':
        expected_geo_col = 'region_nom'
        alt_geo_cols = ['nom_region', 'region_name', 'nom']
    elif geo_level == 'Secteur du Québec':
        expected_geo_col = 'secteur_nom'
        alt_geo_cols = ['nom_secteur', 'secteur_name', 'nom']
    elif geo_level == 'Quartier du Québec':
        expected_geo_col = 'quartier_nom_fr'
        alt_geo_cols = ['quartier_nom', 'nom_quartier', 'quartier_name', 'nom']
    else:
        expected_geo_col = 'secteur_rec_code'
        alt_geo_cols = ['secteur_rec_nom', 'code_secteur_rec', 'nom_secteur_rec', 'nom']
    
    def find_geo_column(df):
        """Trouve la colonne géographique appropriée dans le DataFrame"""
        if expected_geo_col in df.columns:
            return expected_geo_col
        for col in alt_geo_cols:
            if col in df.columns:
                return col
        # Si aucune correspondance n'est trouvée, retourner la première colonne comme fallback
        if len(df.columns) > 0:
            print(f"Colonne géographique non trouvée. Colonnes disponibles: {df.columns.tolist()}. Utilisation de {df.columns[0]} comme fallback.")
            return df.columns[0]
        return None
    
    def filter_by_zone(df, zone_value):
        """Filtre le DataFrame pour ne garder que les lignes correspondant à la zone spécifiée"""
        geo_col = find_geo_column(df)
        if not geo_col:
            print(f"Aucune colonne géographique trouvée")
            return pd.DataFrame()
        
        # Cas spécial pour les secteurs de recensement avec le format "code (région)"
        if geo_level == 'Secteur de recensement' and '(' in zone_value and ')' in zone_value:
            try:
                # Extraire le code du secteur et le nom de la région
                code_part = zone_value.split('(')[0].strip()
                region_part = zone_value.split('(')[1].split(')')[0].strip()
                
                # Chercher d'abord par code de secteur
                filtered = df[df[geo_col] == code_part]
                
                # Puis filtrer par région
                if 'region_nom' in df.columns and not filtered.empty:
                    filtered = filtered[filtered['region_nom'] == region_part]
                
                if not filtered.empty:
                    return filtered
            except Exception as e:
                print(f"Erreur lors du filtrage par secteur: {e}")
                # Continuer avec la méthode standard en cas d'erreur
                pass
        
        # Essai avec différentes versions du nom (avec/sans accent, majuscules/minuscules)
        zone_variants = [
            zone_value,
            zone_value.lower(),
            zone_value.upper(),
            zone_value.replace('é', 'e').replace('è', 'e').replace('ê', 'e').replace('ë', 'e')
                       .replace('à', 'a').replace('â', 'a').replace('ä', 'a')
                       .replace('ù', 'u').replace('û', 'u').replace('ü', 'u')
                       .replace('î', 'i').replace('ï', 'i')
                       .replace('ô', 'o').replace('ö', 'o'),
            zone_value.replace('e', 'é').replace('e', 'è').replace('e', 'ê')
                       .replace('a', 'à').replace('a', 'â')
                       .replace('u', 'ù').replace('u', 'û')
                       .replace('i', 'î')
                       .replace('o', 'ô')
        ]
        
        # Si la zone est "Quebec", ajouter "Québec" aux variantes
        if zone_value == "Quebec":
            zone_variants.append("Québec")
        elif zone_value == "Québec":
            zone_variants.append("Quebec")
        
        filtered = pd.DataFrame()
        
        # Essayer chaque variante
        for variant in zone_variants:
            # Correspondance exacte
            exact_match = df[df[geo_col] == variant]
            if not exact_match.empty:
                filtered = pd.concat([filtered, exact_match])
                break
                
            # Correspondance par contenance (variante dans valeur ou valeur dans variante)
            partial_matches = pd.DataFrame()
            for idx, val in df[geo_col].items():
                if isinstance(val, str) and (variant.lower() in val.lower() or val.lower() in variant.lower()):
                    partial_matches = pd.concat([partial_matches, df.loc[[idx]]])
            
            if not partial_matches.empty:
                filtered = pd.concat([filtered, partial_matches])
                break
        
        # Si aucune correspondance avec les variantes, tenter une correspondance insensible à la casse
        if filtered.empty:
            for idx, val in df[geo_col].items():
                if isinstance(val, str) and val.lower() == zone_value.lower():
                    filtered = pd.concat([filtered, df.loc[[idx]]])
        
        # Si toujours aucune correspondance, chercher avec une correspondance approximative (sous-chaîne)
        if filtered.empty:
            for idx, val in df[geo_col].items():
                if isinstance(val, str) and (zone_value.lower() in val.lower()):
                    filtered = pd.concat([filtered, df.loc[[idx]]])
        
        # Si toujours rien, essayer avec juste les 5 premiers caractères
        if filtered.empty and len(zone_value) > 5:
            prefix = zone_value[:5].lower()
            for idx, val in df[geo_col].items():
                if isinstance(val, str) and val.lower().startswith(prefix):
                    filtered = pd.concat([filtered, df.loc[[idx]]])
        
        # Résultat final
        return filtered
    
    # Récupérer les données de revenu
    year_range = (2010, current_year)
    if geo_level == 'Province':
        rev_df = get_revenue_menage_by_province(year_range)
    elif geo_level == 'Région du Québec':
        rev_df = get_revenue_menage_by_region(year_range)
    elif geo_level == 'Secteur du Québec':
        rev_df = get_revenue_menage_by_sector(year_range)
    elif geo_level == 'Quartier du Québec':
        rev_df = get_revenue_menage_by_quartier(year_range)
    else:
        rev_df = get_revenue_menage_by_secteur_recensement(year_range)
    
    if not rev_df.empty:
        # Filtrer pour la zone spécifique
        zone_df = filter_by_zone(rev_df, zone_name)
        if not zone_df.empty:
            info['revenu'] = zone_df.to_dict('records')
    
    # Récupérer les données d'âge
    if geo_level == 'Province':
        age_df = get_age_population_by_province(year_range)
    elif geo_level == 'Région du Québec':
        age_df = get_age_population_by_region(year_range)
    elif geo_level == 'Secteur du Québec':
        age_df = get_age_population_by_sector(year_range)
    elif geo_level == 'Quartier du Québec':
        age_df = get_age_population_by_quartier(year_range)
    else:
        age_df = get_age_population_by_secteur_recensement(year_range)
    
    if not age_df.empty:
        zone_df = filter_by_zone(age_df, zone_name)
        if not zone_df.empty:
            info['age'] = zone_df.to_dict('records')
    
    # Récupérer les données de logement
    if geo_level == 'Province':
        housing_df = get_etat_logement_by_province(year_range, None)
    elif geo_level == 'Région du Québec':
        housing_df = get_etat_logement_by_region(year_range, None)
    elif geo_level == 'Secteur du Québec':
        housing_df = get_etat_logement_by_sector(year_range, None)
    elif geo_level == 'Quartier du Québec':
        housing_df = get_etat_logement_by_quartier(year_range, None)
    else:
        housing_df = get_etat_logement_by_secteur_recensement(year_range, None)
    
    if not housing_df.empty:
        zone_df = filter_by_zone(housing_df, zone_name)
        if not zone_df.empty:
            info['logement'] = zone_df.to_dict('records')
    
    # Récupérer les données Walkscore
    if geo_level != 'Province' and geo_level != 'Quartier du Québec':
        start_date = datetime.date(current_year-5, 1, 1)
        end_date = datetime.date(current_year, 12, 31)
        date_range = (start_date, end_date)
        
        if geo_level == 'Région du Québec':
            walkscore_df = get_walkscore_by_region(date_range)
        elif geo_level == 'Secteur du Québec':
            walkscore_df = get_walkscore_by_sector(date_range)
        else:
            walkscore_df = get_walkscore_by_recensement(date_range)
        
        if not walkscore_df.empty:
            zone_df = filter_by_zone(walkscore_df, zone_name)
            if not zone_df.empty:
                info['walkscore'] = zone_df.to_dict('records')
    
    # Récupérer les données de loyer moyen
    try:
        # Définir les schémas pour loyer moyen
        loyer_schemas = ["loyer_moyen_by_annees", "loyer_moyen_par_taille_logement", "loyer_moyen_type_logement"]
        
        for schema_name in loyer_schemas:
            # Utiliser 1 comme identifiant de dimension par défaut
            dimension_id = 1
            
            print(f"Récupération données loyer: {schema_name}, {geo_level}")
            
            if geo_level == 'Province':
                loyer_df = get_loyer_moyen_by_province(schema_name, dimension_id, year_range)
            elif geo_level == 'Région du Québec':
                loyer_df = get_loyer_moyen_by_region(schema_name, dimension_id, year_range)
            elif geo_level == 'Secteur du Québec':
                loyer_df = get_loyer_moyen_by_sector(schema_name, dimension_id, year_range)
            elif geo_level == 'Quartier du Québec':
                loyer_df = get_loyer_moyen_by_quartier(schema_name, dimension_id, year_range)
            else:
                loyer_df = get_loyer_moyen_by_secteur_recensement(schema_name, dimension_id, year_range)
            
            print(f"Données récupérées: {len(loyer_df)} lignes")
            
            schema_key = schema_name.replace("loyer_moyen_", "loyer_")
            
            if not loyer_df.empty:
                print(f"Filtrage par zone: {zone_name}")
                zone_df = filter_by_zone(loyer_df, zone_name)
                print(f"Données filtrées: {len(zone_df)} lignes")
                if not zone_df.empty:
                    info[schema_key] = zone_df.to_dict('records')
                else:
                    info[f"{schema_key}_message"] = f"Aucune donnée disponible pour le secteur {zone_name} - {schema_name.replace('_', ' ')}"
                    print(f"Aucune donnée après filtrage pour {schema_name} - zone: {zone_name}")
            else:
                info[f"{schema_key}_message"] = f"Aucune donnée disponible dans la base pour {schema_name.replace('_', ' ')}"
                print(f"Aucune donnée trouvée pour {schema_name}")
    except Exception as e:
        print(f"Erreur lors de la récupération des données de loyer moyen: {e}")
    
    # Récupérer les données d'innoccupation
    try:
        # Définir les schémas pour l'innoccupation
        innoc_schemas = ["innoccupation_by_annees", "innoccupation_par_taille_logement", 
                         "innoccupation_type_logement", "innoccupation_par_fourchette_loyer"]
        
        for schema_name in innoc_schemas:
            # Utiliser le nom du schéma comme identifiant de dimension au lieu d'une valeur fixe
            if schema_name == "innoccupation_by_annees":
                dimension_id = "annees_construction_id"
            elif schema_name == "innoccupation_par_taille_logement":
                dimension_id = "taille_immeuble_id"
            elif schema_name == "innoccupation_type_logement":
                dimension_id = "type_id"
            elif schema_name == "innoccupation_par_fourchette_loyer":
                dimension_id = "fourchette_prix_id"
            else:
                dimension_id = "1"  # Fallback au cas où
            
            print(f"Récupération données inoccupation: {schema_name}, {geo_level}")
            
            if geo_level == 'Province':
                innoc_df = get_inoccupation_rates_by_province(schema_name, dimension_id, year_range)
            elif geo_level == 'Région du Québec':
                innoc_df = get_inoccupation_rates_by_region(schema_name, dimension_id, year_range)
            elif geo_level == 'Secteur du Québec':
                innoc_df = get_inoccupation_rates_by_sector(schema_name, dimension_id, year_range)
            elif geo_level == 'Quartier du Québec':
                innoc_df = get_inoccupation_rates_by_quartier(schema_name, dimension_id, year_range)
            else:
                innoc_df = get_inoccupation_rates_by_secteur_recensement(schema_name, dimension_id, year_range)
            
            print(f"Données récupérées: {len(innoc_df)} lignes")
            
            # Ne pas modifier le préfixe innoccupation_
            schema_key = schema_name
            
            if not innoc_df.empty:
                print(f"Filtrage par zone: {zone_name}")
                zone_df = filter_by_zone(innoc_df, zone_name)
                print(f"Données filtrées: {len(zone_df)} lignes")
                if not zone_df.empty:
                    info[schema_key] = zone_df.to_dict('records')
                else:
                    info[f"{schema_key}_message"] = f"Aucune donnée disponible pour le secteur {zone_name} - {schema_name.replace('_', ' ')}"
                    print(f"Aucune donnée d'inoccupation après filtrage pour {schema_name} - zone: {zone_name}")
            else:
                info[f"{schema_key}_message"] = f"Aucune donnée disponible dans la base pour {schema_name.replace('_', ' ')}"
                print(f"Aucune donnée d'inoccupation trouvée pour {schema_name}")
    except Exception as e:
        print(f"Erreur lors de la récupération des données d'innoccupation: {e}")
    
    # Retourner les infos
    return info

# ============================================================================
# CRÉATION DES COMPOSANTS DASH
# ============================================================================

def create_geo_analysis_tab(property_data):
    """
    Crée l'onglet d'analyse géographique pour l'application Dash.
    
    Args:
        property_data: Données de la propriété incluant latitude et longitude
        
    Returns:
        Composant Dash pour l'onglet
    """
    if not property_data:
        return html.Div([
            dbc.Alert("Aucune propriété sélectionnée", color="warning")
        ])
    
    # Extraire les coordonnées
    latitude = property_data.get('latitude')
    longitude = property_data.get('longitude')
    
    if not latitude or not longitude:
        return html.Div([
            dbc.Alert("Les coordonnées de la propriété ne sont pas disponibles", color="warning")
        ])
    
    # Trouver les zones pour chaque niveau géographique
    zones_info = {}
    geo_levels = ['Région du Québec', 'Secteur du Québec', 'Quartier du Québec', 'Secteur de recensement']
    
    # Version robuste qui gère les erreurs
    for level in geo_levels:
        try:
            zone_id, zone_name = find_zone_for_coordinates(latitude, longitude, level)
            if zone_id and zone_name:
                zones_info[level] = get_all_info_for_zone(zone_id, zone_name, level)
        except Exception as e:
            print(f"Erreur pour le niveau {level}: {e}")
            # Créer une entrée avec des informations de base
            zones_info[level] = {
                'zone_id': 'N/A',
                'zone_name': f'Données non disponibles pour {level}',
                'geo_level': level,
                'has_data': False,
                'error': str(e)
            }
    
    # Si aucune zone n'a été trouvée, créer une version de base
    if not zones_info:
        zones_info['Coordonnées'] = {
            'zone_id': 'GPS',
            'zone_name': f"Localisation GPS",
            'geo_level': 'Coordonnées',
            'has_data': True,
            'available_tables': list_available_tables()
        }
    
    # Créer les onglets pour chaque niveau géographique
    tabs_content = []
    
    for level, zone_info in zones_info.items():
        tab_content = create_zone_info_content(zone_info)
        tabs_content.append(
            dbc.Tab(tab_content, label=level, tab_id=f"tab-{level.replace(' ', '-').lower()}")
        )
    
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.H4("Analyse de la Zone Géographique", className="mb-0"),
                html.Small(f"Coordonnées: {latitude:.6f}, {longitude:.6f}", className="text-muted")
            ]),
            dbc.CardBody([
                # Carte de localisation
                create_location_map(latitude, longitude, zones_info),
                
                html.Hr(),
                
                # Onglets pour les différents niveaux géographiques
                dbc.Tabs(tabs_content, id="geo-analysis-tabs", active_tab=tabs_content[0].tab_id if tabs_content else "")
            ])
        ])
    ])

def create_zone_info_content(zone_info):
    """
    Crée le contenu pour afficher les informations d'une zone.
    Affiche toutes les données disponibles comme dans recherche.py.
    
    Args:
        zone_info: Dictionnaire avec les informations de la zone
        
    Returns:
        Composant Dash avec les informations formatées
    """
    content = []
    
    # Titre de la zone
    zone_name = zone_info.get('nom', zone_info.get('zone_name', 'Zone inconnue'))
    content.append(html.H5(f"📍 {zone_name}", className="mb-3"))
    
    # Informations de base
    content.append(
        dbc.Card([
            dbc.CardHeader("Informations de la Zone"),
            dbc.CardBody([
                html.P([
                    html.Strong("ID de la zone: "), 
                    str(zone_info.get('id', zone_info.get('zone_id', 'N/A')))
                ]),
                html.P([
                    html.Strong("Niveau géographique: "), 
                    zone_info.get('niveau', zone_info.get('geo_level', 'N/A'))
                ])
            ])
        ], className="mb-3")
    )
    
    # Revenu des ménages
    if 'revenu' in zone_info:
        df_revenu = pd.DataFrame(zone_info['revenu'])
        if not df_revenu.empty:
            content.append(
                dbc.Card([
                    dbc.CardHeader("💰 Revenu des ménages"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=df_revenu.to_dict('records'),
                            columns=[{"name": i, "id": i} for i in df_revenu.columns],
                            style_cell={'textAlign': 'left'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)'
                                }
                            ],
                            page_size=10
                        )
                    ])
                ], className="mb-3")
            )
    
    # Population par âge
    if 'age' in zone_info:
        df_age = pd.DataFrame(zone_info['age'])
        if not df_age.empty:
            content.append(
                dbc.Card([
                    dbc.CardHeader("👥 Population par âge"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=df_age.to_dict('records'),
                            columns=[{"name": i, "id": i} for i in df_age.columns],
                            style_cell={'textAlign': 'left'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)'
                                }
                            ],
                            page_size=10
                        )
                    ])
                ], className="mb-3")
            )
    
    # État des logements
    if 'logement' in zone_info:
        df_logement = pd.DataFrame(zone_info['logement'])
        if not df_logement.empty:
            content.append(
                dbc.Card([
                    dbc.CardHeader("🏠 État des logements"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=df_logement.to_dict('records'),
                            columns=[{"name": i, "id": i} for i in df_logement.columns],
                            style_cell={'textAlign': 'left'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)'
                                }
                            ],
                            page_size=10
                        )
                    ])
                ], className="mb-3")
            )
    
    # Walkscore
    if 'walkscore' in zone_info:
        df_walkscore = pd.DataFrame(zone_info['walkscore'])
        if not df_walkscore.empty:
            content.append(
                dbc.Card([
                    dbc.CardHeader("🚶 Walkscore"),
                    dbc.CardBody([
                        dash_table.DataTable(
                            data=df_walkscore.to_dict('records'),
                            columns=[{"name": i, "id": i} for i in df_walkscore.columns],
                            style_cell={'textAlign': 'left'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)'
                                }
                            ],
                            page_size=10
                        )
                    ])
                ], className="mb-3")
            )
    
    # Loyers moyens
    loyer_tabs_content = []
    loyer_tabs_labels = []
    
    # Par année de construction
    if 'loyer_by_annees' in zone_info:
        df_loyer_annees = pd.DataFrame(zone_info['loyer_by_annees'])
        if not df_loyer_annees.empty:
            loyer_tabs_content.append(
                dash_table.DataTable(
                    data=df_loyer_annees.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_loyer_annees.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            loyer_tabs_labels.append("Par année")
    elif 'loyer_by_annees_message' in zone_info:
        loyer_tabs_content.append(
            dbc.Alert(zone_info['loyer_by_annees_message'], color="warning")
        )
        loyer_tabs_labels.append("Par année")
    
    # Par taille de logement
    if 'loyer_par_taille_logement' in zone_info:
        df_loyer_taille = pd.DataFrame(zone_info['loyer_par_taille_logement'])
        if not df_loyer_taille.empty:
            loyer_tabs_content.append(
                dash_table.DataTable(
                    data=df_loyer_taille.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_loyer_taille.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            loyer_tabs_labels.append("Par taille")
    elif 'loyer_par_taille_logement_message' in zone_info:
        loyer_tabs_content.append(
            dbc.Alert(zone_info['loyer_par_taille_logement_message'], color="warning")
        )
        loyer_tabs_labels.append("Par taille")
    
    # Par type de logement
    if 'loyer_type_logement' in zone_info:
        df_loyer_type = pd.DataFrame(zone_info['loyer_type_logement'])
        if not df_loyer_type.empty:
            loyer_tabs_content.append(
                dash_table.DataTable(
                    data=df_loyer_type.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_loyer_type.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            loyer_tabs_labels.append("Par type")
    elif 'loyer_type_logement_message' in zone_info:
        loyer_tabs_content.append(
            dbc.Alert(zone_info['loyer_type_logement_message'], color="warning")
        )
        loyer_tabs_labels.append("Par type")
    
    # Afficher les loyers moyens si on a des données
    if loyer_tabs_content:
        tabs = []
        for i, (content_item, label) in enumerate(zip(loyer_tabs_content, loyer_tabs_labels)):
            tabs.append(
                dbc.Tab(content_item, label=label, tab_id=f"loyer-tab-{i}")
            )
        
        content.append(
            dbc.Card([
                dbc.CardHeader("💵 Loyers moyens"),
                dbc.CardBody([
                    dbc.Tabs(tabs, id="loyer-tabs", active_tab="loyer-tab-0" if tabs else None)
                ])
            ], className="mb-3")
        )
    
    # Taux d'inoccupation
    innoc_tabs_content = []
    innoc_tabs_labels = []
    
    # Par année de construction
    if 'innoccupation_by_annees' in zone_info:
        df_innoc_annees = pd.DataFrame(zone_info['innoccupation_by_annees'])
        if not df_innoc_annees.empty:
            innoc_tabs_content.append(
                dash_table.DataTable(
                    data=df_innoc_annees.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_innoc_annees.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            innoc_tabs_labels.append("Par année")
    elif 'innoccupation_by_annees_message' in zone_info:
        innoc_tabs_content.append(
            dbc.Alert(zone_info['innoccupation_by_annees_message'], color="warning")
        )
        innoc_tabs_labels.append("Par année")
    
    # Par taille de logement
    if 'innoccupation_par_taille_logement' in zone_info:
        df_innoc_taille = pd.DataFrame(zone_info['innoccupation_par_taille_logement'])
        if not df_innoc_taille.empty:
            innoc_tabs_content.append(
                dash_table.DataTable(
                    data=df_innoc_taille.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_innoc_taille.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            innoc_tabs_labels.append("Par taille")
    elif 'innoccupation_par_taille_logement_message' in zone_info:
        innoc_tabs_content.append(
            dbc.Alert(zone_info['innoccupation_par_taille_logement_message'], color="warning")
        )
        innoc_tabs_labels.append("Par taille")
    
    # Par type de logement
    if 'innoccupation_type_logement' in zone_info:
        df_innoc_type = pd.DataFrame(zone_info['innoccupation_type_logement'])
        if not df_innoc_type.empty:
            innoc_tabs_content.append(
                dash_table.DataTable(
                    data=df_innoc_type.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_innoc_type.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            innoc_tabs_labels.append("Par type")
    elif 'innoccupation_type_logement_message' in zone_info:
        innoc_tabs_content.append(
            dbc.Alert(zone_info['innoccupation_type_logement_message'], color="warning")
        )
        innoc_tabs_labels.append("Par type")
    
    # Par fourchette de prix
    if 'innoccupation_par_fourchette_loyer' in zone_info:
        df_innoc_prix = pd.DataFrame(zone_info['innoccupation_par_fourchette_loyer'])
        if not df_innoc_prix.empty:
            innoc_tabs_content.append(
                dash_table.DataTable(
                    data=df_innoc_prix.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in df_innoc_prix.columns],
                    style_cell={'textAlign': 'left'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=10
                )
            )
            innoc_tabs_labels.append("Par prix")
    elif 'innoccupation_par_fourchette_loyer_message' in zone_info:
        innoc_tabs_content.append(
            dbc.Alert(zone_info['innoccupation_par_fourchette_loyer_message'], color="warning")
        )
        innoc_tabs_labels.append("Par prix")
    
    # Afficher les taux d'inoccupation si on a des données
    if innoc_tabs_content:
        tabs = []
        for i, (content_item, label) in enumerate(zip(innoc_tabs_content, innoc_tabs_labels)):
            tabs.append(
                dbc.Tab(content_item, label=label, tab_id=f"innoc-tab-{i}")
            )
        
        content.append(
            dbc.Card([
                dbc.CardHeader("📊 Taux d'inoccupation"),
                dbc.CardBody([
                    dbc.Tabs(tabs, id="innoc-tabs", active_tab="innoc-tab-0" if tabs else None)
                ])
            ], className="mb-3")
        )
    
    # Message si aucune donnée n'est disponible
    if len(content) <= 2:  # Seulement le titre et les infos de base
        content.append(
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "Les données statistiques détaillées sont en cours de chargement ou ne sont pas disponibles pour cette zone."
            ], color="info", className="mt-3")
        )
    
    return html.Div(content)

def create_location_map(lat, lng, zones_info):
    """
    Crée une carte montrant la localisation de la propriété.
    
    Args:
        lat: Latitude
        lng: Longitude
        zones_info: Informations sur les zones
        
    Returns:
        Composant dcc.Graph avec la carte
    """
    fig = go.Figure()
    
    # Ajouter le marqueur de la propriété
    fig.add_trace(go.Scattermapbox(
        lat=[lat],
        lon=[lng],
        mode='markers',
        marker=dict(size=15, color='red'),
        text="Propriété",
        name="Propriété"
    ))
    
    # Configuration de la carte
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=lat, lon=lng),
            zoom=12
        ),
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False
    )
    
    return dcc.Graph(figure=fig, id="geo-location-map")

# ============================================================================
# FONCTION D'EXPORT POUR MAIN2.PY
# ============================================================================

def get_geo_analysis_component(property_data):
    """
    Fonction principale pour obtenir le composant d'analyse géographique.
    À appeler depuis main2.py
    
    Args:
        property_data: Données de la propriété
        
    Returns:
        Composant Dash pour l'onglet d'analyse géographique
    """
    return create_geo_analysis_tab(property_data)