# -*- coding: utf-8 -*-
"""
Module AUTONOME pour la recherche par coordonnées géographiques (latitude, longitude)
Ce fichier est complètement indépendant et contient toutes les fonctions nécessaires
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime
import geopandas as gpd
from shapely.geometry import Point, shape
from shapely import wkb, wkt
import logging
import psycopg2
from contextlib import contextmanager
from psycopg2.extras import RealDictCursor
import binascii
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SECTION 1: CONFIGURATION ET CONNEXION À LA BASE DE DONNÉES
# ============================================================================

# Configuration de la base de données
DB_CONFIG = {
    "dbname": "analysis",
    "user": "postgres",
    "password": "4845",
    "host": "100.73.238.42"
}

# Variables globales
DEBUG_SQL = False  # Désactivé pour la production
SCHEMA_MAPPING = "id"

@contextmanager
def get_connection_context():
    """
    Gestionnaire de contexte pour la connexion à la base de données PostgreSQL
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

def execute_query(query, params=None):
    """
    Exécute une requête SQL et retourne les résultats sous forme d'un DataFrame pandas
    """
    # Debug SQL désactivé
    with get_connection_context() as conn:
        try:
            df = pd.read_sql_query(query, conn, params=params)
            return df
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {e}"
            logger.error(error_msg)
            st.error(error_msg)
            return pd.DataFrame()

def execute_query_dict(query, params=None):
    """
    Exécute une requête SQL et retourne les résultats sous forme de liste de dictionnaires
    """
    # Debug SQL désactivé
    with get_connection_context() as conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution de la requête: {e}"
            logger.error(error_msg)
            st.error(error_msg)
            return []

def execute_query_no_cache(query, params=None):
    """
    Alias pour execute_query - exécute une requête SQL sans cache
    """
    return execute_query(query, params)

# ============================================================================
# SECTION 2: FONCTIONS DE CONVERSION GÉOGRAPHIQUE
# ============================================================================

def create_geodataframe_local(df, geometry_col='geo_zone'):
    """
    Convertit un DataFrame avec des données géométriques en GeoDataFrame
    """
    if df.empty or geometry_col not in df.columns:
        return gpd.GeoDataFrame()
    
    try:
        gdf = gpd.GeoDataFrame(df, geometry=geometry_col)
        if not df.empty and not isinstance(gdf.geometry.iloc[0], (gpd.GeoSeries, wkb.loads(b'').geom_type.__class__)):
            def convert_to_geometry(geo_data):
                if geo_data is None:
                    return None
                if isinstance(geo_data, str):
                    try:
                        return wkt.loads(geo_data)
                    except:
                        try:
                            return wkb.loads(binascii.unhexlify(geo_data))
                        except:
                            pass
                elif isinstance(geo_data, bytes):
                    try:
                        return wkb.loads(geo_data)
                    except:
                        pass
                return None
            
            df['geometry'] = df[geometry_col].apply(convert_to_geometry)
            gdf = gpd.GeoDataFrame(df, geometry='geometry')
    except Exception as e:
        logger.warning(f"Erreur lors de la conversion du DataFrame en GeoDataFrame: {e}")
        df['geometry'] = None
        for i, row in df.iterrows():
            try:
                if isinstance(row[geometry_col], str):
                    try:
                        df.at[i, 'geometry'] = wkt.loads(row[geometry_col])
                    except:
                        try:
                            df.at[i, 'geometry'] = wkb.loads(binascii.unhexlify(row[geometry_col]))
                        except:
                            pass
                elif isinstance(row[geometry_col], bytes):
                    try:
                        df.at[i, 'geometry'] = wkb.loads(row[geometry_col])
                    except:
                        pass
            except:
                pass
        gdf = gpd.GeoDataFrame(df, geometry='geometry')
    
    gdf.crs = "EPSG:4326"
    return gdf

