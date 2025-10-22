from shapely.geometry import Point
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads
from sqlalchemy import create_engine
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, dash_table, ctx, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from itertools import product
from sqlalchemy import create_engine
from datetime import date, datetime
from dash.dash_table.Format import Format, Scheme
from dash.dash_table import FormatTemplate
import json
from dash.exceptions import PreventUpdate
import re
from shapely import wkt
from shapely import wkb
import binascii

from filter.data_loading import (
    load_immeubles, load_immeubles_history, load_provinces, load_regions,
    load_secteurs, load_quartiers, load_secteurs_recensement
)






def update_geographic_filters(data_source, selected_property):
    if data_source == "active":
        df = load_immeubles()
    else:
        return html.Div([
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "Les filtres géographiques sont disponibles uniquement pour les immeubles actifs."
            ], color="info")
        ])
    
    # Province
    provinces_df = load_provinces()
    province_options = [{"label": "Toutes", "value": "all"}] + [
        {"label": p, "value": p} for p in provinces_df['province_name'].tolist()
    ]
    
    return html.Div([
        # Province
                html.Div([
            html.Label("Province", className="fw-bold text-sm"),
            dcc.Dropdown(
                id="filter-province",
                options=province_options,
                value="all",
                placeholder="Sélectionner une province...",
                className="mb-2"
            )
        ]),
        
        # Région
        html.Div(id="region-filter-container"),
        
        # Type de filtre détaillé
        html.Div(id="detailed-filter-container")
    ])


def update_region_filter(province):
    if not province or province == "all":
        return html.Div()
    
    # Obtenir l'ID de la province
    provinces_df = load_provinces()
    province_row = provinces_df[provinces_df['province_name'] == province]
    
    if province_row.empty:
        return html.Div()
    
    province_id = province_row['province_id'].iloc[0]
    regions_df = load_regions(province_id)
    
    if regions_df.empty:
        return html.Div()
    
    region_options = [{"label": "Toutes", "value": "all"}] + [
        {"label": r, "value": r} for r in regions_df['region_nom'].tolist()
    ]
    
    return html.Div([
        html.Label("Région", className="fw-bold text-sm"),
        dcc.Dropdown(
            id="filter-region",
            options=region_options,
            value="all",
            placeholder="Sélectionner une région...",
            className="mb-2"
        )
    ])

def update_detailed_filters(region, province):
    if not region or region == "all" or not province or province == "all":
        return html.Div()
    
    try:
        # Obtenir l'ID de la région
        provinces_df = load_provinces()
        province_id = provinces_df[provinces_df['province_name'] == province]['province_id'].iloc[0]
        regions_df = load_regions(province_id)
        region_row = regions_df[regions_df['region_nom'] == region]
        
        if region_row.empty:
            return html.Div()
        
        region_id = region_row['region_id'].iloc[0]
        
        return html.Div([
            html.Label("Type de filtre détaillé", className="fw-bold text-sm"),
            dcc.RadioItems(
                id="filter-type",
                options=[
                    {"label": "Aucun", "value": "none"},
                    {"label": "Secteur", "value": "secteur"},
                    {"label": "Quartier", "value": "quartier"},
                    {"label": "Secteur de recensement", "value": "secteur_recensement"}
                ],
                value="none",
                className="mb-2"
            ),
            html.Div(id="specific-filter-container")
        ])
    except Exception:
        return html.Div()
    


def update_specific_filter(filter_type, region, province):
    if not filter_type or filter_type == "none" or not region or region == "all":
        return html.Div()
    
    # Obtenir l'ID de la région
    provinces_df = load_provinces()
    province_id = provinces_df[provinces_df['province_name'] == province]['province_id'].iloc[0]
    regions_df = load_regions(province_id)
    region_id = regions_df[regions_df['region_nom'] == region]['region_id'].iloc[0]
    
    if filter_type == "secteur":
        secteurs_df = load_secteurs(region_id)
        options = [{"label": s, "value": s} for s in secteurs_df['secteur_nom'].tolist()]
        label = "Secteur"
    elif filter_type == "quartier":
        quartiers_df = load_quartiers(region_id)
        options = [{"label": q, "value": q} for q in quartiers_df['quartier_nom_fr'].tolist()]
        label = "Quartier"
    elif filter_type == "secteur_recensement":
        secteurs_rec_df = load_secteurs_recensement(region_id)
        options = [{"label": s, "value": s} for s in secteurs_rec_df['secteur_rec_code'].tolist()]
        label = "Secteur de recensement"
    else:
        return html.Div()
    
    return html.Div([
        html.Label(label, className="fw-bold text-sm"),
        dcc.Dropdown(
            id="specific-zone-filter",
            options=options,
            placeholder=f"Sélectionner un {label.lower()}...",
            className="mb-2"
        )
    ])