# ============================================================================
# SECTION 3: FONCTIONS DE RÉCUPÉRATION DES DONNÉES GÉOGRAPHIQUES
# ============================================================================

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
# SECTION 4: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - REVENU DES MÉNAGES
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
# SECTION 5: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - ÂGE ET POPULATION
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
# SECTION 6: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - ÉTAT DES LOGEMENTS
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
# SECTION 7: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - WALKSCORE
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
# SECTION 8: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - LOYER MOYEN
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
        logger.error("Aucun secteur de recensement trouvé pour la province du Québec")
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
        logger.error(f"Table {schema_name}.{table_name} n'existe pas")
        return pd.DataFrame()
        
    # Vérifier s'il y a des données pour la plage d'années spécifiée
    count_query = f"""
    SELECT COUNT(*) as count 
    FROM "{schema_name}"."{table_name}"
    WHERE annee BETWEEN {year_range[0]} AND {year_range[1]}
    """
    count_df = execute_query_no_cache(count_query)
    if count_df.iloc[0, 0] == 0:
        logger.warning(f"Aucune donnée trouvée dans {schema_name}.{table_name} pour les années {year_range}")
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
        logger.error(f"Schéma inconnu: {schema_name}")
        return pd.DataFrame()
    
    # Debug SQL désactivé
    df = execute_query(query)
    logger.info(f"Récupération de {len(df)} lignes de données de loyer moyen pour les secteurs de recensement")
    return df

# ============================================================================
# SECTION 9: FONCTIONS DE RÉCUPÉRATION DES DONNÉES - TAUX D'INOCCUPATION
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
        logger.error("Impossible de trouver l'ID de la province du Québec")
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
        logger.error("Aucun secteur de recensement trouvé pour la province du Québec")
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
        logger.error(f"Table {schema_name}.{table_name} n'existe pas")
        return pd.DataFrame()
    
    count_query = f"""
    SELECT COUNT(*) as count 
    FROM "{schema_name}"."{table_name}"
    WHERE annee BETWEEN {year_range[0]} AND {year_range[1]}
    """
    count_df = execute_query_no_cache(count_query)
    if count_df.iloc[0, 0] == 0:
        logger.warning(f"Aucune donnée trouvée dans {schema_name}.{table_name} pour les années {year_range}")
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
        logger.warning(f"Table de dimension {SCHEMA_MAPPING}.{dimension_table} n'existe pas. Requête simplifiée utilisée.")
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
            logger.warning(f"Schéma {schema_name} non supporté pour les secteurs de recensement")
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
    
    # Debug SQL désactivé
    df = execute_query(query)
    logger.info(f"Récupération de {len(df)} lignes de données d'inoccupation pour les secteurs de recensement")
    return df

# ============================================================================
# SECTION 10: FONCTIONS PRINCIPALES DE RECHERCHE PAR COORDONNÉES
# ============================================================================