def filter_properties_by_geography(province, region, filter_type, specific_zone, 
                                  data_source, hist_date):
    try:
        print(f"\n=== Début du filtrage géographique ===")
        print(f"Province: {province}, Région: {region}, Type: {filter_type}, Zone: {specific_zone}")
        
        # Charger les données
        if data_source == "active":
            df = load_immeubles()
        elif data_source == "historical":
            df = load_immeubles_history(pd.to_datetime(hist_date).date())
        else:
            df_hist = load_immeubles_history(pd.to_datetime(hist_date).date())
            df_live = load_immeubles()
            df = df_hist[~df_hist['address'].isin(df_live['address'].unique())]
        
        print(f"Nombre total d'immeubles: {len(df)}")
        
        # Si aucun filtre géographique n'est sélectionné, retourner toutes les adresses
        if not province or province == "all":
            print("Aucun filtre géographique appliqué")
            # Ne pas utiliser unique() pour permettre les doublons
            return df['address'].tolist()
        
        # Obtenir la géométrie appropriée
        geometry = None
        
        try:
            if specific_zone and filter_type and filter_type != "none":
                # Filtrer par zone spécifique
                print(f"Filtrage par {filter_type}: {specific_zone}")
                provinces_df = load_provinces()
                province_id = provinces_df[provinces_df['province_name'] == province]['province_id'].iloc[0]
                regions_df = load_regions(province_id)
                region_id = regions_df[regions_df['region_nom'] == region]['region_id'].iloc[0]
                
                if filter_type == "secteur":
                    secteurs_df = load_secteurs(region_id)
                    zone_id = secteurs_df[secteurs_df['secteur_nom'] == specific_zone]['secteur_id'].iloc[0]
                elif filter_type == "quartier":
                    quartiers_df = load_quartiers(region_id)
                    zone_id = quartiers_df[quartiers_df['quartier_nom_fr'] == specific_zone]['quartier_id'].iloc[0]
                elif filter_type == "secteur_recensement":
                    secteurs_rec_df = load_secteurs_recensement(region_id)
                    zone_id = secteurs_rec_df[secteurs_rec_df['secteur_rec_code'] == specific_zone]['secteur_rec_id'].iloc[0]
                
                print(f"Zone ID trouvé: {zone_id}")
                geometry = get_zone_geometry(filter_type, zone_id)
            elif region and region != "all":
                # Filtrer par région
                print(f"Filtrage par région: {region}")
                provinces_df = load_provinces()
                province_id = provinces_df[provinces_df['province_name'] == province]['province_id'].iloc[0]
                regions_df = load_regions(province_id)
                region_id = regions_df[regions_df['region_nom'] == region]['region_id'].iloc[0]
                print(f"Region ID trouvé: {region_id}")
                geometry = get_zone_geometry('region', region_id)
            else:
                # Filtrer par province
                print(f"Filtrage par province: {province}")
                provinces_df = load_provinces()
                province_id = provinces_df[provinces_df['province_name'] == province]['province_id'].iloc[0]
                print(f"Province ID trouvé: {province_id}")
                geometry = get_zone_geometry('province', province_id)
        except IndexError as e:
            print(f"Zone non trouvée: {e}")
            return []
        except Exception as e:
            print(f"Erreur lors de la récupération de la géométrie: {e}")
            import traceback
            traceback.print_exc()
            # Retourner toutes les propriétés en cas d'erreur
            return df['address'].tolist()
        
        # Appliquer le filtre géographique
        if geometry:
            print("Géométrie récupérée avec succès, application du filtre")
            df_filtered = filter_immeubles_by_geometry(df, geometry)
            if df_filtered.empty:
                print("Aucun immeuble trouvé dans la zone sélectionnée")
                return []
            print(f"Nombre d'immeubles après filtrage: {len(df_filtered)}")
            # Ne pas utiliser unique() pour permettre les doublons
            return df_filtered['address'].tolist()
        else:
            print("Aucune géométrie trouvée, retour de tous les immeubles")
            return df['address'].tolist()
            
    except Exception as e:
        print(f"Erreur lors du filtrage géographique: {e}")
        import traceback
        traceback.print_exc()
        # En cas d'erreur, retourner une liste vide plutôt que de crasher
        return []


def filter_immeubles_by_geometry(df_immeubles, geometry):
    """Filtre les immeubles qui sont dans la géométrie donnée en utilisant latitude/longitude"""
    
    if geometry is None:
        print("Pas de géométrie fournie, retour de tous les immeubles")
        return df_immeubles
        
    if df_immeubles.empty:
        print("DataFrame des immeubles vide")
        return df_immeubles
    
    # Vérifier que les colonnes latitude et longitude existent
    if 'latitude' not in df_immeubles.columns or 'longitude' not in df_immeubles.columns:
        print("Colonnes latitude/longitude manquantes")
        print(f"Colonnes disponibles: {df_immeubles.columns.tolist()}")
        return df_immeubles
    
    # Copier le DataFrame pour éviter les modifications
    df_work = df_immeubles.copy()
    
    # Nettoyer le DataFrame pour ne garder que les immeubles avec des coordonnées valides
    df_work = df_work.dropna(subset=['latitude', 'longitude'])
    print(f"Immeubles avec coordonnées valides: {len(df_work)}/{len(df_immeubles)}")
    
    if df_work.empty:
        print("Aucun immeuble avec des coordonnées valides")
        return pd.DataFrame()
    
    # Convertir les coordonnées en float si nécessaire
    df_work['latitude'] = pd.to_numeric(df_work['latitude'], errors='coerce')
    df_work['longitude'] = pd.to_numeric(df_work['longitude'], errors='coerce')
    
    # Filtrer à nouveau après conversion
    df_work = df_work.dropna(subset=['latitude', 'longitude'])
    
    # Créer une fonction pour vérifier si un point est dans la géométrie
    def point_in_geometry(row):
        try:
            lat = float(row['latitude'])
            lon = float(row['longitude'])
            
            # Vérifier que les coordonnées sont dans des plages valides
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Important: Point prend (longitude, latitude) dans cet ordre
                point = Point(lon, lat)
                return geometry.contains(point) or geometry.intersects(point)
            else:
                print(f"Coordonnées invalides: lat={lat}, lon={lon}")
                return False
        except (ValueError, TypeError) as e:
            print(f"Erreur avec les coordonnées: {e}")
            return False
    
    # Appliquer le filtre
    mask = df_work.apply(point_in_geometry, axis=1)
    df_filtered = df_work[mask]
    
    print(f"Immeubles dans la zone: {len(df_filtered)}")
    
    return df_filtered


def get_zone_geometry(zone_type, zone_id):
    """Récupère la géométrie d'une zone spécifique"""
    
    engine = create_engine(
        "postgresql://postgres:4845@100.73.238.42:5432/analysis",
        connect_args={"client_encoding": "utf8"}
    )
    
    table_map = {
        'province': ('Canada_Provinces_ID', 'province_id'),
        'region': ('Province_Quebec_Regions_ID', 'region_id'),
        'secteur': ('Province_Quebec_Regions_Secteurs_ID', 'secteur_id'),
        'quartier': ('Province_Quebec_Quartiers_ID', 'quartier_id'),
        'secteur_recensement': ('Province_Quebec_Secteurs_recensement_ID', 'secteur_rec_id')
    }
    
    if zone_type not in table_map:
        return None
        
    table_name, id_column = table_map[zone_type]
    
    # Requête pour récupérer la géométrie
    query = f'''
        SELECT 
            ST_AsEWKB(geo_zone) as geom_bin,
            ST_AsText(geo_zone) as geom_text,
            ST_IsValid(geo_zone) as is_valid,
            ST_GeometryType(geo_zone) as geom_type,
            ST_AsGeoJSON(geo_zone) as geom_json
        FROM id."{table_name}" 
        WHERE {id_column} = {zone_id}
    '''
    
    try:
        result = pd.read_sql(query, engine)
        engine.dispose()
        
        if result.empty:
            print(f"Aucune géométrie trouvée pour {zone_type} avec ID {zone_id}")
            return None
            
        if not result['is_valid'].iloc[0]:
            print(f"Géométrie invalide pour {zone_type} avec ID {zone_id}")
            # Essayer de réparer la géométrie
            query_repair = f'''
                SELECT 
                    ST_AsEWKB(ST_MakeValid(geo_zone)) as geom_bin,
                    ST_AsText(ST_MakeValid(geo_zone)) as geom_text
                FROM id."{table_name}" 
                WHERE {id_column} = {zone_id}
            '''
            result = pd.read_sql(query_repair, engine)
            
        # Essayer d'abord avec EWKB
        if result['geom_bin'].iloc[0] is not None:
            try:
                if isinstance(result['geom_bin'].iloc[0], memoryview):
                    geometry = wkb_loads(bytes(result['geom_bin'].iloc[0]))
                else:
                    geometry = wkb_loads(result['geom_bin'].iloc[0])
                print(f"Géométrie chargée avec succès : {result['geom_type'].iloc[0]}")
                return geometry
            except Exception as e:
                print(f"Erreur EWKB: {e}")
        
        # Si EWKB échoue, essayer avec WKT
        if result['geom_text'].iloc[0] is not None:
            try:
                geometry = wkt_loads(result['geom_text'].iloc[0])
                print(f"Géométrie chargée avec succès (WKT) : {result['geom_type'].iloc[0]}")
                return geometry
            except Exception as e:
                print(f"Erreur WKT: {e}")
                
        return None
            
    except Exception as e:
        print(f"Erreur lors de la récupération de la géométrie: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if 'engine' in locals():
            engine.dispose()