def find_zone_for_coordinates(lat, lng, geo_level='Secteur de recensement'):
    """
    Trouve la zone (province, région, secteur, quartier ou secteur de recensement) 
    contenant les coordonnées spécifiées.
    
    Args:
        lat: Latitude
        lng: Longitude
        geo_level: Niveau géographique ('Province', 'Région du Québec', 'Secteur du Québec', 
                  'Quartier du Québec', 'Secteur de recensement')
                  
    Returns:
        Tuple (code_zone, nom_zone) ou None si aucune zone trouvée
    """
    point = Point(lng, lat)  # GeoJSON utilise (longitude, latitude)
    
    # Charger les données géographiques selon le niveau
    if geo_level == 'Province':
        # Pour la province, pas besoin de chercher - c'est forcément le Québec
        return ('QC', 'Quebec')
    elif geo_level == 'Région du Québec':
        gdf = get_quebec_regions_geo()
        # Vérifier quelles colonnes sont disponibles dans le GeoDataFrame
        if 'region_code' in gdf.columns:
            id_col = 'region_code'
        elif 'code_region' in gdf.columns:
            id_col = 'code_region'
        else:
            # Utilisez la première colonne comme identifiant si aucune des colonnes attendues n'existe
            if len(gdf.columns) > 0:
                id_col = gdf.columns[0]
            else:
                return None
            
        if 'region_nom' in gdf.columns:
            name_col = 'region_nom'
        elif 'nom_region' in gdf.columns:
            name_col = 'nom_region'
        elif 'nom' in gdf.columns:
            name_col = 'nom'
        else:
            # Utilisez la deuxième colonne comme nom si aucune des colonnes attendues n'existe
            if len(gdf.columns) > 1:
                name_col = gdf.columns[1]
            else:
                name_col = id_col  # Utiliser l'ID comme nom si une seule colonne est disponible
    elif geo_level == 'Secteur du Québec':
        gdf = get_quebec_sectors_geo()
        # Vérifier quelles colonnes sont disponibles
        if 'secteur_code' in gdf.columns:
            id_col = 'secteur_code'
        elif 'code_secteur' in gdf.columns:
            id_col = 'code_secteur'
        else:
            if len(gdf.columns) > 0:
                id_col = gdf.columns[0]
            else:
                return None
                
        if 'secteur_nom' in gdf.columns:
            name_col = 'secteur_nom'
        elif 'nom_secteur' in gdf.columns:
            name_col = 'nom_secteur'
        elif 'nom' in gdf.columns:
            name_col = 'nom'
        else:
            if len(gdf.columns) > 1:
                name_col = gdf.columns[1]
            else:
                name_col = id_col
    elif geo_level == 'Quartier du Québec':
        gdf = get_quebec_quartiers_geo()
        # Vérifier quelles colonnes sont disponibles
        if 'quartier_code' in gdf.columns:
            id_col = 'quartier_code'
        elif 'code_quartier' in gdf.columns:
            id_col = 'code_quartier'
        else:
            if len(gdf.columns) > 0:
                id_col = gdf.columns[0]
            else:
                return None
                
        if 'quartier_nom_fr' in gdf.columns:
            name_col = 'quartier_nom_fr'
        elif 'nom_quartier' in gdf.columns:
            name_col = 'nom_quartier'
        elif 'nom' in gdf.columns:
            name_col = 'nom'
        else:
            if len(gdf.columns) > 1:
                name_col = gdf.columns[1]
            else:
                name_col = id_col
    else:  # Secteur de recensement
        # Pour les secteurs de recensement, on doit d'abord identifier la région
        # car un même code de secteur de recensement peut exister dans plusieurs régions
        region_result = find_zone_for_coordinates(lat, lng, 'Région du Québec')
        if not region_result:
            return None
            
        region_id, region_name = region_result
        
        # Ensuite, on cherche le secteur de recensement mais uniquement dans cette région
        gdf = get_quebec_secteur_recensement_geo()
        
        # Filtrer pour ne garder que les secteurs de la région identifiée
        if 'region_nom' in gdf.columns:
            gdf = gdf[gdf['region_nom'] == region_name]
        elif 'region_id' in gdf.columns and region_id.isdigit():
            gdf = gdf[gdf['region_id'] == int(region_id)]
            
        if gdf.empty:
            return None
            
        # Vérifier quelles colonnes sont disponibles
        if 'secteur_rec_code' in gdf.columns:
            id_col = 'secteur_rec_code'
        elif 'code_secteur_rec' in gdf.columns:
            id_col = 'code_secteur_rec'
        else:
            if len(gdf.columns) > 0:
                id_col = gdf.columns[0]
            else:
                return None
                
        if 'secteur_rec_nom' in gdf.columns:
            name_col = 'secteur_rec_nom'
        elif 'nom_secteur_rec' in gdf.columns:
            name_col = 'nom_secteur_rec'
        elif 'nom' in gdf.columns:
            name_col = 'nom'
        else:
            if len(gdf.columns) > 1:
                name_col = gdf.columns[1]
            else:
                name_col = id_col
    
    if gdf.empty:
        return None
    
    # Vérifier dans quelle zone se trouve le point
    for idx, row in gdf.iterrows():
        try:
            # Vérifier que la géométrie est valide
            if not row.geometry.is_valid:
                continue
            
            if row.geometry.contains(point):
                try:
                    # Utiliser des valeurs par défaut si les colonnes spécifiées n'existent pas
                    zone_id = str(row.get(id_col, idx))
                    zone_name = str(row.get(name_col, f"Zone {idx}"))
                    
                    # Pour les secteurs de recensement, ajouter l'information sur la région
                    if geo_level == 'Secteur de recensement' and 'region_nom' in row:
                        return (zone_id, f"{zone_name} ({row['region_nom']})")
                    else:
                        return (zone_id, zone_name)
                except Exception:
                    # Retourner des valeurs par défaut basées sur l'index
                    return (str(idx), f"Zone {idx}")
        except Exception:
            pass
    
    return None

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
            st.warning(f"Colonne géographique non trouvée. Colonnes disponibles: {df.columns.tolist()}. Utilisation de {df.columns[0]} comme fallback.")
            return df.columns[0]
        return None
    
    def filter_by_zone(df, zone_value):
        """Filtre le DataFrame pour ne garder que les lignes correspondant à la zone spécifiée"""
        geo_col = find_geo_column(df)
        if not geo_col:
            logger.debug(f"Aucune colonne géographique trouvée")
            return pd.DataFrame()
        
        # Recherche zone
        
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
                logger.debug(f"Erreur lors du filtrage par secteur: {e}")
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
            
            logger.debug(f"Récupération données loyer: {schema_name}, {geo_level}")
            
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
            
            logger.debug(f"Données récupérées: {len(loyer_df)} lignes")
            
            schema_key = schema_name.replace("loyer_moyen_", "loyer_")
            
            if not loyer_df.empty:
                logger.debug(f"Filtrage par zone: {zone_name}")
                zone_df = filter_by_zone(loyer_df, zone_name)
                logger.debug(f"Données filtrées: {len(zone_df)} lignes")
                if not zone_df.empty:
                    info[schema_key] = zone_df.to_dict('records')
                    # Données ajoutées
                else:
                    info[f"{schema_key}_message"] = f"Aucune donnée disponible pour le secteur {zone_name} - {schema_name.replace('_', ' ')}"
                    logger.warning(f"Aucune donnée après filtrage pour {schema_name} - zone: {zone_name}")
            else:
                info[f"{schema_key}_message"] = f"Aucune donnée disponible dans la base pour {schema_name.replace('_', ' ')}"
                logger.warning(f"Aucune donnée trouvée pour {schema_name}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données de loyer moyen: {e}")
        st.warning(f"Erreur lors de la récupération des données de loyer moyen: {e}")
    
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
            
            logger.debug(f"Récupération données inoccupation: {schema_name}, {geo_level}")
            
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
            
            logger.debug(f"Données récupérées: {len(innoc_df)} lignes")
            
            # Ne pas modifier le préfixe innoccupation_
            schema_key = schema_name
            
            if not innoc_df.empty:
                logger.debug(f"Filtrage par zone: {zone_name}")
                zone_df = filter_by_zone(innoc_df, zone_name)
                logger.debug(f"Données filtrées: {len(zone_df)} lignes")
                if not zone_df.empty:
                    info[schema_key] = zone_df.to_dict('records')
                    # Données ajoutées
                else:
                    info[f"{schema_key}_message"] = f"Aucune donnée disponible pour le secteur {zone_name} - {schema_name.replace('_', ' ')}"
                    logger.warning(f"Aucune donnée d'inoccupation après filtrage pour {schema_name} - zone: {zone_name}")
            else:
                info[f"{schema_key}_message"] = f"Aucune donnée disponible dans la base pour {schema_name.replace('_', ' ')}"
                logger.warning(f"Aucune donnée d'inoccupation trouvée pour {schema_name}")
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données d'innoccupation: {e}")
        st.warning(f"Erreur lors de la récupération des données d'innoccupation: {e}")
    
    # Retourner les infos
    return info

def _render_zone_info(zone, geo_level):
    """
    Fonction helper pour afficher les informations d'une zone
    """
    if zone:
        info = get_all_info_for_zone(zone[0], zone[1], geo_level)
        if info:
            if geo_level == 'Province':
                st.write("### Informations sur la province")
            else:
                st.write(f"### Informations sur {geo_level.lower()}: {zone[1]}")
            
            # Affichage des données uniquement
            
            if 'revenu' in info:
                st.write("#### Revenu des ménages")
                st.dataframe(pd.DataFrame(info['revenu']), use_container_width=True)
            if 'age' in info:
                st.write("#### Population par âge")
                st.dataframe(pd.DataFrame(info['age']), use_container_width=True)
            if 'logement' in info:
                st.write("#### État des logements")
                st.dataframe(pd.DataFrame(info['logement']), use_container_width=True)
            if 'walkscore' in info:
                st.write("#### Walkscore")
                st.dataframe(pd.DataFrame(info['walkscore']), use_container_width=True)
            
            # Loyers moyens par catégorie
            loyer_categories = [k for k in info.keys() if k.startswith('loyer_') and not k.endswith('_message')]
            loyer_messages = [k for k in info.keys() if k.startswith('loyer_') and k.endswith('_message')]
            
            # Toujours afficher la section loyers moyens, même s'il n'y a que des messages
            if loyer_categories or loyer_messages:
                st.write("#### Loyers moyens")
                loyer_tabs = st.tabs(["Par année de construction", "Par taille de logement", "Par type de logement"])
                
                # Par année de construction
                with loyer_tabs[0]:
                    if 'loyer_by_annees' in info:
                        st.dataframe(pd.DataFrame(info['loyer_by_annees']), use_container_width=True)
                    elif 'loyer_by_annees_message' in info:
                        st.warning(info['loyer_by_annees_message'])
                    else:
                        st.info("Aucune donnée disponible pour les loyers moyens par année de construction")
                
                # Par taille de logement
                with loyer_tabs[1]:
                    if 'loyer_par_taille_logement' in info:
                        st.dataframe(pd.DataFrame(info['loyer_par_taille_logement']), use_container_width=True)
                    elif 'loyer_par_taille_logement_message' in info:
                        st.warning(info['loyer_par_taille_logement_message'])
                    else:
                        st.info("Aucune donnée disponible pour les loyers moyens par taille de logement")
                
                # Par type de logement
                with loyer_tabs[2]:
                    if 'loyer_type_logement' in info:
                        st.dataframe(pd.DataFrame(info['loyer_type_logement']), use_container_width=True)
                    elif 'loyer_type_logement_message' in info:
                        st.warning(info['loyer_type_logement_message'])
                    else:
                        st.info("Aucune donnée disponible pour les loyers moyens par type de logement")
            
            # Taux d'innoccupation par catégorie
            innoc_categories = [k for k in info.keys() if k.startswith('innoccupation_') and not k.endswith('_message')]
            innoc_messages = [k for k in info.keys() if k.startswith('innoccupation_') and k.endswith('_message')]
            
            # Toujours afficher la section inoccupation, même s'il n'y a que des messages
            if innoc_categories or innoc_messages:
                st.write("#### Taux d'innoccupation")
                innoc_tabs = st.tabs(["Par année de construction", "Par taille de logement", "Par type de logement", "Par fourchette de prix"])
                
                # Par année de construction
                with innoc_tabs[0]:
                    if 'innoccupation_by_annees' in info:
                        st.dataframe(pd.DataFrame(info['innoccupation_by_annees']), use_container_width=True)
                    elif 'innoccupation_by_annees_message' in info:
                        st.warning(info['innoccupation_by_annees_message'])
                    else:
                        st.info("Aucune donnée disponible pour les taux d'innoccupation par année de construction")
                
                # Par taille de logement
                with innoc_tabs[1]:
                    if 'innoccupation_par_taille_logement' in info:
                        st.dataframe(pd.DataFrame(info['innoccupation_par_taille_logement']), use_container_width=True)
                    elif 'innoccupation_par_taille_logement_message' in info:
                        st.warning(info['innoccupation_par_taille_logement_message'])
                    else:
                        st.info("Aucune donnée disponible pour les taux d'innoccupation par taille de logement")
                
                # Par type de logement
                with innoc_tabs[2]:
                    if 'innoccupation_type_logement' in info:
                        st.dataframe(pd.DataFrame(info['innoccupation_type_logement']), use_container_width=True)
                    elif 'innoccupation_type_logement_message' in info:
                        st.warning(info['innoccupation_type_logement_message'])
                    else:
                        st.info("Aucune donnée disponible pour les taux d'innoccupation par type de logement")
                
                # Par fourchette de prix
                with innoc_tabs[3]:
                    if 'innoccupation_par_fourchette_loyer' in info:
                        st.dataframe(pd.DataFrame(info['innoccupation_par_fourchette_loyer']), use_container_width=True)
                    elif 'innoccupation_par_fourchette_loyer_message' in info:
                        st.warning(info['innoccupation_par_fourchette_loyer_message'])
                    else:
                        st.info("Aucune donnée disponible pour les taux d'innoccupation par fourchette de prix")

# ============================================================================
# SECTION 11: FONCTION PRINCIPALE DE RENDU DE L'INTERFACE
# ============================================================================

def render_recherche_par_coordonnees():
    """
    Fonction principale pour rendre l'interface de recherche par coordonnées
    """
    st.title("🗺️ Recherche par Coordonnées Géographiques")
    st.write("Entrez directement les coordonnées latitude et longitude pour obtenir toutes les informations disponibles.")
    
    # Champs d'entrée pour les coordonnées
    col1, col2 = st.columns(2)
    
    with col1:
        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=45.5017,  # Montréal comme exemple
            step=0.000001,
            format="%.6f",
            help="Latitude en degrés décimaux (ex: 45.501689 pour Montréal)"
        )
    
    with col2:
        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=-73.5673,  # Montréal comme exemple
            step=0.000001,
            format="%.6f",
            help="Longitude en degrés décimaux (ex: -73.567256 pour Montréal)"
        )
    
    # Afficher les coordonnées actuelles
    st.info(f"📍 Coordonnées actuelles: {latitude:.6f}, {longitude:.6f}")
    
    # Exemples de coordonnées
    with st.expander("💡 Exemples de coordonnées"):
        example_coords = {
            "Montréal (Centre-ville)": (45.501689, -73.567256),
            "Québec (Vieux-Québec)": (46.813878, -71.207981),
            "Gatineau": (45.476766, -75.701040),
            "Sherbrooke": (45.404167, -71.892776),
            "Trois-Rivières": (46.343456, -72.542969)
        }
        
        for city, (lat, lng) in example_coords.items():
            if st.button(f"{city}: {lat:.6f}, {lng:.6f}", key=f"coord_{city}"):
                st.rerun()
    
    if st.button("🔍 Analyser cette localisation", type="primary"):
        if latitude and longitude:
            with st.spinner("Analyse en cours..."):
                # Vérifier que les coordonnées sont dans une plage raisonnable pour le Québec
                if not (44.0 <= latitude <= 62.0 and -79.8 <= longitude <= -57.1):
                    st.warning("⚠️ Ces coordonnées semblent être en dehors du Québec. Les résultats pourraient être limités.")
                
                # Créer des colonnes pour les informations par niveau géographique
                col1, col2 = st.columns(2)
                
                # Trouver la zone pour chaque niveau géographique
                with col1:
                    st.subheader("🎯 Zones identifiées")
                    
                    # Province (toujours Québec)
                    province = ('QC', 'Quebec')
                    st.write(f"**🏛️ Province:** {province[1]}")
                    
                    # Région
                    region = find_zone_for_coordinates(latitude, longitude, 'Région du Québec')
                    if region:
                        st.write(f"**🌍 Région:** {region[1]}")
                    else:
                        st.warning("❌ Région non identifiée")
                    
                    # Secteur
                    secteur = find_zone_for_coordinates(latitude, longitude, 'Secteur du Québec')
                    if secteur:
                        st.write(f"**🏙️ Secteur:** {secteur[1]}")
                    else:
                        st.warning("❌ Secteur non identifié")
                    
                    # Quartier
                    quartier = find_zone_for_coordinates(latitude, longitude, 'Quartier du Québec')
                    if quartier:
                        st.write(f"**🏘️ Quartier:** {quartier[1]}")
                    else:
                        st.warning("❌ Quartier non identifié")
                    
                    # Secteur de recensement
                    secteur_rec = find_zone_for_coordinates(latitude, longitude, 'Secteur de recensement')
                    if secteur_rec:
                        st.write(f"**📊 Secteur de recensement:** {secteur_rec[1]}")
                    else:
                        st.warning("❌ Secteur de recensement non identifié")
                
                # Afficher la carte avec le point et les limites de secteur
                with col2:
                    st.subheader("🗺️ Localisation")
                    
                    try:
                        # Créer un GeoDataFrame pour le point
                        point_df = pd.DataFrame({'lat': [latitude], 'lon': [longitude]})
                        
                        # Charger les données de secteur de recensement
                        gdf_secteur = get_quebec_secteur_recensement_geo()
                        
                        if not gdf_secteur.empty:
                            # Afficher la carte avec plotly
                            fig = px.choropleth_mapbox(
                                gdf_secteur,
                                geojson=gdf_secteur.__geo_interface__,
                                locations=gdf_secteur.index,
                                mapbox_style="open-street-map",
                                zoom=12,
                                center={"lat": latitude, "lon": longitude},
                                opacity=0.3
                            )
                            
                            # Ajouter le point
                            fig.add_scattermapbox(
                                lat=[latitude],
                                lon=[longitude],
                                mode='markers',
                                marker=go.scattermapbox.Marker(size=15, color='red'),
                                name='Position analysée',
                                text=f"Lat: {latitude:.6f}<br>Lng: {longitude:.6f}"
                            )
                            
                            fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            # Carte simple sans secteurs
                            fig = go.Figure(go.Scattermapbox(
                                lat=[latitude],
                                lon=[longitude],
                                mode='markers',
                                marker=go.scattermapbox.Marker(size=15, color='red'),
                                name='Position analysée',
                                text=f"Lat: {latitude:.6f}<br>Lng: {longitude:.6f}"
                            ))
                            
                            fig.update_layout(
                                mapbox_style="open-street-map",
                                mapbox=dict(
                                    center=go.layout.mapbox.Center(lat=latitude, lon=longitude),
                                    zoom=12
                                ),
                                margin={"r":0,"t":0,"l":0,"b":0},
                                height=400
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erreur lors de l'affichage de la carte: {e}")
                
                # Créer des onglets pour chaque niveau
                level_tabs = st.tabs(["🏛️ Province", "🌍 Région", "🏙️ Secteur", "🏘️ Quartier", "📊 Secteur de recensement"])
                
                # Province
                with level_tabs[0]:
                    _render_zone_info(province, 'Province')

                # Région
                with level_tabs[1]:
                    if region:
                        _render_zone_info(region, 'Région du Québec')
                    else:
                        st.error("❌ Impossible de récupérer les informations pour cette région.")

                # Secteur
                with level_tabs[2]:
                    if secteur:
                        _render_zone_info(secteur, 'Secteur du Québec')
                    else:
                        st.error("❌ Impossible de récupérer les informations pour ce secteur.")

                # Quartier
                with level_tabs[3]:
                    if quartier:
                        _render_zone_info(quartier, 'Quartier du Québec')
                    else:
                        st.error("❌ Impossible de récupérer les informations pour ce quartier.")

                # Secteur de recensement
                with level_tabs[4]:
                    if secteur_rec:
                        _render_zone_info(secteur_rec, 'Secteur de recensement')
                    else:
                        st.error("❌ Impossible de récupérer les informations pour ce secteur de recensement.")
        else:
            st.error("❌ Veuillez entrer des coordonnées valides.")

# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    render_recherche_par_coordonnees()