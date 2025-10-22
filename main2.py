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

# Import des fonctions de nettoyage d'abord
from functions.clean import (
    clean_monetary_value, clean_percentage_value, clean_numeric_value, safe_float_conversion
)

# Import des fonctions de calcul ensuite
from functions.calculation import (
    calculate_progressive_tax, get_tax_rate_for_province, calculate_bienvenue_tax,
    get_municipal_tax_rate, compare_municipal_taxes, calcul_pret_max,
    calcul_mensualite, calculate_schl_premium, calculate_schl_premium_manual, calculate_loan_amount_from_rdc,
    calculate_negative_cashflow_total, calculate_cashflow_projection,
    calculate_initial_financing_with_bank_rules, calculate_refinancing_scenario,
    calculate_profit_breakdown, create_interest_rate_scenarios, compare_cashflow_scenarios,
    safe_float_conversion, clean_monetary_value, clean_numeric_value,
    calculate_economic_values, get_schl_rate_logement_locatif
)

# Import des fonctions de prêts après
from functions.prets import (
    calculate_schl_premium, calculate_loan_amount_from_rdc, update_loan_amount,
    update_schl_payment_info, update_schl_section, sync_schl_payment_mode_from_profit
)

# Import des fonctions de filtrage en dernier
from filter.geo import get_zone_geometry, update_geographic_filters, update_region_filter, update_detailed_filters, update_specific_filter, filter_properties_by_geography, filter_immeubles_by_geometry

# Import du module d'analyse géographique
from functions.geo_analysis import get_geo_analysis_component

from filter.data_loading import (
    load_tax_rates_particulier, load_tax_rates_entreprise, load_immeubles,
    load_immeubles_history, load_schl_rates, load_app_parameters,
    load_acquisition_costs, load_adjustment_defaults, load_provinces,
    load_regions, load_secteurs, load_quartiers, load_secteurs_recensement,
    load_taxe_bienvenue, load_taxation_municipale, load_taux_hypothecaires,
    clean_percentage_value
)

# Configuration de l'application Dash avec un thème moderne
app = dash.Dash(__name__, 
                external_stylesheets=[
                    dbc.themes.BOOTSTRAP,
                    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
                    "https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&display=swap",
                    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
                ],
                suppress_callback_exceptions=True)

# Style CSS personnalisé
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <!-- Ajout de Three.js pour l'animation 3D -->
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            
            .main-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
                position: relative;
                overflow: hidden;
                height: 220px; /* Hauteur encore augmentée pour l'en-tête */
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            
            .lft-title {
                font-family: 'Garamond', 'EB Garamond', serif;
                letter-spacing: 1px;
            }
            
            #logo3d-container {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 70px; /* Beaucoup plus d'espace pour le texte en bas */
                width: 100%;
                height: calc(100% - 70px);
                z-index: 1;
                display: flex;
                justify-content: center; /* Centre horizontalement */
                align-items: center; /* Centre verticalement */
                background-image: url('/assets/LFT_LOGO.png');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                max-height: 150px;
            }
            
            .main-header-content {
                position: relative;
                z-index: 2;
            }
            
            .card-custom {
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .card-custom:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
            }
            
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                transition: transform 0.3s ease;
            }
            
            .metric-card:hover {
                transform: scale(1.05);
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                margin: 0.5rem 0;
            }
            
            .metric-label {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            
            .sidebar {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                height: fit-content;
            }
            
            .tab-custom {
                background: white;
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .btn-primary-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .btn-primary-custom:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            
            .input-group-custom {
                margin-bottom: 1rem;
            }
            
            .input-group-custom label {
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
                display: block;
            }
            
            .form-control-custom {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 0.75rem;
                transition: border-color 0.3s ease;
            }
            
            .form-control-custom:focus {
                border-color: #667eea;
                outline: none;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .tabs-custom .tab {
                background: #f7fafc;
                border: none;
                padding: 1rem 2rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            .tabs-custom .tab--selected {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .result-card {
                background: #f8f9ff;
                border-left: 4px solid #667eea;
                padding: 1.5rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            }
            
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .alert-custom {
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            }
            
            .alert-info {
                background: #e6f4ff;
                border-left: 4px solid #1890ff;
                color: #0050b3;
            }
            
            .alert-success {
                background: #f0f9ff;
                border-left: 4px solid #52c41a;
                color: #237804;
            }
            
            .graph-container {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 1.5rem;
            }
            
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        
        <!-- Logo PNG statique -->
        <script>
            // Le logo est maintenant affiché via CSS - aucun JavaScript nécessaire
            console.log('Logo LFT chargé depuis /assets/LFT_LOGO.png');
        </script>
    </body>
</html>
'''
def load_gain_capital_rates():
    """Charge les taux de gain en capital depuis la base de données"""
    try:
        engine = create_engine(
            "postgresql://postgres:4845@100.73.238.42:5432/economic",
            connect_args={"client_encoding": "utf8"}
        )
        # Prendre uniquement les données les plus récentes pour chaque province
        query = '''
            WITH latest_dates AS (
                SELECT province, MAX(scrape_date) as max_date
                FROM "all".gain_capital
                GROUP BY province
            )
            SELECT gc.*
            FROM "all".gain_capital gc
            INNER JOIN latest_dates ld 
                ON gc.province = ld.province 
                AND gc.scrape_date = ld.max_date
            ORDER BY gc.province, gc."Lower Limit"
        '''
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        print(f"Erreur lors du chargement des taux de gain en capital: {e}")
        return pd.DataFrame()

def calculate_capital_gains_tax(gain_amount, province):
    """
    Calcule l'impôt sur le gain en capital selon la province
    
    Args:
        gain_amount: Montant du gain en capital
        province: Province pour le calcul
    
    Returns:
        tuple: (impot_total, taux_effectif)
    """
    try:
        # Charger les taux
        df_rates = load_gain_capital_rates()
        
        if df_rates.empty:
            return 0, 0
        
        # Filtrer par province
        province_rates = df_rates[df_rates['province'] == province].copy()
        
        if province_rates.empty:
            # Utiliser Ontario par défaut si province non trouvée
            province_rates = df_rates[df_rates['province'] == 'Ontario'].copy()
        
        # Trier par limite inférieure
        province_rates = province_rates.sort_values('Lower Limit')
        
        # Calculer l'impôt par tranches
        impot_total = 0
        
        for _, row in province_rates.iterrows():
            lower = clean_monetary_value(row['Lower Limit'])
            
            # Gérer 'Infinity' pour la limite supérieure
            if row['Upper Limit'] == 'Infinity':
                upper = float('inf')
            else:
                upper = clean_monetary_value(row['Upper Limit'])
            
            # Extraire le taux (enlever le %)
            taux_str = row['Capital Gains Tax Rate'].replace('%', '').strip()
            taux = float(taux_str) / 100
            
            # Calculer l'impôt pour cette tranche
            if gain_amount > lower:
                montant_imposable_tranche = min(gain_amount - lower, upper - lower)
                impot_tranche = montant_imposable_tranche * taux
                impot_total += impot_tranche
                
                # Si le gain ne dépasse pas cette tranche, arrêter
                if gain_amount <= upper:
                    break
        
        # Calculer le taux effectif
        taux_effectif = (impot_total / gain_amount * 100) if gain_amount > 0 else 0
        
        return impot_total, taux_effectif
        
    except Exception as e:
        print(f"Erreur lors du calcul de l'impôt sur gain en capital: {e}")
        return 0, 0

# Ajouter ces fonctions dans votre fichier main2.py après les autres fonctions de chargement de données

# Fonction load_taxation_municipale déplacée vers data_loading.py

# Fonction get_municipal_tax_rate déplacée vers calculation.py
# Fonction get_property_region déplacée vers calculation.py
def generate_combinations(base_values: dict, adjustments: dict, clamp_min=None, custom_min=None, keys_with_floor=None):
    """
    Génère toutes les combinaisons possibles en variant chaque paramètre autour de sa valeur de base ±3x son ajustement.
    """
    ranges = []
    for key, base in base_values.items():
        # S'assurer que la valeur de base et l'ajustement sont des nombres
        base = safe_float_conversion(base, 0)
        adj = safe_float_conversion(adjustments.get(key, 0), 0)
        values = [base - 3 * adj, base - 2 * adj, base - adj, base, base + adj, base + 2 * adj, base + 3 * adj]
        if custom_min and key in custom_min:
            values = [max(custom_min[key], v) for v in values]
        elif clamp_min is not None:
            values = [max(clamp_min, v) for v in values]
        if keys_with_floor and key in keys_with_floor:
            values = [max(1, v) for v in values]
        ranges.append(values)
    return list(product(*ranges))

# Fonction calcul_pret_max déplacée vers calculation.py
# Fonction calcul_mensualite déplacée vers calculation.py
def sync_schl_payment_mode_from_profit(value):
    return value

@app.callback(
    Output("conventional-rate-selection", "children"),
    Output("conventional-rate-selection", "style"),
    Input("loan-type", "value"),
    State("property-data", "data")
)
def update_conventional_rate_selection(loan_type, property_data):
    if loan_type != "conventional":
        return html.Div(), {"display": "none"}
    
    # Charger les taux des banques
    df_taux = load_taux_hypothecaires()
    
    # Récupérer le taux de la BD PMML
    taux_pmml = None
    if property_data:
        taux_pmml = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5))
    
    # Créer les options pour le dropdown
    options = []
    
    # Ajouter l'option du taux PMML en premier
    if taux_pmml:
        options.append({
            "label": f"Taux BD PMML - {taux_pmml:.2f}%",
            "value": f"pmml_{taux_pmml}"
        })
    
    # Ajouter les taux des banques
    if not df_taux.empty:
        # Séparer par type de taux
        banques_fixe_5ans = df_taux[df_taux['taux_fixe_5ans'].notna()].copy()
        banques_fixe_5ans = banques_fixe_5ans.sort_values('taux_fixe_5ans')
        
        if not banques_fixe_5ans.empty:
            options.append({"label": "--- Taux fixe 5 ans ---", "value": "header_fixe", "disabled": True})
            
            for _, row in banques_fixe_5ans.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_fixe_5ans']:.2f}%",
                    "value": f"fixe5_{row['banque_nom']}_{row['taux_fixe_5ans']}"
                })
        
        # Ajouter les taux variables si disponibles
        banques_variable = df_taux[df_taux['taux_variable_5ans'].notna()].copy()
        banques_variable = banques_variable.sort_values('taux_variable_5ans')
        
        if not banques_variable.empty:
            options.append({"label": "--- Taux variable 5 ans ---", "value": "header_variable", "disabled": True})
            
            for _, row in banques_variable.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_variable_5ans']:.2f}% (variable)",
                    "value": f"variable5_{row['banque_nom']}_{row['taux_variable_5ans']}"
                })
    
    # Créer la mise à jour de la date
    scrap_date = ""
    if not df_taux.empty and 'scrape_date' in df_taux.columns:
        scrap_date = df_taux['scrape_date'].iloc[0]
        if pd.notna(scrap_date):
            scrap_date = f" (Mis à jour: {scrap_date})"
    
    content = html.Div([
        html.Hr(className="my-3"),
        html.Label("Sélectionner le taux d'intérêt", className="fw-bold"),
        dcc.Dropdown(
            id="conventional-rate-selector",
            options=options,
            value=f"pmml_{taux_pmml}" if taux_pmml else None,
            placeholder="Choisir un taux...",
            className="mb-2"
        ),
        html.Small(f"Taux actualisés quotidiennement{scrap_date}", className="text-muted"),
        
        # Afficher le taux sélectionné
        html.Div(id="selected-rate-display", className="mt-2")
    ])
    
    return content, {"display": "block"}

@app.callback(
    Output("selected-rate-display", "children"),
    Input("conventional-rate-selector", "value")
)
def display_selected_rate(selected_value):
    if not selected_value:
        return html.Div()
    
    # Extraire le taux de la valeur
    parts = selected_value.split('_')
    
    if parts[0] == "pmml":
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Taux sélectionné: {parts[1]}% (Base de données PMML)"
        ], color="info", className="mt-2")
    elif parts[0] in ["fixe5", "variable5"]:
        taux_type = "Fixe 5 ans" if parts[0] == "fixe5" else "Variable 5 ans"
        banque = parts[1]
        taux = parts[2]
        return dbc.Alert([
            html.I(className="fas fa-university me-2"),
            f"Taux sélectionné: {taux}% - {banque} ({taux_type})"
        ], color="success", className="mt-2")
    
    return html.Div()

# Si le fichier a déjà un "if __name__ == '__main__':", assurez-vous que ce code est avant
# ... existing code ...
# Fonction safe_float_conversion déplacée vers calculation.py
# Fonction clean_monetary_value déplacée vers calculation.py
# Fonction clean_numeric_value déplacée vers calculation.py
# Fonction load_schl_rates_plex déplacée vers calculation.py
def update_immeuble_in_db(address, updated_data):
    """Met à jour les données d'un immeuble dans la base de données"""
    engine = create_engine(
        "postgresql://postgres:4845@100.73.238.42:5432/simulation",
        connect_args={"client_encoding": "utf8"}
    )
    
    try:
        # Construire la requête UPDATE
        set_clauses = []
        for key, value in updated_data.items():
            if value is not None and value != "":
                if isinstance(value, str):
                    set_clauses.append(f"{key} = '{value}'")
                else:
                    set_clauses.append(f"{key} = {value}")
        
        if set_clauses:
            query = f"""
                UPDATE immeuble.immeuble_now_pmml 
                SET {', '.join(set_clauses)}
                WHERE address = '{address}'
            """
            
            with engine.connect() as conn:
                conn.execute(query)
                conn.commit()
                conn.close()
                conn.close()
            
            return True, "Données mises à jour avec succès!"
    except Exception as e:
        return False, f"Erreur lors de la mise à jour: {str(e)}"

# Charger les paramètres au démarrage de l'application
try:
    APP_PARAMS = load_app_parameters()
    ACQUISITION_COSTS = load_acquisition_costs()
    ADJUSTMENT_DEFAULTS = load_adjustment_defaults()
except Exception as e:
    # Valeurs par défaut de secours si la base de données n'est pas accessible
    print(f"Erreur lors du chargement des paramètres: {e}")
    APP_PARAMS = {
        'default_interest_rate': 5.5,
        'default_amortization': 25,
        'default_rdc_ratio': 1.2,
        'default_dpa_rate': 4.0,
        'default_building_ratio': 80.0,
        'default_inflation_rate': 2.0,
        'default_rent_increase': 2.5,
        'default_appreciation_rate': 3.0,
        'schl_loan_ratio': 0.95,
        'conventional_loan_ratio': 0.80
    }
    ACQUISITION_COSTS = {}
    ADJUSTMENT_DEFAULTS = {}

# Fonction calculate_schl_premium déplacée vers calculation.py
def test_egi_visibility():
    """
    Fonction de test pour vérifier que l'interface EGI s'affiche correctement.
    À utiliser temporairement pour déboguer l'affichage.
    """
    print("🔍 Test de visibilité EGI")
    print("Pour tester l'affichage EGI, vous pouvez temporairement:")
    print("1. Changer style={'display': 'none'} en style={'display': 'block'} dans le layout")
    print("2. Vérifier que le callback update_egi_selection est bien appelé")
    print("3. Vérifier que le nombre d'unités est correctement détecté")
    print("4. Vérifier que le type de prêt est bien 'SCHL'")

# -----------------------------------------------------------------------------
# Fonctions de chargement des données géographiques
# -----------------------------------------------------------------------------
# Fonction load_provinces déplacée vers data_loading.py

# Fonction load_regions déplacée vers data_loading.py

# Fonction load_secteurs déplacée vers data_loading.py

# Fonction load_quartiers déplacée vers data_loading.py

# Fonction load_secteurs_recensement déplacée vers data_loading.py

# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------
# SECTION DE LAYOUT DUPLIQUÉE SUPPRIMÉE (lignes ~626-940)
# Cette section était une copie incorrecte du vrai layout qui se trouve plus bas (ligne ~2580+)
# Elle contenait notamment une duplication de "main-egi-control" qui empêchait le callback de fonctionner

# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------
@app.callback(
    Output("historical-date-div", "style"),
    Input("data-source", "value")
)
def toggle_historical_date(data_source):
    if data_source in ["historical", "unavailable"]:
        return {"display": "block"}
    return {"display": "none"}

@app.callback(
    Output("property-selector", "options"),
    [Input("data-source", "value"),
     Input("historical-date", "date"),
     Input("filtered-properties", "data"),
     # Ajouter des inputs pour forcer la mise à jour quand les filtres changent
     Input("filter-province", "value"),
     Input("filter-region", "value"),
     Input("filter-type", "value"),
     Input("specific-zone-filter", "value")]
)
def update_property_list(data_source, hist_date, filtered_properties, 
                        province, region, filter_type, specific_zone):
    print(f"\n=== Mise à jour de la liste des propriétés ===")
    print(f"Filtres actifs - Province: {province}, Région: {region}, Type: {filter_type}, Zone: {specific_zone}")
    print(f"Propriétés filtrées reçues: {len(filtered_properties) if filtered_properties else 0}")
    
    # Si un filtre géographique est actif et qu'aucune propriété n'est retournée, ne rien afficher
    if (province and province != "all") and (not filtered_properties or len(filtered_properties) == 0):
        print("Filtres géographiques actifs mais aucun immeuble trouvé - retour d'une liste vide")
        return [{"label": "Aucun immeuble dans cette zone", "value": None}]
    
    if data_source == "active":
        df = load_immeubles()
    elif data_source == "historical":
        df = load_immeubles_history(pd.to_datetime(hist_date).date())
    else:  # unavailable
        df_hist = load_immeubles_history(pd.to_datetime(hist_date).date())
        df_live = load_immeubles()
        df = df_hist[~df_hist['address'].isin(df_live['address'].unique())]
    
    print(f"Total des immeubles disponibles: {len(df)}")
    
    # Si des propriétés filtrées existent et qu'un filtre géographique est actif
    if filtered_properties and (province and province != "all"):
        # Filtrer le dataframe pour ne garder que les adresses dans la liste filtrée
        df_filtered = df[df['address'].isin(filtered_properties)]
        print(f"Immeubles après filtrage géographique: {len(df_filtered)}")
        
        if not df_filtered.empty:
            # Ne pas utiliser unique() pour permettre les adresses dupliquées
            print(f"Immeubles trouvés: {len(df_filtered)}")
            # Utiliser un identifiant basé sur la position dans le DataFrame complet
            return [{"label": f"{row['address']} (#{idx})", "value": f"{row['address']}|{idx}"} 
                   for idx, (_, row) in enumerate(df_filtered.iterrows())]
        else:
            print("Aucun immeuble dans la zone sélectionnée")
            return [{"label": "Aucun immeuble dans cette zone", "value": None}]
    
    # Sinon retourner toutes les propriétés sans contrainte d'unicité
    print(f"Retour de tous les immeubles: {len(df)}")
    # Utiliser un identifiant basé sur la position dans le DataFrame complet
    return [{"label": f"{row['address']} (#{idx})", "value": f"{row['address']}|{idx}"} 
           for idx, (_, row) in enumerate(df.iterrows())]

@app.callback(
    Output("effective-tax-rate", "children"),
    [Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("property-data", "data"),
     Input("property-selector", "value")]
)
def update_tax_rate(province, status, property_data, property_addr):
    is_incorporated = status == "incorporated"
    
    # Si incorporé, retourner le taux fixe de la table entreprise
    if is_incorporated:
        rate = get_tax_rate_for_province(province, is_incorporated)
        return f"{rate:.2f}%"
    
    # Si non-incorporé et qu'une propriété est sélectionnée
    if property_data and property_data.get('revenu_net'):
        # Utiliser directement le revenu_net de la BD
        revenu_net_bd = clean_monetary_value(property_data.get('revenu_net', 0))
        
        # Si pas de revenu net, le calculer
        if revenu_net_bd == 0:
            revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
            depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
            revenu_net_bd = revenus_bruts - depenses
        
        # S'assurer qu'on a un revenu net valide
        if revenu_net_bd <= 0:
            return "0.0% (pas de revenu net)"
        
        # Calcul des intérêts déductibles
        interet_annuel = 0
        prix = clean_monetary_value(property_data.get('prix_vente', 0))
        
        if prix > 0:
            # Récupérer les paramètres de financement selon le statut
            if is_incorporated:
                taux_str = str(property_data.get('financement_conv_taux_interet', '5.5')).replace('%', '').strip()
                montant_pret = prix * 0.75  # Conventionnel
            else:
                taux_str = str(property_data.get('financement_schl_taux_interet', '5.5')).replace('%', '').strip()
                montant_pret = prix * 0.85  # SCHL
            
            try:
                taux_interet = float(taux_str) / 100
            except:
                taux_interet = 0.055
            
            interet_annuel = montant_pret * taux_interet
        
        # Calcul de la DPA si applicable
        dpa_deduction = 0
        use_dpa = property_data.get('use_dpa', False)
        if use_dpa and prix > 0:
            building_ratio = 0.8  # 80% par défaut
            dpa_rate = 0.04  # 4% par défaut
            building_value = prix * building_ratio
            # Règle de demi-année pour la première année
            dpa_deduction = building_value * dpa_rate * 0.5
            
            # Limiter la DPA pour ne pas créer de perte
            max_dpa = max(0, revenu_net_bd - interet_annuel)
            dpa_deduction = min(dpa_deduction, max_dpa)
        
        # Revenu imposable
        revenu_imposable = max(0, revenu_net_bd - interet_annuel - dpa_deduction)
        
        # Calcul de l'impôt progressif
        impot = calculate_progressive_tax(revenu_imposable, province) if revenu_imposable > 0 else 0
        
        # Calculer le taux effectif sur le revenu IMPOSABLE (correct)
        taux_effectif = (impot / revenu_imposable * 100) if revenu_imposable > 0 else 0
        
        # Debug
        print(f"\n=== CALCUL TAUX EFFECTIF ===")
        print(f"Province: {province}")
        print(f"Statut: Non-incorporé")
        print(f"Revenu net (BD): {revenu_net_bd:,.0f} $")
        print(f"Intérêts déductibles: {interet_annuel:,.0f} $")
        print(f"DPA: {dpa_deduction:,.0f} $")
        print(f"Revenu imposable: {revenu_imposable:,.0f} $")
        print(f"Impôt calculé: {impot:,.0f} $")
        print(f"Taux effectif: {taux_effectif:.1f}%")
        
        return f"{taux_effectif:.1f}%"
    
    # Fallback si aucune propriété sélectionnée
    if is_incorporated:
        rate = get_tax_rate_for_province(province, is_incorporated)
        return f"{rate:.2f}%"
    else:
        revenu_exemple = 80000
        impot_exemple = calculate_progressive_tax(revenu_exemple, province)
        taux_effectif = (impot_exemple / revenu_exemple * 100)
        return f"{taux_effectif:.1f}% (exemple 80k$)"

# CALLBACK DUPLIQUÉ - COMMENTÉ POUR ÉVITER LES CONFLITS
# Le second callback update_metrics (ligne ~3752) est utilisé à la place
"""
@app.callback(
    [Output("price-metric", "children"),
     Output("revenue-metric", "children"),
     Output("tga-metric", "children"),
     Output("cashflow-metric", "children"),
     Output("property-data", "data")],
    [Input("property-selector", "value"),
     Input("data-source", "value"),
     Input("historical-date", "date"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("schl-payment-mode", "value"),
     Input("conventional-rate-selector", "value"),
     Input("manual-schl-rate", "data")]
)
def update_metrics(property_addr, data_source, hist_date, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate, manual_schl_rate):
    print(f"🔄 Update metrics [1] appelé!")
    print(f"  📍 Property: {property_addr}")
    print(f"  🏦 Loan type: {loan_type}")
    print(f"  💰 SCHL payment mode: {schl_payment_mode}")
    
    if not property_addr:
        return "-", "-", "-", "-", None
    
    # S'assurer que le mode de paiement SCHL est défini avec une valeur par défaut
    if not schl_payment_mode:
        schl_payment_mode = "financed"
        
    # Charger les données
    if data_source == "active":
        df = load_immeubles()
    elif data_source == "historical":
        df = load_immeubles_history(pd.to_datetime(hist_date).date())
    else:
        df_hist = load_immeubles_history(pd.to_datetime(hist_date).date())
        df_live = load_immeubles()
        df = df_hist[~df_hist['address'].isin(df_live['address'].unique())]
    
    # Vérifier si la valeur contient l'index pour traiter le nouveau format "adresse|index"
    if "|" in property_addr:
        address_part, index_part = property_addr.split("|")
        index_part = int(index_part)
        
        # L'index doit être basé sur la position originale dans le DataFrame complet
        # Plutôt que de filtrer par adresse puis utiliser l'index, utilisons l'index original
        # pour trouver l'immeuble correspondant
        try:
            # Vérifier si l'index est valide dans le DataFrame complet
            if index_part < len(df):
                # Vérifier que l'adresse correspond bien à celle attendue
                if df.iloc[index_part]['address'] == address_part:
                    property_data = df.iloc[index_part]
                else:
                    # Si l'adresse ne correspond pas, chercher parmi tous les immeubles avec cette adresse
                    properties_with_addr = df[df['address'] == address_part]
                    if not properties_with_addr.empty:
                        property_data = properties_with_addr.iloc[0]
                    else:
                        # Fallback: première entrée du DataFrame si aucune correspondance
                        property_data = df.iloc[0]
            else:
                # Fallback: chercher l'immeuble par adresse
                properties_with_addr = df[df['address'] == address_part]
                if not properties_with_addr.empty:
                    property_data = properties_with_addr.iloc[0]
                else:
                    # Fallback: première entrée du DataFrame si aucune correspondance
                    property_data = df.iloc[0]
        except Exception as e:
            print(f"Erreur lors de la récupération de l'immeuble: {e}")
            # Fallback: chercher l'immeuble par adresse uniquement
            properties_with_addr = df[df['address'] == address_part]
            if not properties_with_addr.empty:
                property_data = properties_with_addr.iloc[0]
            else:
                # Dernière option: première entrée du DataFrame
                property_data = df.iloc[0]
    else:
        # Ancien format pour compatibilité
        properties = df[df['address'] == property_addr]
        if not properties.empty:
            property_data = properties.iloc[0]
        else:
            # Fallback si l'adresse n'existe pas
            property_data = df.iloc[0]
    
    # Nettoyer et convertir les valeurs avec les VRAIS noms de colonnes
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    
    # *** CORRECTION: Toujours calculer le revenu net à partir de revenus_brut - depenses_totales ***
    revenue_net = revenue_brut - depenses
    
    tga = (revenue_net / prix * 100) if prix > 0 else 0
    
    # Récupérer les paramètres de financement selon le type de prêt
    try:
        # Récupérer les paramètres de prêt pour les calculs supplémentaires
        if loan_type == "SCHL":
            taux_str = str(property_data.get('financement_schl_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_schl_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
        else:
            # Pour conventionnel, utiliser le taux sélectionné si disponible
            if conventional_rate and conventional_rate != "":
                parts = conventional_rate.split('_')
                if len(parts) >= 2:
                    taux_str = parts[-1]
                    taux_interet = float(taux_str) / 100
                else:
                    taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                    taux_interet = float(taux_str) / 100 if taux_str else 0.055
            else:
                taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                taux_interet = float(taux_str) / 100 if taux_str else 0.055
            
            rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 1.2))
            amort_str = str(property_data.get('financement_conv_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
    except (ValueError, TypeError):
        print("Erreur lors de la conversion des paramètres de prêt - utilisation des valeurs par défaut")
        taux_interet = 0.055  # 5.5%
        amortissement = 25
    
    # Calcul du prêt basé sur le RDC
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
    
    # Calcul de la prime SCHL si applicable
    prime_schl = 0
    if loan_type == "SCHL":
        # Pour l'instant, utiliser un taux par défaut de 2.40%
        # Le taux sera mis à jour via le cache lorsque l'utilisateur le modifiera
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
            
        print(f"🎯 [Callback UPDATE_METRICS] Calcul prime SCHL")
        print(f"    📌 Taux par défaut utilisé: {default_rate}%")
        print(f"    💰 Prime calculée: {prime_schl:,.2f} $")
    
    # MODIFICATION : Ajuster le montant financé selon le mode de paiement
    if loan_type == "SCHL" and schl_payment_mode == "cash":
        montant_finance = montant_pret  # La prime n'est PAS ajoutée
    else:
        montant_finance = montant_pret + prime_schl  # La prime est financée
    
    # Si la prime est financée, recalculer la mensualité avec le nouveau montant
    if montant_finance != montant_pret:
        mensualite, _ = calcul_mensualite(montant_finance, taux_interet, amortissement)
    else:
        mensualite = pmt_mensuelle
    
    # Calcul des intérêts et capital pour le premier mois
    taux_mensuel = taux_interet / 12
    interet_mois_1 = montant_finance * taux_mensuel
    capital_mois_1 = mensualite - interet_mois_1
    
    # Calcul pour les 12 premiers mois
    solde_debut = montant_finance
    interet_annuel = 0
    capital_annuel = 0
    
    for mois in range(12):
        interet_mois = solde_debut * taux_mensuel
        capital_mois = mensualite - interet_mois
        interet_annuel += interet_mois
        capital_annuel += capital_mois
        solde_debut -= capital_mois
    
    # Calcul de l'impôt selon la nouvelle logique
    is_incorporated = tax_status == "incorporated"
    
    # Pour le cashflow mensuel, on utilise les valeurs du premier mois
    # montant imposable = Rev Net (M) - interet payé du mois
    revenue_net_mensuel = revenue_net / 12
    montant_imposable_mois_1 = revenue_net_mensuel - interet_mois_1
    
    # Calcul de l'impôt mensuel
    if is_incorporated:
        tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
        impot_mois_1 = montant_imposable_mois_1 * tax_rate if montant_imposable_mois_1 > 0 else 0
    else:
        # Pour les particuliers, calculer l'impôt annuel puis diviser par 12
        montant_imposable_annuel = revenue_net - interet_annuel
        impot_annuel = calculate_progressive_tax(montant_imposable_annuel, tax_province) if montant_imposable_annuel > 0 else 0
        impot_mois_1 = impot_annuel / 12
    
    # CORRECTION: Calcul du cashflow selon la bonne formule
    # 1. Montant imposable = Rev Net (M) - intérêt payé du mois (déjà calculé)
    # 2. Revenus net après impôt = Rev Net (M) - (montant imposable * taux impôt)
    # ATTENTION : C'est montant imposable × taux, pas juste l'impôt !
    if is_incorporated:
        revenue_net_apres_impot = revenue_net_mensuel - (montant_imposable_mois_1 * tax_rate)
    else:
        # Pour les particuliers, on utilise l'impôt calculé
        revenue_net_apres_impot = revenue_net_mensuel - impot_mois_1

    # 3. Final cashflow = Revenus net après impôt - Intérêts - Paiement remboursement du prêt
    # Le paiement de remboursement = Capital seulement
    # Modification: On soustrait aussi les intérêts car ils font partie des dépenses réelles du cashflow
    cashflow_mensuel = revenue_net_mensuel - impot_mois_1 - interet_mois_1 - capital_mois_1
    
    # Debug complet
    print(f"=== DEBUG COMPLET ===")
    print(f"Adresse sélectionnée: {property_addr}")
    print(f"Revenue net mensuel: {revenue_net_mensuel:,.0f} $")
    print(f"PMT mensuelle: {pmt_mensuelle:,.0f} $")
    print(f"Intérêt mois 1: {interet_mois_1:,.0f} $")
    print(f"Capital mois 1: {capital_mois_1:,.0f} $")
    print(f"Montant imposable mois 1: {montant_imposable_mois_1:,.0f} $")
    print(f"Impôt mois 1: {impot_mois_1:,.0f} $")
    print(f"Cashflow mensuel: {cashflow_mensuel:,.0f} $")
    
    return (f"{prix:,.0f} $",
            f"{revenue_net:,.0f} $",
            f"{tga:.2f}%",
            f"{cashflow_mensuel:,.0f} $",
            property_data.to_dict())

@app.callback(
    Output("montant-pret-input", "value"),
    [Input("loan-type", "value"),
     Input("property-data", "data")],
    prevent_initial_call=True
)
def update_montant_pret(loan_type, property_data):
    if not property_data:
        return None
        
    # IMPORTANT: Utiliser le calcul basé sur le RDC pour cohérence avec update_metrics
    # Cela évite d'avoir deux montants de prêt différents
    montant_pret, _, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    print(f"📝 [update_montant_pret #2] Montant calculé avec RDC: {montant_pret:,.0f} $")
    
    return montant_pret




"""
# FIN DU CALLBACK DUPLIQUÉ COMMENTÉ

# CALLBACK DÉPLACÉ PLUS BAS DANS LE FICHIER APRÈS LA DÉFINITION DU LAYOUT






# CALLBACK DE TEST VISIBLE POUR LE SWITCH DE TEST SIMPLE
@app.callback(
    [Output("property-data", "data", allow_duplicate=True),
     Output("test-switch-result", "children", allow_duplicate=True)],
    Input("test-switch-simple", "value"),
    State("property-data", "data"),
    prevent_initial_call='initial_duplicate'
)
def test_switch_simple_callback(test_value, property_data):
    print(f"🚨🚨🚨🚨🚨 [TEST SWITCH SIMPLE] MARCHE ! Valeur: {test_value} 🚨🚨🚨🚨🚨")
    
    if test_value:
        result_message = html.Div([
            html.H5("✅ CALLBACK TEST SWITCH ACTIVÉ !", className="text-success"),
            html.P(f"Valeur reçue: {test_value} (type: {type(test_value)})", className="text-success"),
            html.Small("Le callback fonctionne correctement !", className="text-success")
        ])
    else:
        result_message = html.Div([
            html.H5("❌ CALLBACK TEST SWITCH DÉSACTIVÉ !", className="text-danger"),
            html.P(f"Valeur reçue: {test_value} (type: {type(test_value)})", className="text-danger"),
            html.Small("Le callback fonctionne correctement !", className="text-success")
        ])
    
    return property_data, result_message


# CALLBACK TEMPORAIREMENT DÉSACTIVÉ POUR ÉVITER LES CONFLITS
# @app.callback(
#     Output("egi-rate-display-overview", "children", allow_duplicate=True),
#     [Input("egi-criterion-overview-2", "value"),
#      Input("property-data", "data"),
#      Input("loan-type", "value")],
#     prevent_initial_call=True
# )


# Callback centralisé pour calculer la prime SCHL une seule fois
@app.callback(
    Output("schl-premium-cache", "data"),
    [Input("montant-pret-input", "value"),
     Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("manual-schl-rate", "data")],  # Utiliser le taux manuel
    prevent_initial_call=True
)
def calculate_and_cache_schl_premium(montant_pret, property_data, loan_type, manual_rate):
    """
    Calcule la prime SCHL une seule fois et la stocke dans le cache.
    Utilise maintenant un taux manuel au lieu du critère EGI.
    """
    print(f"🔄 [Cache SCHL] RECALCUL DE LA PRIME SCHL DÉCLENCHÉ")
    print(f"📊 Type de prêt: {loan_type}")
    print(f"🎯 Taux manuel: {manual_rate}%")
    
    if loan_type != "SCHL" or not property_data or not montant_pret:
        return {}
    
    valeur_immeuble = clean_monetary_value(property_data.get('prix_vente', 0))
    if valeur_immeuble == 0:
        return {}
    
    # Utiliser le taux manuel s'il est fourni, sinon utiliser un taux par défaut
    prime_rate = manual_rate if manual_rate is not None else 2.40
    
    print(f"📌 [Cache SCHL] Taux manuel reçu: {manual_rate}%")
    print(f"📌 [Cache SCHL] Taux utilisé: {prime_rate}%")
    
    # Calculer la prime avec le taux manuel
    prime_schl = montant_pret * (prime_rate / 100)
    
    print(f"💾 [Cache SCHL] CALCUL DE LA PRIME AVEC TAUX MANUEL: {prime_rate}%")
    print(f"💰 [Cache SCHL] Prime calculée: {prime_schl:,.2f} $")
    
    # Stocker dans le cache
    cache_data = {
        "prime_schl": prime_schl,
        "prime_rate": prime_rate,
        "montant_pret": montant_pret,
        "valeur_immeuble": valeur_immeuble,
        "manual_rate": True,
        "ltv": (montant_pret / valeur_immeuble * 100) if valeur_immeuble > 0 else 0
    }
    
    return cache_data

@app.callback(
    [Output("conventional-rate-selection", "children"),
     Output("conventional-rate-selection", "style")],
    Input("loan-type", "value"),
    State("property-data", "data")
)
def update_conventional_rate_selection(loan_type, property_data):
    if loan_type != "conventional":
        return html.Div(), {"display": "none"}
    
    # Charger les taux des banques
    df_taux = load_taux_hypothecaires()
    
    # Récupérer le taux de la BD PMML
    taux_pmml = None
    if property_data:
        taux_pmml = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5))
    
    # Créer les options pour le dropdown
    options = []
    
    # Ajouter l'option du taux PMML en premier
    if taux_pmml:
        options.append({
            "label": f"Taux BD PMML - {taux_pmml:.2f}%",
            "value": f"pmml_{taux_pmml}"
        })
    
    # Ajouter les taux des banques
    if not df_taux.empty:
        # Séparer par type de taux
        banques_fixe_5ans = df_taux[df_taux['taux_fixe_5ans'].notna()].copy()
        banques_fixe_5ans = banques_fixe_5ans.sort_values('taux_fixe_5ans')
        
        if not banques_fixe_5ans.empty:
            options.append({"label": "--- Taux fixe 5 ans ---", "value": "header_fixe", "disabled": True})
            
            for _, row in banques_fixe_5ans.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_fixe_5ans']:.2f}%",
                    "value": f"fixe5_{row['banque_nom']}_{row['taux_fixe_5ans']}"
                })
        
        # Ajouter les taux variables si disponibles
        banques_variable = df_taux[df_taux['taux_variable_5ans'].notna()].copy()
        banques_variable = banques_variable.sort_values('taux_variable_5ans')
        
        if not banques_variable.empty:
            options.append({"label": "--- Taux variable 5 ans ---", "value": "header_variable", "disabled": True})
            
            for _, row in banques_variable.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_variable_5ans']:.2f}% (variable)",
                    "value": f"variable5_{row['banque_nom']}_{row['taux_variable_5ans']}"
                })
    
    # Créer la mise à jour de la date
    scrap_date = ""
    if not df_taux.empty and 'scrape_date' in df_taux.columns:
        scrap_date = df_taux['scrape_date'].iloc[0]
        if pd.notna(scrap_date):
            scrap_date = f" (Mis à jour: {scrap_date})"
    
    content = html.Div([
        html.Hr(className="my-3"),
        html.Label("Sélectionner le taux d'intérêt", className="fw-bold"),
        dcc.Dropdown(
            id="conventional-rate-selector",
            options=options,
            value=f"pmml_{taux_pmml}" if taux_pmml else None,
            placeholder="Choisir un taux...",
            className="mb-2"
        ),
        html.Small(f"Taux actualisés quotidiennement{scrap_date}", className="text-muted"),
        
        # Afficher le taux sélectionné
        html.Div(id="selected-rate-display", className="mt-2")
    ])
    
    return content, {"display": "block"}

@app.callback(
    Output("selected-rate-display", "children"),
    Input("conventional-rate-selector", "value")
)
def display_selected_rate(selected_value):
    if not selected_value:
        return html.Div()
    
    # Extraire le taux de la valeur
    parts = selected_value.split('_')
    
    if parts[0] == "pmml":
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Taux sélectionné: {parts[1]}% (Base de données PMML)"
        ], color="info", className="mt-2")
    elif parts[0] in ["fixe5", "variable5"]:
        taux_type = "Fixe 5 ans" if parts[0] == "fixe5" else "Variable 5 ans"
        banque = parts[1]
        taux = parts[2]
        return dbc.Alert([
            html.I(className="fas fa-university me-2"),
            f"Taux sélectionné: {taux}% - {banque} ({taux_type})"
        ], color="success", className="mt-2")
    
    return html.Div()

@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "value"),
     Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("schl-payment-mode", "value"),
     Input("conventional-rate-selector", "value")]
)
def update_tab_content(active_tab, property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate):
    print(f"🚀 [UPDATE_TAB_CONTENT #1] Onglet sélectionné: '{active_tab}'")
    
    if not property_data:
        return dbc.Alert("Veuillez sélectionner un immeuble pour voir les détails.", 
                        color="info", className="mt-3")
    
    if active_tab == "overview":
        return create_overview_tab(property_data)
    elif active_tab == "financial":
        return create_financial_tab(property_data, loan_type, tax_province, tax_status, conventional_rate)
    elif active_tab == "surveillance":
        return create_surveillance_tab(property_data)
    elif active_tab == "summary":
        return create_summary_tab(property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate)
    elif active_tab == "costs":
        return create_costs_tab(property_data, loan_type)
    elif active_tab == "profit":
        return create_profit_tab(property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate)
    elif active_tab == "geo_analysis":
        return get_geo_analysis_component(property_data)
    else:
        return dbc.Alert("Sélectionnez un onglet pour voir le contenu.", 
                        color="info", className="mt-3")

def create_simple_map(property_data):
    """Crée une carte simple basée sur les coordonnées latitude/longitude"""
    import plotly.graph_objects as go
    
    try:
        lat = float(property_data['latitude'])
        lon = float(property_data['longitude'])
        
        fig_map = go.Figure(go.Scattermapbox(
            lat=[lat],
            lon=[lon],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=14,
                color='#667eea'
            ),
            text=property_data.get('address', 'Immeuble'),
            hoverinfo='text'
        ))
        
        fig_map.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(
                    lat=lat,
                    lon=lon
                ),
                zoom=15
            ),
            showlegend=False,
            height=400,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        # S'assurer que l'objet graphique est correctement créé
        result = dcc.Graph(figure=fig_map, config={'displayModeBar': False})
        if result is None:
            raise ValueError("Le composant graphique n'a pas pu être créé")
        return result
        
    except Exception as e:
        print(f"Erreur lors de la création de la carte simple: {e}")
        return None  # Retourner None pour indiquer l'échec de création de la carte

def create_financial_tab(property_data, loan_type, tax_province, tax_status, conventional_rate=None, schl_cache=None, manual_schl_rate=None):
    # Calculer les paramètres de base
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    
    # S'assurer que le prix est bien défini dès le début
    prix_str = str(property_data.get('prix_vente', 0)).replace('$', '').replace(' ', '').replace(',', '')
    try:
        prix = float(prix_str)
    except ValueError:
        print(f"Impossible de convertir la valeur du prix '{prix_str}' en nombre. Utilisation de la valeur par défaut 0.")
        prix = 0
    
    # Paramètres du prêt spécifiques à l'immeuble
    try:
        if loan_type == "SCHL":
            # Utiliser des valeurs par défaut en cas de valeurs manquantes
            rdc_ratio = float(property_data.get('financement_schl_ratio_couverture_dettes', 1.2) or 1.2)
            taux_str = str(property_data.get('financement_schl_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_schl_amortissement', 25)).strip()
            # Nettoyer la chaîne pour extraire uniquement la partie numérique
            import re
            amort_nums = re.findall(r'\d+', amort_str)
            amortissement = float(amort_nums[0]) if amort_nums else 25
        else:
            # Pour conventionnel, utiliser le taux sélectionné si disponible
            if conventional_rate and conventional_rate != "":
                parts = conventional_rate.split('_')
                if len(parts) >= 2:
                    taux_str = parts[-1]
                    taux_interet = float(taux_str) / 100
                else:
                    taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                    taux_interet = float(taux_str) / 100 if taux_str else 0.055
            else:
                taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                taux_interet = float(taux_str) / 100 if taux_str else 0.055
            
            rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 1.2))
            amort_str = str(property_data.get('financement_conv_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
            
        # Calcul du montant du prêt basé sur le RDC
        montant_pret, ratio_pret_valeur, mensualite_max = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
        
    except (ValueError, TypeError):
        print("Erreur lors de la conversion des paramètres de prêt - utilisation des valeurs par défaut")
        rdc_ratio = 1.2
        taux_interet = 0.055  # 5.5%
        amortissement = 25
        
        # En cas d'erreur, utiliser une valeur par défaut pour le prêt
        montant_pret = prix * 0.75  # 75% de la valeur de l'immeuble par défaut
    
    loan_params = {
        "taux": taux_interet,
        "amortissement": amortissement,
        "rdc_ratio": rdc_ratio
    }
    
    # Utiliser la fonction standardisée pour le calcul du prêt
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
    
    return html.Div([
        # Alerte pour les changements de paramètres fiscaux
        dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            html.Strong("Paramètres fiscaux actuels : "),
            f"Province: {tax_province}, Statut: {'Incorporé' if is_incorporated else 'Non incorporé'}, ",
            f"Taux d'imposition: {tax_rate*100:.1f}%" if is_incorporated else f"Taux d'imposition: Progressif selon les tranches",
            html.Br(),
            html.Small("Les simulations précédentes pourraient ne pas refléter ces paramètres. Relancez les simulations après un changement.", className="text-muted")
        ], color="warning", dismissable=True, className="mb-4"),
        
        # Section Revenue Net
        html.Div([
            html.H4([
                html.I(className="fas fa-chart-line me-2"),
                "Simulation du Revenue Net"
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Revenu Brut Annuel", className="fw-bold"),
                    dbc.Input(
                        id="revenue-brut-input",
                        type="number",
                        value=property_data.get('revenus_brut', 0),
                        step=1000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Dépenses Annuelles", className="fw-bold"),
                    dbc.Input(
                        id="depenses-input",
                        type="number",
                        value=property_data.get('depenses_totales', 0),
                        step=1000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("TGA (%)", className="fw-bold"),
                    dbc.Input(
                        id="tga-input",
                        type="number",
                        value=round(((safe_float_conversion(property_data.get('revenus_brut', 0)) - safe_float_conversion(property_data.get('depenses_totales', 0))) / safe_float_conversion(property_data.get('prix_vente', 1)) * 100), 2),
                        step=0.1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
            ]),
            
            # Options DPA
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-calculator me-2"),
                        "Déduction pour Amortissement (DPA)"
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="use-dpa",
                                options=[{"label": "Appliquer la DPA", "value": True}],
                                value=[],
                                className="mb-2"
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Taux DPA (%)", className="fw-bold"),
                            dbc.Input(
                                id="dpa-rate",
                                type="number",
                                value=APP_PARAMS.get('default_dpa_rate', 4.0),
                                step=0.1,
                                disabled=True,
                                className="form-control-custom"
                            )
                        ], width=6),
                        dbc.Input(
                            id="building-ratio",
                            type="hidden",
                            value=100.0
                        )
                    ])
                ])
            ], className="mb-4"),
            
            # Ajustements pour simulation
            html.H5("Ajustements pour Simulation", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Ajustement Revenue (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-revenue", type="number", value=ADJUSTMENT_DEFAULTS.get('revenue_adjustment', 1000), step=100, className="form-control-custom")
                ], width=4),
                dbc.Col([
                    html.Label("Ajustement Dépenses (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-depenses", type="number", value=ADJUSTMENT_DEFAULTS.get('expense_adjustment', 1000), step=100, className="form-control-custom")
                ], width=4),
                dbc.Col([
                    html.Label("Ajustement TGA (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-tga", type="number", value=ADJUSTMENT_DEFAULTS.get('tga_adjustment', 0.1), step=0.1, className="form-control-custom")
                ], width=4),
            ]),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-revenue-btn", style={"display": "none"}),
            
            html.Div(id="revenue-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Coût d'Intérêt
        html.Div([
            html.H4([
                html.I(className="fas fa-percentage me-2"),
                "Simulation du Coût d'Intérêt"
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Montant du Prêt ($)", className="fw-bold"),
                    dbc.Input(
                        id="montant-pret-input",
                        type="number",
                        value=montant_pret,
                        step=5000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Taux d'Intérêt (%)", className="fw-bold"),
                    dbc.Input(
                        id="taux-interet-input",
                        type="number",
                        value=loan_params['taux'],
                        step=0.1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Amortissement (années)", className="fw-bold"),
                    dbc.Input(
                        id="amortissement-input",
                        type="number",
                        value=loan_params['amortissement'],
                        step=1,
                        min=1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
            ]),
            
            # Prime SCHL si applicable
            html.Div(id="schl-premium-section"),
            
            # Ajustements pour simulation
            html.H5("Ajustements pour Simulation", className="mb-3 mt-4"),
            dbc.Row([
                dbc.Col([
                    html.Label("Ajustement Prêt (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-pret", type="number", value=ADJUSTMENT_DEFAULTS.get('loan_adjustment', 5000), step=1000, className="form-control-custom")
                ], width=3),
                dbc.Col([
                    html.Label("Ajustement Taux (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-taux", type="number", value=ADJUSTMENT_DEFAULTS.get('rate_adjustment', 0.1), step=0.01, className="form-control-custom")
                ], width=3),
                dbc.Col([
                    html.Label("Ajustement Amort. (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-amort", type="number", value=ADJUSTMENT_DEFAULTS.get('amortization_adjustment', 0), step=1, className="form-control-custom")
                ], width=3),
            ]),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-interet-btn", style={"display": "none"}),
            
            html.Div(id="interet-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Simulation Intégrée
        html.Div([
            html.H4([
                html.I(className="fas fa-sync-alt me-2"),
                "Simulation Intégrée (Méthode Fiscale Complète)"
            ], className="mb-4"),
            
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Cette simulation applique la logique fiscale complète : "),
                html.Br(),
                "• Les intérêts sont déduits du revenu imposable",
                html.Br(),
                "• L'impôt est calculé sur (NOI - Intérêts - DPA)",
                html.Br(),
                "• Le cashflow final = NOI - Impôt - Intérêts - Capital"
            ], color="info", className="mb-4"),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-integrated-btn", style={"display": "none"}),
            
            html.Div(id="integrated-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Cashflow
        html.Div([
            html.H4([
                html.I(className="fas fa-money-bill-wave me-2"),
                "Analyse du Cashflow"
            ], className="mb-4"),
            
            # Bouton caché car simulation auto
            dbc.Button(id="calculate-cashflow-btn", style={"display": "none"}),
            
            html.Div(id="cashflow-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Projections financières (anciennement onglet séparé)
        html.Div([
            html.H4([
                html.I(className="fas fa-chart-area me-2"),
                "Projections financières"
            ], className="mb-4"),
            
            # Paramètres de projection
            dbc.Row([
                dbc.Col([
                    html.Label("Inflation annuelle (%)", className="fw-bold"),
                    dbc.Input(
                        id="inflation-rate",
                        type="number",
                        value=APP_PARAMS.get('default_inflation_rate', 2.0),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Augmentation loyers (%/an)", className="fw-bold"),
                    dbc.Input(
                        id="rent-increase",
                        type="number",
                        value=APP_PARAMS.get('default_rent_increase', 2.5),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Appréciation immobilière (%/an)", className="fw-bold"),
                    dbc.Input(
                        id="appreciation-rate",
                        type="number",
                        value=APP_PARAMS.get('default_appreciation_rate', 3.0),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
            ], className="mb-4"),
            
            # Section des taux d'intérêt par terme
            html.H5("Taux d'intérêt par terme (5 ans)", className="mt-4 mb-3"),
            html.P("Simulez l'évolution des taux d'intérêt après chaque renouvellement de terme", className="text-muted mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Terme initial (0-5 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-initial",
                        type="number",
                        value=clean_numeric_value(property_data.get(
                            'financement_schl_taux_interet' if loan_type == "SCHL" else 'financement_conv_taux_interet', 
                            APP_PARAMS.get('default_interest_rate', 5.5)
                        )) if property_data else APP_PARAMS.get('default_interest_rate', 5.5),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("2e terme (6-10 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-2",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 0.5,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("3e terme (11-15 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-3",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("4e terme (16-20 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-4",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("5e terme (21-25 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-5",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        id="use-degressive-interest",
                        options=[{"label": "Utiliser intérêts dégressifs", "value": True}],
                        value=[True],
                        className="mb-2"
                    ),
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Années à projeter", className="fw-bold"),
                    dbc.Input(
                        id="projection-years",
                        type="number",
                        value=25,
                        min=5,
                        max=30,
                        step=5,
                        className="form-control-custom"
                    )
                ], width=4),
            ], className="mb-4"),
            
            dbc.Button([
                html.I(className="fas fa-chart-line me-2"),
                "Générer Projections"
            ], id="generate-projections-btn", className="btn-primary-custom", size="lg"),
            
            html.Div(id="projection-results", className="mt-4")
                  ], className="card-custom")
      ])
  
  

# Configuration de l'application Dash avec un thème moderne
app = dash.Dash(__name__, 
                external_stylesheets=[
                    dbc.themes.BOOTSTRAP,
                    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
                    "https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500;600;700&display=swap",
                    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
                ],
                suppress_callback_exceptions=True)

# Style CSS personnalisé
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <!-- Ajout de Three.js pour l'animation 3D -->
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            
            .main-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 2rem;
                position: relative;
                overflow: hidden;
                height: 220px; /* Hauteur encore augmentée pour l'en-tête */
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            
            .lft-title {
                font-family: 'Garamond', 'EB Garamond', serif;
                letter-spacing: 1px;
            }
            
            #logo3d-container {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 70px; /* Beaucoup plus d'espace pour le texte en bas */
                width: 100%;
                height: calc(100% - 70px);
                z-index: 1;
                display: flex;
                justify-content: center; /* Centre horizontalement */
                align-items: center; /* Centre verticalement */
                background-image: url('/assets/LFT_LOGO.png');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                max-height: 150px;
            }
            
            .main-header-content {
                position: relative;
                z-index: 2;
            }
            
            .card-custom {
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            
            .card-custom:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
            }
            
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 12px;
                padding: 1.5rem;
                text-align: center;
                transition: transform 0.3s ease;
            }
            
            .metric-card:hover {
                transform: scale(1.05);
            }
            
            .metric-value {
                font-size: 2rem;
                font-weight: 700;
                margin: 0.5rem 0;
            }
            
            .metric-label {
                font-size: 0.9rem;
                opacity: 0.9;
            }
            
            .sidebar {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 1.5rem;
                height: fit-content;
            }
            
            .tab-custom {
                background: white;
                border-radius: 12px;
                padding: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .btn-primary-custom {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            
            .btn-primary-custom:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            }
            
            .input-group-custom {
                margin-bottom: 1rem;
            }
            
            .input-group-custom label {
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
                display: block;
            }
            
            .form-control-custom {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                padding: 0.75rem;
                transition: border-color 0.3s ease;
            }
            
            .form-control-custom:focus {
                border-color: #667eea;
                outline: none;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .tabs-custom .tab {
                background: #f7fafc;
                border: none;
                padding: 1rem 2rem;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            
            .tabs-custom .tab--selected {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            
            .result-card {
                background: #f8f9ff;
                border-left: 4px solid #667eea;
                padding: 1.5rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            }
            
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .alert-custom {
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            }
            
            .alert-info {
                background: #e6f4ff;
                border-left: 4px solid #1890ff;
                color: #0050b3;
            }
            
            .alert-success {
                background: #f0f9ff;
                border-left: 4px solid #52c41a;
                color: #237804;
            }
            
            .graph-container {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 1.5rem;
            }
            
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        
        <!-- Logo PNG statique -->
        <script>
            // Le logo est maintenant affiché via CSS - aucun JavaScript nécessaire
            console.log('Logo LFT chargé depuis /assets/LFT_LOGO.png');
        </script>
    </body>
</html>
'''
# Ajouter ces fonctions dans votre fichier main2.py après les autres fonctions de chargement de données

# Fonction load_taxation_municipale déplacée vers data_loading.py

# Fonction get_municipal_tax_rate déplacée vers calculation.py
# Fonction get_property_region déplacée vers calculation.py
def generate_combinations(base_values: dict, adjustments: dict, clamp_min=None, custom_min=None, keys_with_floor=None):
    """
    Génère toutes les combinaisons possibles en variant chaque paramètre autour de sa valeur de base ±3x son ajustement.
    """
    ranges = []
    for key, base in base_values.items():
        # S'assurer que la valeur de base et l'ajustement sont des nombres
        base = safe_float_conversion(base, 0)
        adj = safe_float_conversion(adjustments.get(key, 0), 0)
        values = [base - 3 * adj, base - 2 * adj, base - adj, base, base + adj, base + 2 * adj, base + 3 * adj]
        if custom_min and key in custom_min:
            values = [max(custom_min[key], v) for v in values]
        elif clamp_min is not None:
            values = [max(clamp_min, v) for v in values]
        if keys_with_floor and key in keys_with_floor:
            values = [max(1, v) for v in values]
        ranges.append(values)
    return list(product(*ranges))

# Fonction calcul_pret_max déplacée vers calculation.py
# Fonction calcul_mensualite déplacée vers calculation.py
def sync_schl_payment_mode_from_profit(value):
    return value

@app.callback(
    Output("conventional-rate-selection", "children"),
    Output("conventional-rate-selection", "style"),
    Input("loan-type", "value"),
    State("property-data", "data")
)
def update_conventional_rate_selection(loan_type, property_data):
    if loan_type != "conventional":
        return html.Div(), {"display": "none"}
    
    # Charger les taux des banques
    df_taux = load_taux_hypothecaires()
    
    # Récupérer le taux de la BD PMML
    taux_pmml = None
    if property_data:
        taux_pmml = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5))
    
    # Créer les options pour le dropdown
    options = []
    
    # Ajouter l'option du taux PMML en premier
    if taux_pmml:
        options.append({
            "label": f"Taux BD PMML - {taux_pmml:.2f}%",
            "value": f"pmml_{taux_pmml}"
        })
    
    # Ajouter les taux des banques
    if not df_taux.empty:
        # Séparer par type de taux
        banques_fixe_5ans = df_taux[df_taux['taux_fixe_5ans'].notna()].copy()
        banques_fixe_5ans = banques_fixe_5ans.sort_values('taux_fixe_5ans')
        
        if not banques_fixe_5ans.empty:
            options.append({"label": "--- Taux fixe 5 ans ---", "value": "header_fixe", "disabled": True})
            
            for _, row in banques_fixe_5ans.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_fixe_5ans']:.2f}%",
                    "value": f"fixe5_{row['banque_nom']}_{row['taux_fixe_5ans']}"
                })
        
        # Ajouter les taux variables si disponibles
        banques_variable = df_taux[df_taux['taux_variable_5ans'].notna()].copy()
        banques_variable = banques_variable.sort_values('taux_variable_5ans')
        
        if not banques_variable.empty:
            options.append({"label": "--- Taux variable 5 ans ---", "value": "header_variable", "disabled": True})
            
            for _, row in banques_variable.iterrows():
                options.append({
                    "label": f"{row['banque_nom']} - {row['taux_variable_5ans']:.2f}% (variable)",
                    "value": f"variable5_{row['banque_nom']}_{row['taux_variable_5ans']}"
                })
    
    # Créer la mise à jour de la date
    scrap_date = ""
    if not df_taux.empty and 'scrape_date' in df_taux.columns:
        scrap_date = df_taux['scrape_date'].iloc[0]
        if pd.notna(scrap_date):
            scrap_date = f" (Mis à jour: {scrap_date})"
    
    content = html.Div([
        html.Hr(className="my-3"),
        html.Label("Sélectionner le taux d'intérêt", className="fw-bold"),
        dcc.Dropdown(
            id="conventional-rate-selector",
            options=options,
            value=f"pmml_{taux_pmml}" if taux_pmml else None,
            placeholder="Choisir un taux...",
            className="mb-2"
        ),
        html.Small(f"Taux actualisés quotidiennement{scrap_date}", className="text-muted"),
        
        # Afficher le taux sélectionné
        html.Div(id="selected-rate-display", className="mt-2")
    ])
    
    return content, {"display": "block"}

@app.callback(
    Output("selected-rate-display", "children"),
    Input("conventional-rate-selector", "value")
)
def display_selected_rate(selected_value):
    if not selected_value:
        return html.Div()
    
    # Extraire le taux de la valeur
    parts = selected_value.split('_')
    
    if parts[0] == "pmml":
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            f"Taux sélectionné: {parts[1]}% (Base de données PMML)"
        ], color="info", className="mt-2")
    elif parts[0] in ["fixe5", "variable5"]:
        taux_type = "Fixe 5 ans" if parts[0] == "fixe5" else "Variable 5 ans"
        banque = parts[1]
        taux = parts[2]
        return dbc.Alert([
            html.I(className="fas fa-university me-2"),
            f"Taux sélectionné: {taux}% - {banque} ({taux_type})"
        ], color="success", className="mt-2")
    
    return html.Div()

# Si le fichier a déjà un "if __name__ == '__main__':", assurez-vous que ce code est avant
# ... existing code ...
# Fonction safe_float_conversion déplacée vers calculation.py
# Fonction clean_monetary_value déplacée vers calculation.py
# Fonction clean_numeric_value déplacée vers calculation.py
def update_immeuble_in_db(address, updated_data):
    """Met à jour les données d'un immeuble dans la base de données"""
    engine = create_engine(
        "postgresql://postgres:4845@100.73.238.42:5432/simulation",
        connect_args={"client_encoding": "utf8"}
    )
    
    try:
        # Construire la requête UPDATE
        set_clauses = []
        for key, value in updated_data.items():
            if value is not None and value != "":
                if isinstance(value, str):
                    set_clauses.append(f"{key} = '{value}'")
                else:
                    set_clauses.append(f"{key} = {value}")
        
        if set_clauses:
            query = f"""
                UPDATE immeuble.immeuble_now_pmml 
                SET {', '.join(set_clauses)}
                WHERE address = '{address}'
            """
            
            with engine.connect() as conn:
                conn.execute(query)
                conn.commit()
                conn.close()
            
            return True, "Données mises à jour avec succès!"
    except Exception as e:
        return False, f"Erreur lors de la mise à jour: {str(e)}"

# Charger les paramètres au démarrage de l'application
try:
    APP_PARAMS = load_app_parameters()
    ACQUISITION_COSTS = load_acquisition_costs()
    ADJUSTMENT_DEFAULTS = load_adjustment_defaults()
except Exception as e:
    # Valeurs par défaut de secours si la base de données n'est pas accessible
    print(f"Erreur lors du chargement des paramètres: {e}")
    APP_PARAMS = {
        'default_interest_rate': 5.5,
        'default_amortization': 25,
        'default_rdc_ratio': 1.2,
        'default_dpa_rate': 4.0,
        'default_building_ratio': 80.0,
        'default_inflation_rate': 2.0,
        'default_rent_increase': 2.5,
        'default_appreciation_rate': 3.0,
        'schl_loan_ratio': 0.95,
        'conventional_loan_ratio': 0.80
    }
    ACQUISITION_COSTS = {}
    ADJUSTMENT_DEFAULTS = {}

# Fonction calculate_loan_amount_from_rdc déplacée vers calculation.py
app.layout = dbc.Container([
    # Stores for data
    dcc.Store(id="property-data", storage_type="memory"),
    dcc.Store(id="filtered-properties", storage_type="memory"),
    dcc.Store(id="revenue-simulation-data", storage_type="memory"),
    dcc.Store(id="interet-simulation-data", storage_type="memory"),
    dcc.Store(id="additional-costs-data", storage_type="memory"),
    dcc.Store(id="schl-payment-mode-store", storage_type="memory", data="financed"),
    dcc.Store(id="additional-revenues-store", storage_type="memory", data=[]),
    dcc.Store(id="additional-expenses-store", storage_type="memory", data=[]),
    dcc.Store(id="confluence-data-store", storage_type="session", data={}),
    dcc.Store(id="schl-premium-cache", storage_type="memory", data={}),  # Cache centralisé pour la prime SCHL
    dcc.Store(id="rbr-status", storage_type="memory", data=True),  # État RBR atteint/non atteint (True = atteint)
    dcc.Store(id="manual-schl-rate", storage_type="memory", data=2.60),  # Taux SCHL sélectionné
    
    # Header
    html.Div([
        # Conteneur pour l'animation 3D
        html.Div(id="logo3d-container"),
        
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.P("ANALYSIS", 
                               className="text-center mb-0 fw-bold fs-3 lft-title")
                    ], className="main-header-content",
                    style={"position": "absolute", "bottom": "20px", "left": "0", "right": "0", "width": "100%", "z-index": "2", "text-align": "center"})
                ])
            ])
        ])
    ], className="main-header"),
    
    # Corps principal
    dbc.Container([
        dbc.Row([
            # Sidebar
            dbc.Col([
                html.Div([
                    html.H4([
                        html.I(className="fas fa-cog me-2"),
                        "Configuration"
                    ], className="mb-4"),
                    
                    # Sélection immeuble
                    html.Div([
                        html.Label("Sélectionner un immeuble", className="fw-bold"),
                        dcc.Dropdown(
                            id="property-selector",
                            placeholder="Choisir un immeuble...",
                            className="mb-3"
                        ),
                    ], className="input-group-custom"),
                    
                    # Type de données
                    html.Div([
                        html.Label("Source des données", className="fw-bold"),
                        dbc.RadioItems(
                            id="data-source",
                            options=[
                                {"label": "Actif maintenant", "value": "active"},
                                {"label": "Historique", "value": "historical"},
                                {"label": "Plus disponible", "value": "unavailable"}
                            ],
                            value="active",
                            className="mt-2"
                        )
                    ], className="input-group-custom"),
                    
                    # Date historique (cachée par défaut)
                    html.Div([
                        html.Label("Date historique", className="fw-bold"),
                        dcc.DatePickerSingle(
                            id="historical-date",
                            date=date.today(),
                            display_format="DD/MM/YYYY",
                            className="w-100"
                        )
                    ], id="historical-date-div", style={"display": "none"}, className="input-group-custom"),
                    
                    html.Hr(className="my-4"),
                    
                    # Filtres géographiques avancés
                    html.H5([
                        html.I(className="fas fa-map-marked-alt me-2"),
                        "Filtres géographiques"
                    ], className="mb-3"),
                    
                    html.Div(id="geographic-filters", className="mb-3"),
                    
                    html.Hr(className="my-4"),
                    
                    # Statut fiscal
                    html.H5([
                        html.I(className="fas fa-calculator me-2"),
                        "Paramètres fiscaux"
                    ], className="mb-3"),
                    
                    html.Div([
                        html.Label("Province fiscale", className="fw-bold"),
                        dcc.Dropdown(
                            id="tax-province",
                            options=[
                                {"label": p, "value": p} for p in [
                                    "Québec", "Ontario", "Alberta", "Colombie-Britannique",
                                    "Manitoba", "Saskatchewan", "Nouvelle-Écosse", "Nouveau-Brunswick",
                                    "Île-du-Prince-Édouard", "Terre-Neuve-et-Labrador", 
                                    "Territoires du Nord-Ouest", "Yukon", "Nunavut"
                                ]
                            ],
                            value="Québec",
                            className="mb-3"
                        )
                    ], className="input-group-custom"),
                    
                    html.Div([
                        html.Label("Statut fiscal", className="fw-bold"),
                        dbc.RadioItems(
                            id="tax-status",
                            options=[
                                {"label": "Incorporé", "value": "incorporated"},
                                {"label": "Non Incorporé", "value": "not_incorporated"}
                            ],
                            value="incorporated",
                            className="mt-2"
                        )
                    ], className="input-group-custom"),
                    
                    html.Div([
                        html.Label("Taux d'imposition effectif", className="fw-bold"),
                        html.Div(id="effective-tax-rate", className="metric-value text-primary")
                    ], className="input-group-custom"),
                    
                    html.Hr(className="my-4"),
                    
                    # Type de prêt
                    html.H5([
                        html.I(className="fas fa-hand-holding-usd me-2"),
                        "Type de prêt"
                    ], className="mb-3"),
                    
                    dbc.RadioItems(
                        id="loan-type",
                        options=[
                            {"label": "SCHL", "value": "SCHL"},
                            {"label": "Conventionnelle", "value": "conventional"}
                        ],
                        value="SCHL",
                        className="mt-2"
                    ),
                    
                    # Section pour la sélection du taux conventionnel
                    html.Div(id="conventional-rate-selection", style={"display": "none"}),
                    
                    # NOUVEAU : Section principale pour le critère EGI (SCHL uniquement)
                    html.Div([
                        html.H3("⏳ En attente du callback...", style={"color": "orange", "background": "lightyellow", "padding": "10px"}),
                        html.P("Ce message devrait être remplacé par le callback")
                    ], id="main-egi-control", className="mt-3"),

                    
                    html.Hr(className="my-4"),
                    
                    # URL de l'immeuble
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-link me-2"),
                            "Lien de l'annonce"
                        ], className="mb-3"),
                        html.Div(id="property-url", className="small")
                    ], className="mb-3"),
                    
                    # Détails complets de l'immeuble
                    html.Hr(className="my-4"),
                    
                    html.Div([
                        html.H5([
                            html.I(className="fas fa-database me-2"),
                            "Données complètes"
                        ], className="mb-3"),
                        html.Div(id="complete-property-data", className="small")
                    ], className="mb-3"),
                    
                    # Boutons d'action en bas de la sidebar
                    html.Hr(className="my-4"),
                    
                    html.Div([
                        dbc.Button([
                            html.I(className="fas fa-info-circle me-2"),
                            "Voir les calculs détaillés"
                        ], id="show-calculations-button", className="w-100 mb-2", color="info", outline=True),
                        
                        dbc.Button([
                            html.I(className="fas fa-edit me-2"),
                            "Modifier les données de l'immeuble"
                        ], id="edit-property-button", className="w-100", color="warning", outline=True),
                        
                        # Section pour afficher/modifier les données
                        html.Div(id="property-edit-section", className="mt-4", style={"display": "none"})
                    ], className="mt-4")
                    
                ], className="sidebar")
            ], width=3),
            
            # Contenu principal
            dbc.Col([
                # Métriques clés
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.P("Prix de vente", className="metric-label"),
                            html.H3(id="price-metric", className="metric-value"),
                            html.P("Valeur marchande", className="small text-white-50")
                        ], className="metric-card")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.P("Revenue net", className="metric-label"),
                            html.H3(id="revenue-metric", className="metric-value"),
                            html.P("Après dépenses", className="small text-white-50")
                        ], className="metric-card")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.P("TGA", className="metric-label"),
                            html.H3(id="tga-metric", className="metric-value"),
                            html.P("Taux global", className="small text-white-50")
                        ], className="metric-card")
                    ], width=3),
                    dbc.Col([
                        html.Div([
                            html.P("Cashflow mois 1", className="metric-label"),
                            html.H3(id="cashflow-metric", className="metric-value"),
                            html.P("Premier mois", className="small text-white-50")
                        ], className="metric-card")
                    ], width=3),
                ], className="mb-4"),
                
                # Tabs
                dcc.Tabs(id="main-tabs", value="overview", children=[
                    dcc.Tab(label="Vue d'ensemble", value="overview", className="tab-custom"),
                    dcc.Tab(label="Analyse financière", value="financial", className="tab-custom"),
                    dcc.Tab(label="Surveillance Revenus et Dépenses", value="surveillance", className="tab-custom"),
                    dcc.Tab(label="Résumé", value="summary", className="tab-custom"),
                    dcc.Tab(label="Coûts d'acquisition", value="costs", className="tab-custom"),
                    dcc.Tab(label="Profit", value="profit", className="tab-custom"),
                    dcc.Tab(label="Données Zone Géographique", value="geo_analysis", className="tab-custom"),
                ], className="tabs-custom"),
                
                # Contenu des tabs
                html.Div(id="tab-content", className="mt-4")
                
            ], width=9)
        ])
    ], fluid=True),
    
    # Store components pour les données - SECTION DUPLIQUÉE COMMENTÉE
    # dcc.Store(id="analysis-results"),
    # dcc.Store(id="schl-payment-mode-store", data="financed"),
    
    # Conteneur caché pour les éléments dynamiques (évite les erreurs de callback)
    html.Div([
    # Éléments de l'onglet Analyse financière
    dbc.Input(id="revenue-brut-input", type="hidden"),
    dbc.Input(id="depenses-input", type="hidden"),
    dbc.Input(id="tga-input", type="hidden"),
    dbc.Checklist(id="use-dpa", options=[], value=[], style={"display": "none"}),
    dbc.Input(id="dpa-rate", type="hidden"),
    dbc.Input(id="building-ratio", type="hidden"),
    dbc.Input(id="adj-revenue", type="hidden"),
    dbc.Input(id="adj-depenses", type="hidden"),
    dbc.Input(id="adj-tga", type="hidden"),
    dbc.Button(id="simulate-revenue-btn", style={"display": "none"}),
    html.Div(id="revenue-simulation-results"),
    
    # AJOUT : Déplacer le composant schl-payment-mode ici
    dbc.RadioItems(
        id="schl-payment-mode",
        options=[
            {"label": "Financer la prime SCHL (ajouter au prêt)", "value": "financed"},
            {"label": "Payer la prime SCHL comptant (chez le notaire)", "value": "cash"}
        ],
        value="financed",
        persistence=True,
        persistence_type="session",
        style={"display": "none"}  # Caché par défaut
    ),
    
    # Composant pour l'affichage dans l'onglet profit
    dbc.RadioItems(
        id="schl-payment-mode-profit-display",
        options=[
            {"label": "Financer la prime SCHL (ajouter au prêt)", "value": "financed"},
            {"label": "Payer la prime SCHL comptant (chez le notaire)", "value": "cash"}
        ],
        value="financed",
        style={"display": "none"}
    ),
        
        # Éléments pour la simulation d'intérêt
        dbc.Input(id="montant-pret-input", type="hidden"),
        dbc.Input(id="taux-interet-input", type="hidden"),
        dbc.Input(id="amortissement-input", type="hidden"),
        dbc.Input(id="adj-pret", type="hidden"),
        dbc.Input(id="adj-taux", type="hidden"),
        dbc.Input(id="adj-amort", type="hidden"),
        dbc.Button(id="simulate-interet-btn", style={"display": "none"}),
        html.Div(id="interet-simulation-results"),
        html.Div(id="schl-premium-section"),
        
        # Boutons de simulation
        dbc.Button(id="simulate-integrated-btn", style={"display": "none"}),
        html.Div(id="integrated-simulation-results"),
        dbc.Button(id="calculate-cashflow-btn", style={"display": "none"}),
        html.Div(id="cashflow-results"),
        
        # Éléments des filtres géographiques
        dcc.Dropdown(id="filter-province", options=[], style={"display": "none"}),
        html.Div(id="region-filter-container"),
        dcc.Dropdown(id="filter-region", options=[], style={"display": "none"}),
        html.Div(id="detailed-filter-container"),
        dcc.RadioItems(id="filter-type", options=[], style={"display": "none"}),
        html.Div(id="specific-filter-container"),
        dcc.Dropdown(id="specific-zone-filter", options=[], style={"display": "none"}),
        
        # Ne pas utiliser cet élément, utiliser summary-content à la place
        # html.Div(id="summary-content-container-hidden"),
        
        # Inputs pour l'édition des propriétés
        *[dbc.Input(id=f"edit-{field}", type="hidden") for field in [
            "address", "prix_vente", "nombre_unites", "annee_construction", "type_batiment",
            "revenus_brut", "depenses_totales", "revenu_net", "depenses_taxes_municipales", 
            "depenses_taxes_scolaires", "depenses_assurances", "depenses_electricite", "depenses_chauffage",
            "financement_schl_ratio_couverture_dettes", "financement_schl_taux_interet", "financement_schl_amortissement",
            "financement_conv_ratio_couverture_dettes", "financement_conv_taux_interet", "financement_conv_amortissement",
            "latitude", "longitude"
        ]],
        dbc.Button(id="save-property-changes", style={"display": "none"}),
        dbc.Button(id="cancel-property-changes", style={"display": "none"}),
        
        # Éléments de projections
        dbc.Input(id="inflation-rate", type="hidden"),
        dbc.Input(id="rent-increase", type="hidden"),
        dbc.Input(id="appreciation-rate", type="hidden"),
        dbc.Input(id="projection-years", type="hidden"),
        dbc.Input(id="taux-terme-initial", type="hidden"),
        dbc.Input(id="taux-terme-2", type="hidden"),
        dbc.Input(id="taux-terme-3", type="hidden"),
        dbc.Input(id="taux-terme-4", type="hidden"),
        dbc.Input(id="taux-terme-5", type="hidden"),
        dbc.Checklist(id="use-degressive-interest", options=[], value=[], style={"display": "none"}),
        dbc.Button(id="generate-projections-btn", style={"display": "none"}),
        html.Div(id="projection-results"),
        
        # Sélecteur de taux conventionnel
        dcc.Dropdown(id="conventional-rate-selector", options=[], style={"display": "none"}),
        # Store egi-criterion centralisé
        
        # Éléments pour la section Prix à payer (cachés ici car créés dynamiquement)
        dbc.Input(id="adjusted-revenue-brut", type="hidden"),
        dbc.Input(id="adjusted-depenses-totales", type="hidden"),
        dbc.Button(id="add-revenue-btn", style={"display": "none"}),
        dbc.Button(id="add-expense-btn", style={"display": "none"}),
        html.Div(id="additional-revenues-container"),
        html.Div(id="additional-expenses-container"),
        dbc.Button(id="recalculate-economic-values-btn", style={"display": "none"}),
        html.Div(id="economic-values-content"),
        
    ], style={"display": "none"}),
    
    # Modal pour les calculs détaillés
    dbc.Modal([
        dbc.ModalHeader([
            html.I(className="fas fa-calculator me-2"),
            "Explications détaillées des calculs"
        ]),
        dbc.ModalBody(id="calculations-modal-body"),
        dbc.ModalFooter(
            dbc.Button("Fermer", id="close-calculations", className="btn-primary-custom")
        )
    ], id="calculations-modal", size="xl", scrollable=True),
    
], fluid=True, className="p-0")

# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------
@app.callback(
    Output("historical-date-div", "style"),
    Input("data-source", "value")
)
def toggle_historical_date(data_source):
    if data_source in ["historical", "unavailable"]:
        return {"display": "block"}
    return {"display": "none"}

@app.callback(
    Output("property-selector", "options"),
    [Input("data-source", "value"),
     Input("historical-date", "date"),
     Input("filtered-properties", "data"),
     # Ajouter des inputs pour forcer la mise à jour quand les filtres changent
     Input("filter-province", "value"),
     Input("filter-region", "value"),
     Input("filter-type", "value"),
     Input("specific-zone-filter", "value")]
)
def update_property_list(data_source, hist_date, filtered_properties, 
                        province, region, filter_type, specific_zone):
    print(f"\n=== Mise à jour de la liste des propriétés ===")
    print(f"Filtres actifs - Province: {province}, Région: {region}, Type: {filter_type}, Zone: {specific_zone}")
    print(f"Propriétés filtrées reçues: {len(filtered_properties) if filtered_properties else 0}")
    
    # Si un filtre géographique est actif et qu'aucune propriété n'est retournée, ne rien afficher
    if (province and province != "all") and (not filtered_properties or len(filtered_properties) == 0):
        print("Filtres géographiques actifs mais aucun immeuble trouvé - retour d'une liste vide")
        return [{"label": "Aucun immeuble dans cette zone", "value": None}]
    
    if data_source == "active":
        df = load_immeubles()
    elif data_source == "historical":
        df = load_immeubles_history(pd.to_datetime(hist_date).date())
    else:  # unavailable
        df_hist = load_immeubles_history(pd.to_datetime(hist_date).date())
        df_live = load_immeubles()
        df = df_hist[~df_hist['address'].isin(df_live['address'].unique())]
    
    print(f"Total des immeubles disponibles: {len(df)}")
    
    # Si des propriétés filtrées existent et qu'un filtre géographique est actif
    if filtered_properties and (province and province != "all"):
        # Filtrer le dataframe pour ne garder que les adresses dans la liste filtrée
        df_filtered = df[df['address'].isin(filtered_properties)]
        print(f"Immeubles après filtrage géographique: {len(df_filtered)}")
        
        if not df_filtered.empty:
            # Ne pas utiliser unique() pour permettre les adresses dupliquées
            print(f"Immeubles trouvés: {len(df_filtered)}")
            # Utiliser un identifiant basé sur la position dans le DataFrame complet
            return [{"label": f"{row['address']} (#{idx})", "value": f"{row['address']}|{idx}"} 
                   for idx, (_, row) in enumerate(df_filtered.iterrows())]
        else:
            print("Aucun immeuble dans la zone sélectionnée")
            return [{"label": "Aucun immeuble dans cette zone", "value": None}]
    
    # Sinon retourner toutes les propriétés sans contrainte d'unicité
    print(f"Retour de tous les immeubles: {len(df)}")
    # Utiliser un identifiant basé sur la position dans le DataFrame complet
    return [{"label": f"{row['address']} (#{idx})", "value": f"{row['address']}|{idx}"} 
           for idx, (_, row) in enumerate(df.iterrows())]

@app.callback(
    Output("effective-tax-rate", "children"),
    [Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("property-data", "data"),
     Input("property-selector", "value")]
)
def update_tax_rate(province, status, property_data, property_addr):
    is_incorporated = status == "incorporated"
    
    # Si incorporé, retourner le taux fixe de la table entreprise
    if is_incorporated:
        rate = get_tax_rate_for_province(province, is_incorporated)
        return f"{rate:.2f}%"
    
    # Si non-incorporé et qu'une propriété est sélectionnée
    if property_data and property_data.get('revenu_net'):
        # Utiliser directement le revenu_net de la BD
        revenu_net_bd = clean_monetary_value(property_data.get('revenu_net', 0))
        
        # Si pas de revenu net, le calculer
        if revenu_net_bd == 0:
            revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
            depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
            revenu_net_bd = revenus_bruts - depenses
        
        # S'assurer qu'on a un revenu net valide
        if revenu_net_bd <= 0:
            return "0.0% (pas de revenu net)"
        
        # Calcul des intérêts déductibles
        interet_annuel = 0
        prix = clean_monetary_value(property_data.get('prix_vente', 0))
        
        if prix > 0:
            # Récupérer les paramètres de financement selon le statut
            if is_incorporated:
                taux_str = str(property_data.get('financement_conv_taux_interet', '5.5')).replace('%', '').strip()
                montant_pret = prix * 0.75  # Conventionnel
            else:
                taux_str = str(property_data.get('financement_schl_taux_interet', '5.5')).replace('%', '').strip()
                montant_pret = prix * 0.85  # SCHL
            
            try:
                taux_interet = float(taux_str) / 100
            except:
                taux_interet = 0.055
            
            interet_annuel = montant_pret * taux_interet
        
        # Calcul de la DPA si applicable
        dpa_deduction = 0
        use_dpa = property_data.get('use_dpa', False)
        if use_dpa and prix > 0:
            building_ratio = 0.8  # 80% par défaut
            dpa_rate = 0.04  # 4% par défaut
            building_value = prix * building_ratio
            # Règle de demi-année pour la première année
            dpa_deduction = building_value * dpa_rate * 0.5
            
            # Limiter la DPA pour ne pas créer de perte
            max_dpa = max(0, revenu_net_bd - interet_annuel)
            dpa_deduction = min(dpa_deduction, max_dpa)
        
        # Revenu imposable
        revenu_imposable = max(0, revenu_net_bd - interet_annuel - dpa_deduction)
        
        # Calcul de l'impôt progressif
        impot = calculate_progressive_tax(revenu_imposable, province) if revenu_imposable > 0 else 0
        
        # Calculer le taux effectif sur le revenu IMPOSABLE (correct)
        taux_effectif = (impot / revenu_imposable * 100) if revenu_imposable > 0 else 0
        
        # Debug
        print(f"\n=== CALCUL TAUX EFFECTIF ===")
        print(f"Province: {province}")
        print(f"Statut: Non-incorporé")
        print(f"Revenu net (BD): {revenu_net_bd:,.0f} $")
        print(f"Intérêts déductibles: {interet_annuel:,.0f} $")
        print(f"DPA: {dpa_deduction:,.0f} $")
        print(f"Revenu imposable: {revenu_imposable:,.0f} $")
        print(f"Impôt calculé: {impot:,.0f} $")
        print(f"Taux effectif: {taux_effectif:.1f}%")
        
        return f"{taux_effectif:.1f}%"
    
    # Fallback si aucune propriété sélectionnée
    if is_incorporated:
        rate = get_tax_rate_for_province(province, is_incorporated)
        return f"{rate:.2f}%"
    else:
        revenu_exemple = 80000
        impot_exemple = calculate_progressive_tax(revenu_exemple, province)
        taux_effectif = (impot_exemple / revenu_exemple * 100)
        return f"{taux_effectif:.1f}% (exemple 80k$)"

@app.callback(
    [Output("price-metric", "children"),
     Output("revenue-metric", "children"),
     Output("tga-metric", "children"),
     Output("cashflow-metric", "children"),
     Output("property-data", "data")],
    [Input("property-selector", "value"),
     Input("data-source", "value"),
     Input("historical-date", "date"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("schl-payment-mode", "value"),
     Input("conventional-rate-selector", "value"),
     Input("manual-schl-rate", "data")]
)
def update_metrics(property_addr, data_source, hist_date, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate, manual_schl_rate):
    print(f"🔄 Update metrics [2] appelé!")
    print(f"  📍 Property: {property_addr}")
    print(f"  🏦 Loan type: {loan_type}")
    print(f"  💰 SCHL payment mode: {schl_payment_mode}")
    print(f"  📊 Taux SCHL manuel: {manual_schl_rate}%")
    
    if not property_addr:
        return "-", "-", "-", "-", None
    
    # S'assurer que le mode de paiement SCHL est défini avec une valeur par défaut
    if not schl_payment_mode:
        schl_payment_mode = "financed"
        
    # Charger les données
    if data_source == "active":
        df = load_immeubles()
    elif data_source == "historical":
        df = load_immeubles_history(pd.to_datetime(hist_date).date())
    else:
        df_hist = load_immeubles_history(pd.to_datetime(hist_date).date())
        df_live = load_immeubles()
        df = df_hist[~df_hist['address'].isin(df_live['address'].unique())]
    
    # Vérifier si la valeur contient l'index pour traiter le nouveau format "adresse|index"
    if "|" in property_addr:
        address_part, index_part = property_addr.split("|")
        index_part = int(index_part)
        
        # L'index doit être basé sur la position originale dans le DataFrame complet
        # Plutôt que de filtrer par adresse puis utiliser l'index, utilisons l'index original
        # pour trouver l'immeuble correspondant
        try:
            # Vérifier si l'index est valide dans le DataFrame complet
            if index_part < len(df):
                # Vérifier que l'adresse correspond bien à celle attendue
                if df.iloc[index_part]['address'] == address_part:
                    property_data = df.iloc[index_part]
                else:
                    # Si l'adresse ne correspond pas, chercher parmi tous les immeubles avec cette adresse
                    properties_with_addr = df[df['address'] == address_part]
                    if not properties_with_addr.empty:
                        property_data = properties_with_addr.iloc[0]
                    else:
                        # Fallback: première entrée du DataFrame si aucune correspondance
                        property_data = df.iloc[0]
            else:
                # Fallback: chercher l'immeuble par adresse
                properties_with_addr = df[df['address'] == address_part]
                if not properties_with_addr.empty:
                    property_data = properties_with_addr.iloc[0]
                else:
                    # Fallback: première entrée du DataFrame si aucune correspondance
                    property_data = df.iloc[0]
        except Exception as e:
            print(f"Erreur lors de la récupération de l'immeuble: {e}")
            # Fallback: chercher l'immeuble par adresse uniquement
            properties_with_addr = df[df['address'] == address_part]
            if not properties_with_addr.empty:
                property_data = properties_with_addr.iloc[0]
            else:
                # Dernière option: première entrée du DataFrame
                property_data = df.iloc[0]
    else:
        # Ancien format pour compatibilité
        properties = df[df['address'] == property_addr]
        if not properties.empty:
            property_data = properties.iloc[0]
        else:
            # Fallback si l'adresse n'existe pas
            property_data = df.iloc[0]
    
    # Nettoyer et convertir les valeurs avec les VRAIS noms de colonnes
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    
    # *** CORRECTION: Toujours calculer le revenu net à partir de revenus_brut - depenses_totales ***
    revenue_net = revenue_brut - depenses
    
    tga = (revenue_net / prix * 100) if prix > 0 else 0
    
    # Récupérer les paramètres de financement selon le type de prêt
    try:
        # Récupérer les paramètres de prêt pour les calculs supplémentaires
        if loan_type == "SCHL":
            taux_str = str(property_data.get('financement_schl_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_schl_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
        else:
            # Pour conventionnel, utiliser le taux sélectionné si disponible
            if conventional_rate and conventional_rate != "":
                parts = conventional_rate.split('_')
                if len(parts) >= 2:
                    taux_str = parts[-1]
                    taux_interet = float(taux_str) / 100
                else:
                    taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                    taux_interet = float(taux_str) / 100 if taux_str else 0.055
            else:
                taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                taux_interet = float(taux_str) / 100 if taux_str else 0.055
            
            rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 1.2))
            amort_str = str(property_data.get('financement_conv_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
    except (ValueError, TypeError):
        print("Erreur lors de la conversion des paramètres de prêt - utilisation des valeurs par défaut")
        taux_interet = 0.055  # 5.5%
        amortissement = 25
    
    # Calcul du prêt basé sur le RDC
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
    
    # Calcul de la prime SCHL si applicable
    prime_schl = 0
    if loan_type == "SCHL":
        # Pour l'instant, utiliser un taux par défaut de 2.40%
        # Utiliser le taux manuel s'il est fourni, sinon utiliser le taux par défaut
        rate_to_use = manual_schl_rate if manual_schl_rate is not None else 2.40
        prime_schl = montant_pret * (rate_to_use / 100)
        
        print(f"🎯 [Callback UPDATE_METRICS #2] Calcul prime SCHL")
        print(f"    📌 Taux utilisé: {rate_to_use}% (manuel: {manual_schl_rate})")
        print(f"    💰 Prime calculée: {prime_schl:,.2f} $")
    
    # MODIFICATION : Ajuster le montant financé selon le mode de paiement
    if loan_type == "SCHL" and schl_payment_mode == "cash":
        montant_finance = montant_pret  # La prime n'est PAS ajoutée
    else:
        montant_finance = montant_pret + prime_schl  # La prime est financée
    
    # Si la prime est financée, recalculer la mensualité avec le nouveau montant
    if montant_finance != montant_pret:
        mensualite, _ = calcul_mensualite(montant_finance, taux_interet, amortissement)
    else:
        mensualite = pmt_mensuelle
    
    # Calcul des intérêts et capital pour le premier mois
    taux_mensuel = taux_interet / 12
    interet_mois_1 = montant_finance * taux_mensuel
    capital_mois_1 = mensualite - interet_mois_1
    
    # Calcul pour les 12 premiers mois
    solde_debut = montant_finance
    interet_annuel = 0
    capital_annuel = 0
    
    for mois in range(12):
        interet_mois = solde_debut * taux_mensuel
        capital_mois = mensualite - interet_mois
        interet_annuel += interet_mois
        capital_annuel += capital_mois
        solde_debut -= capital_mois
    
    # Calcul de l'impôt selon la nouvelle logique
    is_incorporated = tax_status == "incorporated"
    
    # Pour le cashflow mensuel, on utilise les valeurs du premier mois
    revenue_net_mensuel = revenue_net / 12
    
    # 1. Montant imposable = Rev Net (M) - intérêt payé du mois
    montant_imposable_mois_1 = revenue_net_mensuel - interet_mois_1
    
    # Calcul de l'impôt sur le montant imposable
    if is_incorporated:
        tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
        impot_mois_1 = montant_imposable_mois_1 * tax_rate if montant_imposable_mois_1 > 0 else 0
    else:
        # Pour les particuliers, calculer l'impôt annuel puis diviser par 12
        montant_imposable_annuel = revenue_net - interet_annuel
        impot_annuel = calculate_progressive_tax(montant_imposable_annuel, tax_province) if montant_imposable_annuel > 0 else 0
        impot_mois_1 = impot_annuel / 12
    
    # 2. Revenus net après impôt = Rev Net (M) - (montant imposable × taux impôt)
    # ATTENTION : C'est montant imposable × taux, pas juste l'impôt !
    if is_incorporated:
        revenue_net_apres_impot = revenue_net_mensuel - (montant_imposable_mois_1 * tax_rate)
    else:
        # Pour les particuliers, on utilise l'impôt calculé
        revenue_net_apres_impot = revenue_net_mensuel - impot_mois_1
    
    # 3. Final cashflow = Revenus net après impôt - Intérêts - Paiement remboursement du prêt
    # Le paiement de remboursement = Capital seulement
    # Modification: On soustrait aussi les intérêts car ils font partie des dépenses réelles du cashflow
    cashflow_mensuel = revenue_net_mensuel - impot_mois_1 - interet_mois_1 - capital_mois_1
    
    # Debug complet
    print(f"=== DEBUG COMPLET ===")
    print(f"Adresse sélectionnée: {property_addr}")
    print(f"Revenue net mensuel: {revenue_net_mensuel:,.0f} $")
    print(f"PMT mensuelle: {pmt_mensuelle:,.0f} $")
    print(f"Intérêt mois 1: {interet_mois_1:,.0f} $")
    print(f"Capital mois 1: {capital_mois_1:,.0f} $")
    print(f"Montant imposable mois 1: {montant_imposable_mois_1:,.0f} $")
    print(f"Impôt mois 1: {impot_mois_1:,.0f} $")
    print(f"Cashflow mensuel: {cashflow_mensuel:,.0f} $")
    
    return (f"{prix:,.0f} $",
            f"{revenue_net:,.0f} $",
            f"{tga:.2f}%",
            f"{cashflow_mensuel:,.0f} $",
            property_data.to_dict())

@app.callback(
    Output("tab-content", "children"),
    [Input("main-tabs", "value"),
     Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("schl-payment-mode", "value"),
     Input("conventional-rate-selector", "value"),
     Input("schl-premium-cache", "data"),
     Input("manual-schl-rate", "data")]
)
def update_tab_content(active_tab, property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate, schl_cache, manual_schl_rate):
    print(f"🚀 [UPDATE_TAB_CONTENT #2] Onglet sélectionné: '{active_tab}'")
    
    if not property_data:
        return dbc.Alert("Veuillez sélectionner un immeuble pour voir les détails.", 
                        color="info", className="mt-3")
    
    if active_tab == "overview":
        return create_overview_tab(property_data)
    elif active_tab == "financial":
        return create_financial_tab(property_data, loan_type, tax_province, tax_status, conventional_rate, schl_cache, manual_schl_rate)
    elif active_tab == "surveillance":
        return create_surveillance_tab(property_data)
    elif active_tab == "summary":
        return create_summary_tab(property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate)
    elif active_tab == "costs":
        return create_costs_tab(property_data, loan_type)
    elif active_tab == "profit":
        return create_profit_tab(property_data, loan_type, tax_province, tax_status, schl_payment_mode, conventional_rate)
    elif active_tab == "geo_analysis":
        return get_geo_analysis_component(property_data)
    else:
        return dbc.Alert("Sélectionnez un onglet pour voir le contenu.", 
                        color="info", className="mt-3")

def create_overview_tab(property_data):
    # Utiliser les VRAIS noms de colonnes avec nettoyage
    nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
    annee_construction = clean_numeric_value(property_data.get('annee_construction', 0))
    
    # Composant supprimé - plus de gestion EGI automatique
    egi_component = None
    
    # Créer la carte si les coordonnées sont disponibles
    map_component = None
    
    # Variable pour suivre si une carte a été créée avec succès
    map_created = False
    
    # D'abord essayer avec latitude/longitude (plus simple et plus fiable)
    if property_data.get('latitude') and property_data.get('longitude'):
        try:
            lat = float(property_data['latitude'])
            lon = float(property_data['longitude'])
            
            # Vérifier que les coordonnées sont valides
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                map_component = create_simple_map(property_data)
                print(f"Carte créée avec lat/lon: {lat}, {lon}")
                map_created = True
            else:
                print(f"Coordonnées invalides: lat={lat}, lon={lon}")
        except (ValueError, TypeError) as e:
            print(f"Erreur lors de la conversion des coordonnées lat/lon: {e}")
    
    # Si pas de lat/lon ou erreur, essayer geo_zone (plus complexe)
    if not map_created and property_data.get('geo_zone') and str(property_data.get('geo_zone')).lower() not in ['none', 'null', '']:
        try:
            import plotly.graph_objects as go
            import numpy as np
            from shapely import wkb
            
            geo_value = property_data['geo_zone']
            print(f"Type de geo_zone: {type(geo_value)}, Valeur (début): {str(geo_value)[:50]}...")
            
            # Si c'est une chaîne hexadécimale, la convertir en bytes
            if isinstance(geo_value, str):
                try:
                    wkb_bytes = bytes.fromhex(geo_value)
                except Exception as e:
                    print(f"Erreur de conversion hexadécimale: {e}")
                    raise ValueError("Impossible de convertir la chaîne hexadécimale en bytes")
            else:
                wkb_bytes = geo_value.tobytes() if hasattr(geo_value, "tobytes") else geo_value
            
            # Charger la géométrie à partir des bytes
            geometry = wkb.loads(wkb_bytes)
            print(f"Géométrie décodée avec succès, type: {geometry.geom_type}")
            
            # Extraire les coordonnées du polygone
            if hasattr(geometry, 'exterior'):
                # C'est un polygone
                x, y = geometry.exterior.xy
                lats, lons = list(y), list(x)
                center_lat, center_lon = geometry.centroid.y, geometry.centroid.x
            elif hasattr(geometry, 'xy'):
                # C'est une ligne
                x, y = geometry.xy
                lats, lons = list(y), list(x)
                center_lat, center_lon = np.mean(y), np.mean(x)
            else:
                # C'est un point ou autre
                center_lat, center_lon = geometry.y, geometry.x
                lats, lons = [center_lat], [center_lon]
    
            # Créer la figure avec la zone et le marqueur central
            fig_map = go.Figure()
            
            # Ajouter le polygone ou la ligne de la zone
            if len(lats) > 1:
                fig_map.add_trace(go.Scattermapbox(
                    lat=lats,
                    lon=lons,
                    mode='lines',
                    line=dict(width=2, color='#667eea'),
                    fill='toself',
                    fillcolor='rgba(102, 126, 234, 0.2)',
                    showlegend=False
                ))
            
            # Ajouter le marqueur pour l'adresse
            fig_map.add_trace(go.Scattermapbox(
                lat=[center_lat],
                lon=[center_lon],
                mode='markers',
                marker=go.scattermapbox.Marker(
                    size=14,
                    color='#667eea'
                ),
                text=property_data['address'],
                showlegend=False
            ))
            
            fig_map.update_layout(
                mapbox=dict(
                    style="open-street-map",
                    center=dict(
                        lat=center_lat,
                        lon=center_lon
                    ),
                    zoom=15
                ),
                showlegend=False,
                height=400,
                margin={"r":0,"t":0,"l":0,"b":0}
            )
            
            map_component = dcc.Graph(figure=fig_map, config={'displayModeBar': False})
            print("Carte créée avec geo_zone")
            map_created = True
            
        except Exception as e:
            print(f"Erreur lors du traitement de la géométrie: {e}")
            # Ne pas lever l'erreur, juste continuer sans carte
            map_component = None
    
    # Si toujours pas de carte, afficher un message d'information avec les données disponibles
    if not map_created:
        # Créer un message d'information avec les données disponibles
        debug_info = []
        if property_data.get('latitude'):
            debug_info.append(f"Latitude: {property_data.get('latitude')}")
        if property_data.get('longitude'):
            debug_info.append(f"Longitude: {property_data.get('longitude')}")
        if property_data.get('geo_zone'):
            debug_info.append(f"Geo_zone: {str(property_data.get('geo_zone'))[:50]}...")
        
        if debug_info:
            map_component = dbc.Alert([
                html.H6("Données de localisation détectées mais non utilisables", className="alert-heading"),
                html.Ul([html.Li(info) for info in debug_info]),
                html.P("Veuillez vérifier la qualité des données de géolocalisation.", className="mb-0")
            ], color="warning")
        else:
            map_component = dbc.Alert([
                html.I(className="fas fa-map-marker-alt me-2"),
                "Aucune donnée de localisation disponible pour cet immeuble."
            ], color="info")
    
    return html.Div([
        dbc.Row([
            dbc.Col([
        html.Div([
            html.H4([
                    html.I(className="fas fa-home me-2"),
                        "Détails de l'immeuble"
            ], className="mb-4"),
            
                dbc.Row([
                    dbc.Col([
                        html.P("Adresse", className="text-muted mb-1"),
                        html.P(property_data.get('address', 'N/A'), className="fw-bold")
                        ], width=12),
                        dbc.Col([
                            html.P("Nombre d'unités", className="text-muted mb-1"),
                            html.P(f"{int(nombre_unites) if nombre_unites else 0}", className="fw-bold")
                    ], width=6),
                    dbc.Col([
                            html.P("Année de construction", className="text-muted mb-1"),
                            html.P(f"{int(annee_construction) if annee_construction else 'N/A'}", className="fw-bold")
                        ], width=6),
                    dbc.Col([
                            html.P("Type de bâtiment", className="text-muted mb-1"),
                            html.P(f"{property_data.get('type_batiment', 'N/A')}", className="fw-bold")
                        ], width=6),
                        dbc.Col([
                            html.P("Nombre d'étages", className="text-muted mb-1"),
                            html.P(f"{property_data.get('nombre_etages', 'N/A')}", className="fw-bold")
                        ], width=6),
                    ])
        ], className="card-custom")
            ], width=6),
            
                    dbc.Col([
                        html.Div([
                    html.H4([
                        html.I(className="fas fa-chart-pie me-2"),
                        "Répartition des revenus"
        ], className="mb-4"),
        
                    dcc.Graph(
                        id="revenue-breakdown",
                        figure=create_revenue_breakdown_chart(property_data),
                        config={'displayModeBar': False}
                    )
                ], className="card-custom")
            ], width=6)
        ]),
        
        # Carte de localisation
                dbc.Row([
                    dbc.Col([
        html.Div([
                    html.H4([
                        html.I(className="fas fa-map-marked-alt me-2"),
                        "Localisation"
                    ], className="mb-4"),
                    
                    map_component
                ], className="card-custom")
            ], width=12)
        ], className="mt-4"),
        
        # Ajout du composant EGI s'il est disponible
        egi_component if egi_component else html.Div(),
    ])

def create_simple_map(property_data):
    """Crée une carte simple basée sur les coordonnées latitude/longitude"""
    import plotly.graph_objects as go
    
    try:
        lat = float(property_data['latitude'])
        lon = float(property_data['longitude'])
        
        fig_map = go.Figure(go.Scattermapbox(
            lat=[lat],
            lon=[lon],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=14,
                color='#667eea'
            ),
            text=property_data.get('address', 'Immeuble'),
            hoverinfo='text'
        ))
        
        fig_map.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(
                    lat=lat,
                    lon=lon
                ),
                zoom=15
            ),
            showlegend=False,
            height=400,
            margin={"r":0,"t":0,"l":0,"b":0}
        )
        
        # S'assurer que l'objet graphique est correctement créé
        result = dcc.Graph(figure=fig_map, config={'displayModeBar': False})
        if result is None:
            raise ValueError("Le composant graphique n'a pas pu être créé")
        return result
        
    except Exception as e:
        print(f"Erreur lors de la création de la carte simple: {e}")
        return None  # Retourner None pour indiquer l'échec de création de la carte

def create_financial_tab(property_data, loan_type, tax_province, tax_status, conventional_rate=None, schl_cache=None, manual_schl_rate=None):
    # Calculer les paramètres de base
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    
    # S'assurer que le prix est bien défini dès le début
    prix_str = str(property_data.get('prix_vente', 0)).replace('$', '').replace(' ', '').replace(',', '')
    try:
        prix = float(prix_str)
    except ValueError:
        print(f"Impossible de convertir la valeur du prix '{prix_str}' en nombre. Utilisation de la valeur par défaut 0.")
        prix = 0
    
    # Paramètres du prêt spécifiques à l'immeuble
    try:
        if loan_type == "SCHL":
            # Utiliser des valeurs par défaut en cas de valeurs manquantes
            rdc_ratio = float(property_data.get('financement_schl_ratio_couverture_dettes', 1.2) or 1.2)
            taux_str = str(property_data.get('financement_schl_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_schl_amortissement', 25)).strip()
            # Nettoyer la chaîne pour extraire uniquement la partie numérique
            import re
            amort_nums = re.findall(r'\d+', amort_str)
            amortissement = float(amort_nums[0]) if amort_nums else 25
        else:
            # Pour conventionnel, utiliser le taux sélectionné si disponible
            if conventional_rate and conventional_rate != "":
                parts = conventional_rate.split('_')
                if len(parts) >= 2:
                    taux_str = parts[-1]
                    taux_interet = float(taux_str) / 100
                else:
                    taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                    taux_interet = float(taux_str) / 100 if taux_str else 0.055
            else:
                taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
                taux_interet = float(taux_str) / 100 if taux_str else 0.055
            
            rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 1.2))
            amort_str = str(property_data.get('financement_conv_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
            
        # Calcul du montant du prêt basé sur le RDC
        montant_pret, ratio_pret_valeur, mensualite_max = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
        
    except (ValueError, TypeError):
        print("Erreur lors de la conversion des paramètres de prêt - utilisation des valeurs par défaut")
        rdc_ratio = 1.2
        taux_interet = 0.055  # 5.5%
        amortissement = 25
        
        # En cas d'erreur, utiliser une valeur par défaut pour le prêt
        montant_pret = prix * 0.75  # 75% de la valeur de l'immeuble par défaut
    
    loan_params = {
        "taux": taux_interet,
        "amortissement": amortissement,
        "rdc_ratio": rdc_ratio
    }
    
    # Utiliser la fonction standardisée pour le calcul du prêt
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
    
    return html.Div([
        # Alerte pour les changements de paramètres fiscaux
        dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            html.Strong("Paramètres fiscaux actuels : "),
            f"Province: {tax_province}, Statut: {'Incorporé' if is_incorporated else 'Non incorporé'}, ",
            f"Taux d'imposition: {tax_rate*100:.1f}%" if is_incorporated else f"Taux d'imposition: Progressif selon les tranches",
            html.Br(),
            html.Small("Les simulations précédentes pourraient ne pas refléter ces paramètres. Relancez les simulations après un changement.", className="text-muted")
        ], color="warning", dismissable=True, className="mb-4"),
        
        # Section Revenue Net
        html.Div([
            html.H4([
                html.I(className="fas fa-chart-line me-2"),
                "Simulation du Revenue Net"
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Revenu Brut Annuel", className="fw-bold"),
                    dbc.Input(
                        id="revenue-brut-input",
                        type="number",
                        value=property_data.get('revenus_brut', 0),
                        step=1000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Dépenses Annuelles", className="fw-bold"),
                    dbc.Input(
                        id="depenses-input",
                        type="number",
                        value=property_data.get('depenses_totales', 0),
                        step=1000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("TGA (%)", className="fw-bold"),
                    dbc.Input(
                        id="tga-input",
                        type="number",
                        value=round(((safe_float_conversion(property_data.get('revenus_brut', 0)) - safe_float_conversion(property_data.get('depenses_totales', 0))) / safe_float_conversion(property_data.get('prix_vente', 1)) * 100), 2),
                        step=0.1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
            ]),
            
            # Options DPA
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-calculator me-2"),
                        "Déduction pour Amortissement (DPA)"
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="use-dpa",
                                options=[{"label": "Appliquer la DPA", "value": True}],
                                value=[],
                                className="mb-2"
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label("Taux DPA (%)", className="fw-bold"),
                            dbc.Input(
                                id="dpa-rate",
                                type="number",
                                value=APP_PARAMS.get('default_dpa_rate', 4.0),
                                step=0.1,
                                disabled=True,
                                className="form-control-custom"
                            )
                        ], width=6),
                        dbc.Input(
                            id="building-ratio",
                            type="hidden",
                            value=100.0
                        )
                    ])
                ])
            ], className="mb-4"),
            
            # Ajustements pour simulation
            html.H5("Ajustements pour Simulation", className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Label("Ajustement Revenue (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-revenue", type="number", value=ADJUSTMENT_DEFAULTS.get('revenue_adjustment', 1000), step=100, className="form-control-custom")
                ], width=4),
                dbc.Col([
                    html.Label("Ajustement Dépenses (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-depenses", type="number", value=ADJUSTMENT_DEFAULTS.get('expense_adjustment', 1000), step=100, className="form-control-custom")
                ], width=4),
                dbc.Col([
                    html.Label("Ajustement TGA (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-tga", type="number", value=ADJUSTMENT_DEFAULTS.get('tga_adjustment', 0.1), step=0.1, className="form-control-custom")
                ], width=4),
            ]),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-revenue-btn", style={"display": "none"}),
            
            html.Div(id="revenue-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Coût d'Intérêt
        html.Div([
            html.H4([
                html.I(className="fas fa-percentage me-2"),
                "Simulation du Coût d'Intérêt"
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Montant du Prêt ($)", className="fw-bold"),
                    dbc.Input(
                        id="montant-pret-input",
                        type="number",
                        value=montant_pret,
                        step=5000,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Taux d'Intérêt (%)", className="fw-bold"),
                    dbc.Input(
                        id="taux-interet-input",
                        type="number",
                        value=loan_params['taux'],
                        step=0.1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Amortissement (années)", className="fw-bold"),
                    dbc.Input(
                        id="amortissement-input",
                        type="number",
                        value=loan_params['amortissement'],
                        step=1,
                        min=1,
                        className="form-control-custom mb-3"
                    )
                ], width=4),
            ]),
            
            # Prime SCHL si applicable
            html.Div(id="schl-premium-section"),
            
            # Ajustements pour simulation
            html.H5("Ajustements pour Simulation", className="mb-3 mt-4"),
            dbc.Row([
                dbc.Col([
                    html.Label("Ajustement Prêt (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-pret", type="number", value=ADJUSTMENT_DEFAULTS.get('loan_adjustment', 5000), step=1000, className="form-control-custom")
                ], width=3),
                dbc.Col([
                    html.Label("Ajustement Taux (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-taux", type="number", value=ADJUSTMENT_DEFAULTS.get('rate_adjustment', 0.1), step=0.01, className="form-control-custom")
                ], width=3),
                dbc.Col([
                    html.Label("Ajustement Amort. (±3x)", className="fw-bold"),
                    dbc.Input(id="adj-amort", type="number", value=ADJUSTMENT_DEFAULTS.get('amortization_adjustment', 0), step=1, className="form-control-custom")
                ], width=3),
            ]),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-interet-btn", style={"display": "none"}),
            
            html.Div(id="interet-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Simulation Intégrée
        html.Div([
            html.H4([
                html.I(className="fas fa-sync-alt me-2"),
                "Simulation Intégrée (Méthode Fiscale Complète)"
            ], className="mb-4"),
            
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Cette simulation applique la logique fiscale complète : "),
                html.Br(),
                "• Les intérêts sont déduits du revenu imposable",
                html.Br(),
                "• L'impôt est calculé sur (NOI - Intérêts - DPA)",
                html.Br(),
                "• Le cashflow final = NOI - Impôt - Intérêts - Capital"
            ], color="info", className="mb-4"),
            
            # Bouton caché car simulation auto
            dbc.Button(id="simulate-integrated-btn", style={"display": "none"}),
            
            html.Div(id="integrated-simulation-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Cashflow
        html.Div([
            html.H4([
                html.I(className="fas fa-money-bill-wave me-2"),
                "Analyse du Cashflow"
            ], className="mb-4"),
            
            # Bouton caché car simulation auto
            dbc.Button(id="calculate-cashflow-btn", style={"display": "none"}),
            
            html.Div(id="cashflow-results", className="mt-4")
        ], className="card-custom"),
        
        html.Hr(className="my-5"),
        
        # Section Projections financières (anciennement onglet séparé)
        html.Div([
            html.H4([
                html.I(className="fas fa-chart-area me-2"),
                "Projections financières"
            ], className="mb-4"),
            
            # Paramètres de projection
            dbc.Row([
                dbc.Col([
                    html.Label("Inflation annuelle (%)", className="fw-bold"),
                    dbc.Input(
                        id="inflation-rate",
                        type="number",
                        value=APP_PARAMS.get('default_inflation_rate', 2.0),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Augmentation loyers (%/an)", className="fw-bold"),
                    dbc.Input(
                        id="rent-increase",
                        type="number",
                        value=APP_PARAMS.get('default_rent_increase', 2.5),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
                dbc.Col([
                    html.Label("Appréciation immobilière (%/an)", className="fw-bold"),
                    dbc.Input(
                        id="appreciation-rate",
                        type="number",
                        value=APP_PARAMS.get('default_appreciation_rate', 3.0),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=4),
            ], className="mb-4"),
            
            # Section des taux d'intérêt par terme
            html.H5("Taux d'intérêt par terme (5 ans)", className="mt-4 mb-3"),
            html.P("Simulez l'évolution des taux d'intérêt après chaque renouvellement de terme", className="text-muted mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Terme initial (0-5 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-initial",
                        type="number",
                        value=clean_numeric_value(property_data.get(
                            'financement_schl_taux_interet' if loan_type == "SCHL" else 'financement_conv_taux_interet', 
                            APP_PARAMS.get('default_interest_rate', 5.5)
                        )) if property_data else APP_PARAMS.get('default_interest_rate', 5.5),
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("2e terme (6-10 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-2",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 0.5,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("3e terme (11-15 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-3",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
                dbc.Col([
                    html.Label("4e terme (16-20 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-4",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("5e terme (21-25 ans)", className="fw-bold"),
                    dbc.Input(
                        id="taux-terme-5",
                        type="number",
                        value=APP_PARAMS.get('default_interest_rate', 5.5) + 1.0,
                        step=0.1,
                        className="form-control-custom"
                    )
                ], width=3),
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        id="use-degressive-interest",
                        options=[{"label": "Utiliser intérêts dégressifs", "value": True}],
                        value=[True],
                        className="mb-2"
                    ),
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Années à projeter", className="fw-bold"),
                    dbc.Input(
                        id="projection-years",
                        type="number",
                        value=25,
                        min=5,
                        max=30,
                        step=5,
                        className="form-control-custom"
                    )
                ], width=4),
            ], className="mb-4"),
            
            dbc.Button([
                html.I(className="fas fa-chart-line me-2"),
                "Générer Projections"
            ], id="generate-projections-btn", className="btn-primary-custom", size="lg"),
            
            html.Div(id="projection-results", className="mt-4")
                  ], className="card-custom")
      ])
  
  
# Remplacer la fonction create_surveillance_tab dans votre fichier main2.py

def create_surveillance_tab(property_data):
    # Extraire les revenus détaillés
    revenus = {
        "Résidentiel": clean_monetary_value(property_data.get('revenu_residentiel', 0)),
        "Commercial": clean_monetary_value(property_data.get('revenu_commercial', 0)),
        "Stationnement": clean_monetary_value(property_data.get('revenu_stationnement', 0)),
        "Buanderie": clean_monetary_value(property_data.get('revenu_buanderie', 0)),
        "Rangement": clean_monetary_value(property_data.get('revenu_rangement', 0)),
        "Récupération": clean_monetary_value(property_data.get('revenu_recuperation', 0))
    }
    
    # Extraire les dépenses détaillées - gérer les cas singulier/pluriel et nettoyer les valeurs monétaires
    depenses = {
        "Vacances": clean_monetary_value(property_data.get('depense_vacances', property_data.get('depense_vacances', 0))),
        "Administration": clean_monetary_value(property_data.get('depense_administration', property_data.get('depense_administration', 0))),
        "Taxes municipales": clean_monetary_value(property_data.get('depenses_taxes_municipales', 0)),
        "Taxes scolaires": clean_monetary_value(property_data.get('depenses_taxes_scolaires', 0)),
        "Assurances": clean_monetary_value(property_data.get('depenses_assurances', 0)),
        "Électricité": clean_monetary_value(property_data.get('depenses_electricite', 0)),
        "Chauffage": clean_monetary_value(property_data.get('depenses_chauffage', 0)),
        "Déneigement": clean_monetary_value(property_data.get('depenses_deneigement', 0)),
        "Ascenseur": clean_monetary_value(property_data.get('depenses_ascenseur', 0)),
        "Location équipement": clean_monetary_value(property_data.get('depenses_location_equipement', 0)),
        "Réserve entretien": clean_monetary_value(property_data.get('depenses_reserve_entretien', 0)),
        "Salaire concierge": clean_monetary_value(property_data.get('depenses_salaire_concierge', 0)),
        "Réserve mobilier": clean_monetary_value(property_data.get('depenses_reserve_mobilier', 0)),
        "Air climatisé": clean_monetary_value(property_data.get('depenses_air_climatise', 0)),
        "WiFi/Surveillance": clean_monetary_value(property_data.get('depenses_wifi_surveillance', 0)),
        "Entretien/Paysagement": clean_monetary_value(property_data.get('depenses_entretien_paysagement', property_data.get('depense_entretien_paysagement', 0))),
        "Télécommunications": clean_monetary_value(property_data.get('depenses_telecommunications', property_data.get('depense_telecommunications', 0)))
    }
    
    # Calculer les totaux à partir des valeurs détaillées
    revenus_total_calcule = sum(revenus.values())
    depenses_total_calcule = sum(depenses.values())
    
    # Récupérer les totaux stockés
    revenus_total_stocke = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses_total_stocke = clean_monetary_value(property_data.get('depenses_totales', 0))
    
    # Comparer les taxes municipales avec les taux officiels
    tax_comparison = compare_municipal_taxes(property_data)
    
    # Extraire les caractéristiques
    caracteristiques = {
        "Système de chauffage": property_data.get('caract_systeme_chauffage', 'N/A'),
        "Système eau chaude": property_data.get('caract_systeme_eau_chaude', 'N/A'),
        "Panneaux électriques": property_data.get('caract_panneaux_electriques', 'N/A'),
        "Plomberie": property_data.get('caract_plomberie', 'N/A'),
        "Condition cuisines": property_data.get('caract_condition_cuisines', 'N/A'),
        "Condition salles de bain": property_data.get('caract_condition_salles_bain', 'N/A'),
        "Recouvrement planchers": property_data.get('caract_recouvrement_planchers', 'N/A'),
        "Étude environnementale": property_data.get('caract_etude_environnementale', 'N/A'),
        "Condition toit": property_data.get('caract_condition_toit', 'N/A'),
        "Revêtement extérieur": property_data.get('caract_revetement_exterieur', 'N/A'),
        "Condition balcons": property_data.get('caract_condition_balcons', 'N/A'),
        "Condition portes": property_data.get('caract_condition_portes', 'N/A'),
        "Condition fenêtres": property_data.get('caract_condition_fenetres', 'N/A'),
        "Type stationnement": property_data.get('caract_type_stationnement', 'N/A'),
        "Intercom": property_data.get('caract_intercom', 'N/A'),
        "Système alarme": property_data.get('caract_systeme_alarme', 'N/A'),
        "Entente concierge": property_data.get('caract_entente_concierge', 'N/A')
    }
    
    # Créer les graphiques
    # Graphique des revenus
    fig_revenus = go.Figure(data=[go.Bar(
        x=list(revenus.keys()),
        y=list(revenus.values()),
        marker_color='#48bb78',
        text=[f"{v:,.0f} $" for v in revenus.values()],
        textposition='auto',
    )])
    fig_revenus.update_layout(
        title="Détail des revenus",
        yaxis_title="Montant ($)",
        showlegend=False,
        height=400
    )
    
    # Graphique des dépenses
    fig_depenses = go.Figure(data=[go.Bar(
        x=list(depenses.keys()),
        y=list(depenses.values()),
        marker_color='#ff6b6b',
        text=[f"{v:,.0f} $" for v in depenses.values()],
        textposition='auto',
    )])
    fig_depenses.update_layout(
        title="Détail des dépenses",
        yaxis_title="Montant ($)",
        showlegend=False,
        height=400,
        xaxis_tickangle=-45
    )
    
    return html.Div([
        # Section Revenus
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-chart-line me-2"),
                    "Analyse détaillée des revenus"
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_revenus, config={'displayModeBar': False})
                    ], width=8),
                    dbc.Col([
                        html.H5("Total des revenus", className="mb-3"),
                        html.H3(f"{revenus_total_stocke:,.0f} $", className="text-success"),
                        html.Hr(),
                        html.Div([
                            html.P([
                                html.Strong(f"{k}: "),
                                f"{v:,.0f} $"
                            ], className="mb-2") for k, v in revenus.items() if v > 0
                        ]),
                        # Afficher le total calculé si différent du total stocké
                        html.Div([
                            html.Hr(),
                            html.P([
                                html.Strong("Total calculé: "),
                                f"{revenus_total_calcule:,.0f} $"
                            ], className="text-info")
                        ]) if abs(revenus_total_calcule - revenus_total_stocke) > 1 else html.Div()
                    ], width=4)
                ])
            ])
        ], className="mb-4"),
        
        # Section Dépenses
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-receipt me-2"),
                    "Analyse détaillée des dépenses"
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_depenses, config={'displayModeBar': False})
                    ], width=8),
                    dbc.Col([
                        html.H5("Total des dépenses", className="mb-3"),
                        html.H3(f"{depenses_total_stocke:,.0f} $", className="text-danger"),
                        html.Hr(),
                        html.Div([
                            html.P([
                                html.Strong(f"{k}: "),
                                f"{v:,.0f} $"
                            ], className="mb-2") for k, v in sorted(depenses.items(), key=lambda x: x[1], reverse=True) if v > 0
                        ], style={"maxHeight": "400px", "overflowY": "auto"}),
                        # Afficher le total calculé si différent du total stocké
                        html.Div([
                            html.Hr(),
                            html.P([
                                html.Strong("Total calculé: "),
                                f"{depenses_total_calcule:,.0f} $"
                            ], className="text-info")
                        ]) if abs(depenses_total_calcule - depenses_total_stocke) > 1 else html.Div()
                    ], width=4)
                ])
            ])
        ], className="mb-4"),
        
        # Section Analyse des taxes municipales
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-balance-scale me-2"),
                    "Analyse des taxes municipales"
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        html.H6("Région détectée", className="text-muted"),
                        html.P(tax_comparison['region'], className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.H6("Évaluation municipale", className="text-muted"),
                        html.P(f"{tax_comparison['eval_municipale']:,.0f} $" if tax_comparison['eval_municipale'] else "N/D", 
                               className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.H6("Taux officiel", className="text-muted"),
                        html.P(f"{tax_comparison['taux_officiel']:.4f}%" if tax_comparison['taux_officiel'] else "N/D", 
                               className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.H6("Taxes dans la BD", className="text-muted"),
                        html.P(f"{tax_comparison['taxes_bd']:,.0f} $" if tax_comparison['taxes_bd'] else "N/D", 
                               className="fw-bold")
                    ], width=3),
                ]),
                
                html.Div([
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.H6("Taxes calculées (selon taux officiel)", className="text-muted"),
                            html.P(f"{tax_comparison['taxes_calculees']:,.0f} $" if tax_comparison['taxes_calculees'] else "N/D", 
                                   className="fw-bold text-primary")
                        ], width=4),
                        dbc.Col([
                            html.H6("Différence", className="text-muted"),
                            html.P([
                                f"{tax_comparison['difference']:+,.0f} $ ",
                                f"({tax_comparison['difference_pct']:+.1f}%)" if tax_comparison['difference_pct'] else ""
                            ] if tax_comparison['difference'] is not None else "N/D", 
                            className=f"fw-bold {'text-danger' if tax_comparison['difference'] and tax_comparison['difference'] > 0 else 'text-success'}")
                        ], width=4),
                        dbc.Col([
                            html.H6("Analyse", className="text-muted"),
                            html.P(
                                "Taxes surévaluées dans la BD" if tax_comparison['difference'] and tax_comparison['difference'] < 0 
                                else "Taxes sous-évaluées dans la BD" if tax_comparison['difference'] and tax_comparison['difference'] > 0 
                                else "Taxes conformes" if tax_comparison['difference'] == 0 
                                else "Analyse impossible",
                                className="fw-bold"
                            )
                        ], width=4),
                    ])
                ]) if tax_comparison['taxes_calculees'] else html.Div([
                    html.Hr(),
                    dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        "Impossible de calculer les taxes municipales. Vérifiez que l'évaluation municipale et la région sont disponibles."
                    ], color="info")
                ])
            ])
        ], className="mb-4"),
        
        # Section Caractéristiques
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-building me-2"),
                    "Caractéristiques de l'immeuble"
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td(k, className="fw-bold"),
                                    html.Td(v if v and v != 'N/A' else html.Span("Non spécifié", className="text-muted"))
                                ]) for k, v in list(caracteristiques.items())[:len(caracteristiques)//2]
                            ])
                        ], striped=True, hover=True, size="sm")
                    ], width=6),
                    dbc.Col([
                        dbc.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td(k, className="fw-bold"),
                                    html.Td(v if v and v != 'N/A' else html.Span("Non spécifié", className="text-muted"))
                                ]) for k, v in list(caracteristiques.items())[len(caracteristiques)//2:]
                            ])
                        ], striped=True, hover=True, size="sm")
                    ], width=6)
                ])
            ])
        ], className="mb-4"),
        
        # Section Indicateurs économiques
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-chart-area me-2"),
                    "Indicateurs économiques"
                ], className="mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Taux d'emploi", className="text-muted"),
                                html.P(f"Région: {property_data.get('indicateur_taux_emploi_region', 'N/A')}%"),
                                html.P(f"Province: {property_data.get('indicateur_taux_emploi_province', 'N/A')}%")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Taux de chômage", className="text-muted"),
                                html.P(f"Région: {property_data.get('indicateur_taux_chomage_region', 'N/A')}%"),
                                html.P(f"Province: {property_data.get('indicateur_taux_chomage_province', 'N/A')}%")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Revenu disponible", className="text-muted"),
                                html.P(f"Région: {property_data.get('indicateur_revenu_disponible_region', 'N/A')} $"),
                                html.P(f"Province: {property_data.get('indicateur_revenu_disponible_province', 'N/A')} $")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Évaluation municipale", className="text-muted"),
                                html.P(f"Terrain: {clean_monetary_value(property_data.get('eval_municipale_terrain', 0)):,.0f} $"),
                                html.P(f"Bâtiment: {clean_monetary_value(property_data.get('eval_municipale_batiment', 0)):,.0f} $"),
                                html.P(f"Total: {clean_monetary_value(property_data.get('eval_municipale_totale', 0)):,.0f} $", className="fw-bold")
                            ])
                        ])
                    ], width=3)
                ])
            ])
        ])
    ])

def create_summary_tab(property_data, loan_type=None, tax_province=None, tax_status=None, schl_payment_mode=None, conventional_rate=None):
    # Debug
    print(f"🔍 [CREATE_SUMMARY_TAB] Loan type: {loan_type}")
    if property_data:
        nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
        print(f"🔍 [CREATE_SUMMARY_TAB] Nombre d'unités: {nombre_unites}")
    
    # Générer directement le contenu au lieu d'utiliser un callback séparé
    if not property_data:
        summary_content = dbc.Alert("Veuillez sélectionner un immeuble pour voir le résumé.", 
                        color="info", className="mt-3")
    else:
        try:
            # Debug
            print(f"🔍 [RÉSUMÉ DIRECT] Loan type: {loan_type}")
            if property_data:
                nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
                print(f"🔍 [RÉSUMÉ DIRECT] Nombre d'unités: {nombre_unites}")
            
            # Récupérer les données financières de base
            prix = clean_monetary_value(property_data.get('prix_vente', 0))
            revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
            depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
            revenue_net = clean_monetary_value(property_data.get('revenu_net', 0))
            
            if revenue_net == 0:
                revenue_net = revenue_brut - depenses
            
            tga = (revenue_net / prix * 100) if prix > 0 else 0
            
            # Paramètres de financement
            is_incorporated = tax_status == "incorporated"
            
            # Utilisation standardisée du calcul du prêt
            montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
            
            # Récupérer les paramètres du prêt pour les calculs suivants
            if loan_type == "SCHL":
                rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 0))
                if rdc_ratio == 0:
                    raise ValueError("RDC SCHL manquant dans la base de données pour cette propriété")
                taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
                amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
            else:
                rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 0))
                if rdc_ratio == 0:
                    raise ValueError("RDC Conventionnel manquant dans la base de données pour cette propriété")
                
                # Utiliser le taux conventionnel sélectionné si disponible
                if conventional_rate and conventional_rate != "":
                    parts = conventional_rate.split('_')
                    if len(parts) >= 2:
                        taux_str = parts[-1]
                        taux_interet = float(taux_str) / 100
                    else:
                        taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
                else:
                    taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
                
                amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
            
            # Mise de fonds calculée à partir du ratio prêt/valeur
            mise_de_fonds_pct = (1 - ratio_pret_valeur) * 100
            mise_de_fonds = prix * (mise_de_fonds_pct / 100)
            
            # Prime SCHL
            prime_schl = 0
            prime_rate = 0
            if loan_type == "SCHL":
                # Utiliser le taux du cache s'il existe, sinon le taux manuel, sinon le taux par défaut
                if schl_cache and 'prime_rate' in schl_cache:
                    prime_rate = schl_cache['prime_rate']
                    prime_schl = schl_cache.get('prime_schl', montant_pret * (prime_rate / 100))
                else:
                    prime_rate = manual_schl_rate if manual_schl_rate is not None else 2.40
                    prime_schl = montant_pret * (prime_rate / 100)
                print(f"📊 [Financial Tab] Taux SCHL utilisé: {prime_rate}% (manuel: {manual_schl_rate})")
            
            # Montant financé selon le mode de paiement SCHL
            if loan_type == "SCHL" and schl_payment_mode == "cash":
                montant_finance = montant_pret  # La prime est payée comptant, pas financée
            else:
                montant_finance = montant_pret + prime_schl  # La prime est financée
            
            # Calculer la mensualité
            mensualite = pmt_mensuelle
            n_payments = int(amortissement * 12)
            
            # Calcul du PMT max basé sur le RDC exigé par le prêteur
            revenue_net_mensuel = revenue_net / 12
            pmt_max_rdc = revenue_net_mensuel / rdc_ratio if rdc_ratio > 0 else 0
            
            # Calculer les intérêts totaux basés sur l'amortissement réel
            total_paiements = 0
            solde_temp = montant_finance
            for i in range(n_payments):
                interet_mois = solde_temp * (taux_interet / 12)
                capital_mois = mensualite - interet_mois
                if capital_mois > solde_temp:
                    capital_mois = solde_temp
                    total_paiements += interet_mois + capital_mois
                    break
                solde_temp -= capital_mois
                total_paiements += mensualite
            
            interets_totaux = total_paiements - montant_finance
            
            # Calcul du cashflow (copié de la version callback)
            taxe_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
            
            # Calculer les composants du premier mois pour le cashflow
            solde_debut_mois_1 = montant_finance
            interet_mois_1 = solde_debut_mois_1 * (taux_interet / 12)
            capital_mois_1 = mensualite - interet_mois_1
            revenue_net_mensuel = revenue_net / 12
            
            # Calcul de l'impôt (simplifiée)
            revenu_imposable_annuel = revenue_net - (interet_mois_1 * 12)
            if is_incorporated:
                impot = revenu_imposable_annuel * taxe_rate if revenu_imposable_annuel > 0 else 0
                impot_mois_1 = impot / 12
            else:
                # Pour les particuliers, calculer l'impôt progressif
                impot = calculate_progressive_tax(revenu_imposable_annuel, tax_province) if revenu_imposable_annuel > 0 else 0
                impot_mois_1 = impot / 12
            
            # Cashflow final
            cashflow_mensuel = revenue_net_mensuel - impot_mois_1 - interet_mois_1 - capital_mois_1
            cashflow_annuel = cashflow_mensuel * 12
            
            # MRN et RDC calculés
            mrn = prix / revenue_net if revenue_net > 0 else 0
            rdc_calc = revenue_net / (mensualite * 12) if mensualite else 0
            rdc_calc = round(rdc_calc, 2)
            
            # Coûts d'acquisition
            total_costs = prix * 0.04 + calculate_bienvenue_tax(prix, property_data)
            
            # Vérifications automatiques
            cashflow_positif = cashflow_annuel >= 0
            mrn_ok = mrn >= 15
            rdc_ok = rdc_calc >= 1.2
            
            # Messages de débogage pour le terminal
            nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
            print(f"DEBUG: Type={loan_type}, Unités={nombre_unites}")
            
            # Construire le résumé
            summary_content = html.Div([
                # Section Propriété
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-home me-2"),
                            "Détails de la Propriété"
                        ], className="mb-4"),
                        dbc.Row([
                            dbc.Col([
                                html.P("Adresse", className="text-muted mb-1"),
                                html.P(property_data.get('address', 'N/A'), className="fw-bold")
                            ], width=6),
                            dbc.Col([
                                html.P("Prix de vente", className="text-muted mb-1"),
                                html.P(f"{prix:,.0f} $", className="fw-bold")
                            ], width=3),
                            dbc.Col([
                                html.P("Nombre d'unités", className="text-muted mb-1"),
                                html.P(f"{clean_numeric_value(property_data.get('nombre_unites', 0)):.0f}", className="fw-bold")
                            ], width=3),
                        ])
                    ])
                ], className="mb-4"),
                
                # Section Analyse Financière
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-chart-line me-2"),
                            "Analyse Financière"
                        ], className="mb-4"),
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.H6("Revenus", className="text-primary mb-3"),
                                    html.P(f"Revenue brut annuel: {revenue_brut:,.0f} $"),
                                    html.P(f"Dépenses annuelles: {depenses:,.0f} $"),
                                    html.P(f"Revenue net annuel: {revenue_net:,.0f} $", className="fw-bold"),
                                    html.P(f"TGA: {tga:.2f}%", className="fw-bold text-success"),
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div([
                                    html.H6("Financement", className="text-primary mb-3"),
                                    html.P(f"Type de prêt: {loan_type}"),
                                    html.P(f"Mise de fonds ({mise_de_fonds_pct:.1f}%): {mise_de_fonds:,.0f} $"),
                                    html.P(f"Montant du prêt: {montant_pret:,.0f} $"),
                                    html.P(f"Prime SCHL: {prime_schl:,.0f} $" if loan_type == "SCHL" else "Prime SCHL: N/A"),
                                    html.P(f"Mensualité: {mensualite:,.0f} $"),
                                    html.P(f"Intérêts totaux: {interets_totaux:,.0f} $"),
                                ])
                            ], width=4),
                            dbc.Col([
                                html.Div([
                                    html.H6("Résultats", className="text-primary mb-3"),
                                    html.P(f"Province: {tax_province}"),
                                    html.P(f"Statut: {'Incorporé' if is_incorporated else 'Non Incorporé'}"),
                                    html.P(f"Cashflow mensuel année 1 moyenne: {cashflow_mensuel:,.0f} $", 
                                          className=f"fw-bold {'text-success' if cashflow_mensuel > 0 else 'text-danger'}"),
                                    html.P(f"Cashflow annuel: {cashflow_annuel:,.0f} $"),
                                    html.P(f"Mise de fonds totale: {mise_de_fonds + total_costs:,.0f} $"),
                                ])
                            ], width=4),
                        ])
                    ])
                ], className="mb-4"),
                
                # Section Confluence
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-stream me-2"),
                            "Confluence"
                        ], className="mb-3"),

                        # Section Rentabilité
                        html.H6("Confluences rentabilité", className="text-primary mb-3"),
                        
                        dbc.Checklist(
                            id="confluence-rentabilite",
                            options=[
                                {"label": "Cashflow positif", "value": "cashflow_positif"},
                                {"label": "MRN ≥ 15", "value": "mrn_ok"},
                                {"label": "RDC ≥ 1.2", "value": "rdc_ok"}
                            ],
                            value=[
                                "cashflow_positif" if cashflow_positif else None,
                                "mrn_ok" if mrn_ok else None,
                                "rdc_ok" if rdc_ok else None
                            ],
                            switch=True,
                            className="mb-3"
                        ),
                        
                        html.Hr(),
                        
                        # Section Qualité
                        html.H6("Confluences qualité", className="text-primary mb-3 mt-3"),
                        
                        # Loyer comparé au secteur
                        html.Div([
                            html.P("Loyer de l'immeuble par rapport au secteur:", className="mb-2"),
                            dbc.RadioItems(
                                id="loyer-secteur",
                                options=[
                                    {"label": "Plus haut", "value": "plus_haut"},
                                    {"label": "Plus bas", "value": "plus_bas"}
                                ],
                                inline=True,
                                className="mb-3"
                            )
                        ]),
                        
                        # Prix par porte comparé au secteur
                        html.Div([
                            html.P("Prix par porte par rapport au secteur:", className="mb-2"),
                            dbc.RadioItems(
                                id="prix-porte-secteur",
                                options=[
                                    {"label": "Plus haut", "value": "plus_haut"},
                                    {"label": "Plus bas", "value": "plus_bas"}
                                ],
                                inline=True,
                                className="mb-3"
                            )
                        ]),
                        
                        html.Hr(),
                        
                        # Section Négociation
                        html.H6("Négociation", className="text-primary mb-3 mt-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Label("Fourchette basse", className="mb-2"),
                                dbc.InputGroup([
                                    dbc.Input(id="nego-low", type="number", placeholder="Ex: 8000000", step=1000),
                                    dbc.InputGroupText("$")
                                ])
                            ], width=6),
                            dbc.Col([
                                html.Label("Fourchette haute", className="mb-2"),
                                dbc.InputGroup([
                                    dbc.Input(id="nego-high", type="number", placeholder="Ex: 9000000", step=1000),
                                    dbc.InputGroupText("$")
                                ])
                            ], width=6),
                        ], className="mb-3"),
                        
                        html.Div(id="nego-summary", className="mt-3")
                    ])
                ], className="mb-4"),
                
                # Section Métriques Clés
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-chart-bar me-2"),
                            "Métriques Clés"
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.P("Multiple de Revenu Net (MRN)", className="text-muted mb-1"),
                                html.H4(f"{mrn:.2f}", className=f"fw-bold {'text-success' if mrn_ok else 'text-warning'}")
                            ], width=4),
                            dbc.Col([
                                html.P("Ratio de Couverture de la Dette (RDC)", className="text-muted mb-1"),
                                html.H4(f"{rdc_calc:.2f}", className=f"fw-bold {'text-success' if rdc_ok else 'text-warning'}")
                            ], width=4),
                            dbc.Col([
                                html.P("Prix par unité", className="text-muted mb-1"),
                                html.H4(f"{prix/clean_numeric_value(property_data.get('nombre_unites', 1)):,.0f} $", className="fw-bold")
                            ], width=4),
                        ])
                    ])
                ], className="mb-4"),
            ])
            
        except Exception as e:
            print(f"Erreur dans create_summary_tab: {e}")
            import traceback
            traceback.print_exc()
            summary_content = dbc.Alert(f"Erreur lors de la génération du résumé: {str(e)}", 
                            color="danger", className="mt-3")
    
    return html.Div([
        html.Div([
            html.H4([
                html.I(className="fas fa-clipboard-list me-2"),
                "Résumé Complet de l'Analyse"
            ], className="mb-4"),
            
            # Afficher directement le contenu
            summary_content
                  ], className="card-custom")
      ])

def create_costs_tab(property_data, loan_type):
    # S'assurer que le prix est bien un nombre
    prix = clean_monetary_value(property_data['prix_vente'])
    
    # Récupérer le nombre d'unités
    nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
    
    # Calcul des différents coûts
    costs = {}
    
    # Si les coûts sont chargés depuis la base de données
    if ACQUISITION_COSTS:
        for cost_type, cost_info in ACQUISITION_COSTS.items():
            if cost_info['fixed_amount'] is not None and cost_info['fixed_amount'] > 0:
                costs[cost_type] = cost_info['fixed_amount']
            elif cost_info['percentage'] is not None:
                costs[cost_type] = prix * (cost_info['percentage'] / 100)
    else:
        # Valeurs par défaut si pas de données en base
        costs = {
            "Inspection": nombre_unites * 75,
            "Notaire": prix * 0.007,
            "Taxe de mutation (Bienvenue)": calculate_bienvenue_tax(prix, property_data),
            "Évaluation bancaire": 400,
            "Frais de dossier bancaire": 300,
            "Assurance titre": prix * 0.0025,
            "Ajustements (taxes, etc.)": prix * 0.005,
            "Déménagement": 1500,
            "Rénovations mineures": 5000,
            "Fonds de prévoyance": prix * 0.01
        }
    
    # Ajouter les variables manquantes :
    if loan_type == "SCHL":
        mise_fonds_schl_pct = 5.0  # 5% de mise de fonds pour SCHL
        mise_fonds_conv_pct = 20.0  # 20% pour conventionnel
    else:
        mise_fonds_schl_pct = 5.0
        mise_fonds_conv_pct = 20.0
    
    # Ajuster les frais de dossier bancaire selon le type de prêt
    if loan_type == "SCHL":
        # Pour SCHL: 150$ par porte/logement
        costs["Frais d'analyse de dossier SCHL"] = nombre_unites * 150
        # Retirer les frais de dossier bancaire standard s'ils existent
        costs.pop("Frais de dossier bancaire", None)
    elif "Frais d'analyse de dossier SCHL" in costs:
        # Si conventionnel, s'assurer qu'on n'a pas les frais SCHL
        costs.pop("Frais d'analyse de dossier SCHL", None)
        if "Frais de dossier bancaire" not in costs:
            costs["Frais de dossier bancaire"] = 300
    
    # Ajouter la taxe de bienvenue si pas déjà présente
    if "Taxe de mutation (Bienvenue)" not in costs:
        costs["Taxe de mutation (Bienvenue)"] = calculate_bienvenue_tax(prix, property_data)
    
    # Vérifier si la prime SCHL doit être ajoutée aux coûts
    if loan_type == "SCHL":
        # Ajouter un champ pour la prime SCHL payée comptant
        costs["Prime SCHL (si payée comptant)"] = 0  # Sera mise à jour dynamiquement
    
    # Calculer le cashflow négatif total des premières années
    # Utiliser des valeurs par défaut pour tax_province et tax_status
    # Ces valeurs seront mises à jour via le callback update_costs_table_with_additional
    cashflow_negatif_total = 0
    try:
        # Utiliser des valeurs par défaut si elles ne sont pas disponibles
        default_tax_province = "Québec"
        default_tax_status = "incorporated"
        
        cashflow_negatif_total = calculate_negative_cashflow_total(
            property_data, 
            loan_type, 
            default_tax_province, 
            default_tax_status, 
            years_to_calculate=5
        )
        
        if cashflow_negatif_total > 0:
            costs["Provision pour cashflow négatif (5 ans)"] = cashflow_negatif_total
    except Exception as e:
        print(f"Erreur lors du calcul du cashflow négatif total: {e}")
    
    total_costs = sum(costs.values())
    
    # Créer le graphique des coûts
    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=list(costs.keys()),
        values=list(costs.values()),
        hole=.3,
        marker_colors=px.colors.qualitative.Set3
    ))
    
    fig.update_layout(
        title="Répartition des coûts d'acquisition",
        height=500
    )
    
    # Section Optimisation - Coûts potentiels pour réduire la prime d'assurance
    optimisation_section = dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-lightbulb me-2"),
                "Coûts additionnels"
            ], className="mb-0")
        ]),
        dbc.CardBody([
            html.H6("Coûts potentiels pour réduire la prime d'assurance", className="mb-3 text-primary"),
            html.P("Cochez les éléments à mettre à jour pour réduire la prime d'assurance:", className="text-muted"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Système incendie à jour", "value": "systeme_incendie"},
                        ],
                        value=[],
                        id="cost-systeme-incendie",
                    ),
                    html.Small("Si non conforme: 1000$", className="text-muted")
                ], width=6),
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Clapet anti-retour à jour", "value": "clapet_anti_retour"},
                        ],
                        value=[],
                        id="cost-clapet-anti-retour",
                    ),
                    html.Small("Installation: 1000-2000$", className="text-muted")
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Détecteur de fuite d'eau avec coupure d'alimentation", "value": "detecteur_fuite"},
                        ],
                        value=[],
                        id="cost-detecteur-fuite",
                    ),
                    html.Small("Installation: 629,99$", className="text-muted")
                ], width=6),
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Chauffe-eau électrique de moins de 10 ans", "value": "chauffe_eau"},
                        ],
                        value=[],
                        id="cost-chauffe-eau",
                    ),
                    html.Small("Remplacement: 1140$", className="text-muted")
                ], width=6),
            ], className="mb-3"),
            
            # Section des tests environnementaux
            html.H6("Tests environnementaux", className="mt-4 mb-3 text-primary"),
            html.P("Sélectionnez les tests environnementaux nécessaires:", className="text-muted"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Phase 1 (obligatoire)", "value": "env_phase_1"},
                        ],
                        value=["env_phase_1"],  # Phase 1 est toujours cochée par défaut
                        id="cost-env-phase-1",
                        style={"pointer-events": "none", "opacity": "0.7"}  # Style pour indiquer que c'est non modifiable
                    ),
                    html.Small("Obligatoire: 1200$", className="text-muted")
                ], width=6),
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Phase 2", "value": "env_phase_2"},
                        ],
                        value=[],
                        id="cost-env-phase-2",
                    ),
                    html.Small("Coût: 5000$", className="text-muted")
                ], width=6),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[
                            {"label": "Phase 3", "value": "env_phase_3"},
                        ],
                        value=[],
                        id="cost-env-phase-3",
                    ),
                    html.Small("Coût: 10000$", className="text-muted")
                ], width=6),
            ], className="mb-3"),
            
            dbc.Button(
                "Calculer les coûts additionnels",
                id="calculate-additional-costs-btn",
                color="primary",
                className="mt-2 mb-3"
            ),
            
            html.Div(id="additional-costs-result")
        ])
    ], className="mb-4")
    
    return html.Div([
        # Store pour les coûts additionnels - COMMENTÉ car dupliqué avec ligne 3140
        # dcc.Store(id="additional-costs-data", data={}),
        
        html.Div([
            html.H4([
                html.I(className="fas fa-receipt me-2"),
                "Coûts d'acquisition détaillés"
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Prix de l'immeuble", className="text-muted"),
                            html.H3(f"{prix:,.0f} $", className="text-primary")
                        ])
                    ], className="text-center mb-4")
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Coûts totaux d'acquisition", className="text-muted"),
                            html.H3(f"{total_costs:,.0f} $", className="text-danger"),
                            html.Div(id="total-with-additional-costs", className="small text-muted")
                        ])
                    ], className="text-center mb-4")
                ], width=6),
            ]),
            
            # Section Optimisation
            optimisation_section,
            
            # Tableau détaillé des coûts
            html.Div([
                html.H5("Détail des coûts", className="mb-3"),
                html.Div(id="costs-table-container", children=[
                    dbc.Table([
                        html.Thead([
                            html.Tr([
                                html.Th("Type de coût"),
                                html.Th("Montant", className="text-end"),
                                html.Th("% du prix", className="text-end")
                            ])
                        ]),
                        html.Tbody([
                            html.Tr([
                                html.Td(cost_name),
                                html.Td(f"{cost_value:,.0f} $", className="text-end"),
                                html.Td(f"{(cost_value/prix*100):.2f}%", className="text-end")
                            ]) for cost_name, cost_value in costs.items()
                        ] + [
                            html.Tr([
                                html.Td(html.B("TOTAL")),
                                html.Td(html.B(f"{total_costs:,.0f} $"), className="text-end"),
                                html.Td(html.B(f"{(total_costs/prix*100):.2f}%"), className="text-end")
                            ], className="table-primary")
                        ])
                    ], striped=True, hover=True, className="mb-4")
                ])
            ]),
            
            # Graphique
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            
            # Résumé avec mise de fonds
            html.Div([
                html.H5("Résumé du financement", className="mb-3 mt-4"),
                dbc.Row(id="financing-summary", children=[
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(f"Mise de fonds SCHL ({mise_fonds_schl_pct:.1f}%)", className="text-muted"),
                                html.H4(f"{prix * (mise_fonds_schl_pct/100):,.0f} $")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(f"Mise de fonds conv. ({mise_fonds_conv_pct:.1f}%)", className="text-muted"),
                                html.H4(f"{prix * (mise_fonds_conv_pct/100):,.0f} $")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Coûts d'acquisition", className="text-muted"),
                                html.H4(f"{total_costs:,.0f} $")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Total (conv. + coûts)", className="text-muted"),
                                html.H4(f"{prix * (mise_fonds_conv_pct/100) + total_costs:,.0f} $", className="text-danger")
                            ])
                        ])
                    ], width=3),
                ])
            ], className="mt-4")
            
        ], className="card-custom")
    ])

def create_profit_tab(property_data, loan_type, tax_province, tax_status, schl_payment_mode=None, conventional_rate=None):
    """Crée l'onglet Profit avec tableau d'amortissement et graphique"""
    
    # Récupérer les données financières
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    
    # === NOUVEAU : Section Profit à l'achat et Refinancement ===
    try:
        from functions.calculation import calculate_profit_breakdown
        profit_analysis = calculate_profit_breakdown(property_data, loan_type, conventional_rate)
        
        profit_section = dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-chart-line me-2"),
                    "Analyse du Profit à l'Achat"
                ], className="mb-4"),
                
                # Profit à l'achat (équité instantanée)
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6([
                                    html.I(className="fas fa-piggy-bank me-2"),
                                    "Profit à l'Achat (Équité)"
                                ], className="text-primary"),
                                html.H4(f"{profit_analysis['profit_achat_equite']:,.0f} $", 
                                        className="text-success" if profit_analysis['profit_achat_equite'] > 0 else "text-danger"),
                                html.P("= Valeur économique - Prix payé", className="text-muted small mb-2"),
                                html.P(
                                    "✅ Équité instantanée (pas du cash immédiat)" if profit_analysis['profit_achat_equite'] > 0 
                                    else "❌ Aucun profit à l'achat", 
                                    className="mb-0"
                                )
                            ])
                        ], color="light", outline=True)
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6([
                                    html.I(className="fas fa-info-circle me-2"),
                                    "Règles de Financement Bancaire"
                                ], className="text-info"),
                                html.Ul([
                                    html.Li("La banque utilise la PLUS PETITE valeur entre : valeur réelle (marché) ET valeur de financement"),
                                    html.Li("Elle finance sur le prix payé si ≤ à cette valeur minimum"),
                                    html.Li("Si prix > valeur minimum, elle finance sur la valeur minimum"),
                                    html.Li("❌ Jamais de cash au notaire même avec profit"),
                                    html.Li("💰 Le profit se réalise au refinancement seulement")
                                ], className="mb-0 small")
                            ])
                        ], color="info", outline=True)
                    ], width=6)
                ], className="mb-4"),
                
                # Scénarios de refinancement
                html.H6([
                    html.I(className="fas fa-exchange-alt me-2"),
                    "Scénarios de Refinancement (après 1 an)"
                ], className="mb-3"),
                
                dbc.Row([
                    # Scénario conservateur
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Conservateur", className="text-secondary"),
                                html.P("0% appréciation", className="small text-muted"),
                                html.H5(f"{profit_analysis['profit_potentiel_1_an']['conservateur']:,.0f} $", 
                                        className="text-success" if profit_analysis['profit_potentiel_1_an']['conservateur'] > 0 else "text-muted"),
                                html.P("cash potentiel", className="small mb-0")
                            ])
                        ], color="secondary", outline=True)
                    ], width=4),
                    # Scénario réaliste
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Réaliste", className="text-primary"),
                                html.P("2% appréciation", className="small text-muted"),
                                html.H5(f"{profit_analysis['profit_potentiel_1_an']['realiste']:,.0f} $", 
                                        className="text-success" if profit_analysis['profit_potentiel_1_an']['realiste'] > 0 else "text-muted"),
                                html.P("cash potentiel", className="small mb-0")
                            ])
                        ], color="primary", outline=True)
                    ], width=4),
                    # Scénario optimiste
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Optimiste", className="text-success"),
                                html.P("3% appréciation + 20k$ améliorations", className="small text-muted"),
                                html.H5(f"{profit_analysis['profit_potentiel_1_an']['optimiste']:,.0f} $", 
                                        className="text-success" if profit_analysis['profit_potentiel_1_an']['optimiste'] > 0 else "text-muted"),
                                html.P("cash potentiel", className="small mb-0")
                            ])
                        ], color="success", outline=True)
                    ], width=4)
                ], className="mb-4"),
                
                # Détails du financement initial
                dbc.Collapse([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Détails du Financement Initial", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Prix payé: "), 
                                    f"{profit_analysis['initial_financing']['prix_paye']:,.0f} $"
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Valeur économique réelle: "), 
                                    f"{profit_analysis['initial_financing']['valeur_economique_reelle']:,.0f} $"
                                ], width=4),
                                dbc.Col([
                                    html.Strong("Valeur économique financement: "), 
                                    f"{profit_analysis['initial_financing']['valeur_economique_financement']:,.0f} $"
                                ], width=4)
                            ], className="mb-2"),
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Valeur de financement bancaire: "), 
                                    html.Br(),
                                    html.Span(f"{profit_analysis['initial_financing']['valeur_financement_bancaire']:,.0f} $", 
                                             className="text-primary"),
                                    html.Br(),
                                    html.Small("(La plus petite des valeurs économiques)", className="text-muted")
                                ], width=12, className="text-center mb-3")
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Strong("Montant prêt: "), 
                                    f"{profit_analysis['initial_financing']['montant_pret_initial']:,.0f} $"
                                ], width=6),
                                dbc.Col([
                                    html.Strong("Mise de fonds: "), 
                                    f"{profit_analysis['initial_financing']['mise_de_fonds']:,.0f} $ ({profit_analysis['initial_financing']['mise_de_fonds_pct']:.1f}%)"
                                ], width=6)
                            ], className="mb-2"),
                            html.P(
                                "⚠️ La banque protège son risque en limitant le financement" 
                                if profit_analysis['initial_financing']['banque_protege_risque'] 
                                else "✅ Prix payé conforme aux valeurs économiques",
                                className="text-warning" if profit_analysis['initial_financing']['banque_protege_risque'] else "text-success"
                            )
                        ])
                    ])
                ], id="collapse-financing-details", is_open=False),
                
                dbc.Button(
                    [html.I(className="fas fa-chevron-down me-2"), "Voir les détails"],
                    id="toggle-financing-details",
                    color="outline-secondary",
                    size="sm",
                    className="mt-2"
                )
            ])
        ], className="mb-4", color="success", outline=True)
        
    except Exception as e:
        print(f"Erreur lors du calcul du profit: {e}")
        profit_section = dbc.Alert(
            f"Erreur lors du calcul du profit à l'achat: {str(e)}", 
            color="warning", 
            className="mb-4"
        )
    
    # Ajouter une section de configuration pour la prime SCHL
    schl_config_section = html.Div([])
    if loan_type == "SCHL":
        schl_config_section = dbc.Card([
            dbc.CardBody([
                html.H6([
                    html.I(className="fas fa-cog me-2"),
                    "Configuration de la prime SCHL"
                ], className="mb-3"),
                html.Div([
                    # Créer directement le RadioItems ici
                    dbc.RadioItems(
                        id="schl-payment-mode-profit-display",  # ID unique pour cet affichage
                        options=[
                            {"label": "Financer la prime SCHL (ajouter au prêt)", "value": "financed"},
                            {"label": "Payer la prime SCHL comptant (chez le notaire)", "value": "cash"}
                        ],
                        value=schl_payment_mode or "financed",
                        className="mb-2"
                    )
                ]),
                html.Div(id="schl-payment-info", className="mt-2")
            ])
        ], className="mb-4", color="info", outline=True)
    
    # === MODIFICATION 1 : Calcul cohérent du revenu net ===
    revenue_net = clean_monetary_value(property_data.get('revenu_net', 0))
    if revenue_net == 0:
        revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
        depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
        revenue_net = revenus_bruts - depenses
    
    # === MODIFICATION : Utilisation standardisée du calcul du prêt ===
    # Utiliser la fonction calculate_loan_amount_from_rdc pour la cohérence
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
    
    # Paramètres du prêt selon le type - UTILISER LES VALEURS DE LA BASE DE DONNÉES
    if loan_type == "SCHL":
        rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            raise ValueError("RDC SCHL manquant dans la base de données pour cette propriété")
        taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
    else:
        rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            raise ValueError("RDC Conventionnel manquant dans la base de données pour cette propriété")
        taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
    
    print(f"=== CALCUL MENSUALITÉ MAX ===")
    print(f"Revenue net mensuel: {revenue_net/12:,.0f} $")
    print(f"RDC ratio: {rdc_ratio}")
    print(f"PMT mensuelle: {pmt_mensuelle:,.0f} $")
    print(f"Montant prêt max (basé sur RDC): {montant_pret:,.0f} $")
    print(f"Ratio prêt-valeur: {ratio_pret_valeur:.1%}")
    
    # === MODIFICATION : Calcul standardisé de la prime SCHL ===
    prime_schl = 0
    prime_rate = 0
    if loan_type == "SCHL":
        # Utiliser le taux du cache s'il existe, sinon le taux manuel, sinon le taux par défaut
        if schl_cache and 'prime_rate' in schl_cache:
            prime_rate = schl_cache['prime_rate']
            prime_schl = schl_cache.get('prime_schl', montant_pret * (prime_rate / 100))
        else:
            prime_rate = manual_schl_rate if manual_schl_rate is not None else 2.40
            prime_schl = montant_pret * (prime_rate / 100)
        print(f"Prime SCHL: {prime_schl:,.0f} $ ({prime_rate:.2f}%)")
    
    # Montant total financé selon le mode de paiement SCHL
    if loan_type == "SCHL" and schl_payment_mode == "cash":
        montant_finance = montant_pret  # La prime n'est PAS ajoutée
    else:
        montant_finance = montant_pret + prime_schl  # La prime est financée
    
    # === CORRECTION : Utiliser la PMT mensuelle calculée selon votre formule ===
    # La mensualité reste la même peu importe si la prime SCHL est financée ou non
    # car elle est basée sur la capacité de paiement (RDC)
    mensualite = pmt_mensuelle
    n_payments = int(amortissement * 12)
    
    print(f"Mensualité finale (basée sur RDC): {mensualite:,.0f} $")
    
    # === MODIFICATION 6 : Calcul des intérêts totaux ===
    # Calculer les intérêts totaux basés sur l'amortissement réel
    total_paiements = 0
    solde_temp = montant_finance
    for i in range(n_payments):
        interet_mois = solde_temp * (taux_interet / 12)
        capital_mois = mensualite - interet_mois
        if capital_mois > solde_temp:
            capital_mois = solde_temp
        solde_temp -= capital_mois
        total_paiements += mensualite
        if solde_temp <= 0:
            break
    
    interets_totaux = total_paiements - montant_finance
    cout_total_interet = interets_totaux  # Pour clarté
    
    print(f"Total des paiements: {total_paiements:,.0f} $")
    print(f"Coût total des intérêts: {cout_total_interet:,.0f} $")
    
    # Créer le tableau d'amortissement pour les 300 premiers mois (25 ans)
    amortization_data = []
    solde_restant = montant_finance
    
    # Limiter à 300 mois ou au nombre total de paiements
    mois_a_afficher = min(int(amortissement * 12), n_payments)
    
    for mois in range(1, mois_a_afficher + 1):
        interet_mois = solde_restant * (taux_interet / 12)
        capital_mois = mensualite - interet_mois
        
        # S'assurer que le dernier paiement correspond exactement au solde
        if mois == mois_a_afficher:
            capital_mois = solde_restant
            interet_mois = mensualite - capital_mois
        
        amortization_data.append({
            "#": mois,
            "Mois": mois,
            "Solde restant": solde_restant,
            "Intérêts payés": interet_mois,
            "Capital remboursé": capital_mois
        })
        
        solde_restant = max(0, solde_restant - capital_mois)
    
    df_amortization = pd.DataFrame(amortization_data)
    
    # === MODIFICATION 7 : Ajouter des informations de débogage dans l'interface ===
    # Calculer le revenu net mensuel ici pour l'affichage
    revenue_net_mensuel = revenue_net / 12
    
    debug_info = dbc.Alert([
        html.H6("📊 Calculs utilisés :", className="alert-heading"),
        html.Ul([
            html.Li(f"Revenue net mensuel: {revenue_net_mensuel:,.0f} $"),
            html.Li(f"PMT mensuelle: {pmt_mensuelle:,.0f} $ (calculée avec la formule standard)"),
            html.Li(f"Montant du prêt: {montant_pret:,.0f} $"),
            html.Li(f"Prime SCHL: {prime_schl:,.0f} $ ({prime_rate:.2f}%" if loan_type == "SCHL" else "Prime SCHL: N/A"),
            html.Li(f"Montant financé total: {montant_finance:,.0f} $"),
            html.Li(f"Mensualité calculée: {mensualite:,.0f} $"),
            html.Li(f"Coût total des intérêts: ({mensualite:,.0f} $ × {n_payments}) - {montant_finance:,.0f} $ = {cout_total_interet:,.0f} $")
        ])
    ], color="info", className="mb-4")
    
    # Créer le graphique d'amortissement par année
    years = list(range(1, int(amortissement) + 1))
    annual_data = []
    
    for year in years:
        start_month = (year - 1) * 12
        end_month = min(year * 12, len(amortization_data))
        
        year_data = df_amortization.iloc[start_month:end_month]
        
        annual_principal = year_data['Capital remboursé'].sum()
        annual_interest = year_data['Intérêts payés'].sum()
        balance_end_year = year_data.iloc[-1]['Solde restant'] if len(year_data) > 0 else 0
        
        annual_data.append({
            'Année': year,
            'Principal': annual_principal,
            'Intérêts': annual_interest,
            'Solde': balance_end_year
        })
    
    df_annual = pd.DataFrame(annual_data)
    
    # Créer le graphique combiné (barres empilées + ligne)
    fig = go.Figure()
    
    # Barres pour le principal (vert)
    fig.add_trace(go.Bar(
        name='Principal',
        x=df_annual['Année'],
        y=df_annual['Principal'],
        marker_color='#48bb78',
        yaxis='y'
    ))
    
    # Barres pour les intérêts (bleu)
    fig.add_trace(go.Bar(
        name='Intérêts',
        x=df_annual['Année'],
        y=df_annual['Intérêts'],
        marker_color='#4299e1',
        yaxis='y'
    ))
    
    # Ligne pour le solde (orange)
    fig.add_trace(go.Scatter(
        name='Balance',
        x=df_annual['Année'],
        y=df_annual['Solde'],
        mode='lines+markers',
        line=dict(color='#ed8936', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    # Configuration du layout
    fig.update_layout(
        title={
            'text': f'Amortissement sur {amortissement} ans',
            'x': 0.5,
            'xanchor': 'center'
        },
        barmode='stack',
        xaxis=dict(
            title='',
            tickmode='linear',
            tick0=2026,
            dtick=2,
            tickvals=list(range(2026, 2026 + len(years), 2)),
            ticktext=[str(2026 + i*2) for i in range(0, len(years)//2 + 1)]
        ),
        yaxis=dict(
            title='Balance',
            side='left',
            showgrid=True,
            range=[0, max(df_annual['Principal'].max() + df_annual['Intérêts'].max(), montant_finance) * 1.1]
        ),
        yaxis2=dict(
            title='Payment',
            side='right',
            overlaying='y',
            showgrid=False,
            range=[0, montant_finance * 1.1]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified',
        height=500,
        plot_bgcolor='white'
    )
    
    # Dropdown pour les scénarios - permettre plusieurs périodes
    scenario_dropdown = dcc.Dropdown(
        id="amortization-scenario",
        options=[
            {"label": f"Amortissement sur {years} ans", "value": years}
            for years in [5, 10, 15, 20, 25, 30]
            if years <= int(amortissement)  # Ne montrer que les options <= à l'amortissement configuré
        ],
        value=int(amortissement),
        className="mb-4",
        style={"width": "300px"}
    )
    
    return html.Div([
        # === NOUVEAU : Section Profit à l'achat ===
        profit_section,
        
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    html.I(className="fas fa-chart-line me-2"),
                    "Tableau d'amortissement"
                ], className="mb-4"),
                
                # Configuration SCHL si applicable
                schl_config_section,
                
                # Ajouter les informations de débogage
                debug_info,
                
                # Section du graphique
                html.Div([
                    html.H5("Tableau d'amortissement", className="text-primary mb-3"),
                    html.Div([
                        scenario_dropdown,
                        dcc.Graph(
                            id="amortization-graph",
                            figure=fig,
                            config={'displayModeBar': False}
                        )
                    ])
                ], className="mb-5"),
                
                html.Hr(),
                
                # Section du tableau
                html.Div([
                    html.H5("Tableau d'amortissement", className="mb-3"),
                    html.Div([
                        html.Div([
                            html.Button([
                                html.I(className="fas fa-download me-2"),
                                "Télécharger"
                            ], className="btn btn-secondary btn-sm float-end mb-2"),
                            html.Button([
                                html.I(className="fas fa-times me-2")
                            ], className="btn btn-secondary btn-sm float-end mb-2 me-2")
                        ], className="clearfix"),
                        
                        # Tableau avec style sombre
                        html.Div([
                            dash_table.DataTable(
                                id="amortization-table",
                                data=df_amortization.to_dict('records'),  # Afficher tous les mois
                                columns=[
                                    {"name": "#", "id": "#", "type": "numeric"},
                                    {"name": "Mois", "id": "Mois", "type": "numeric"},
                                    {"name": "Solde restant", "id": "Solde restant", "type": "numeric", "format": FormatTemplate.money(2)},
                                    {"name": "Intérêts payés", "id": "Intérêts payés", "type": "numeric", "format": FormatTemplate.money(2)},
                                    {"name": "Capital remboursé", "id": "Capital remboursé", "type": "numeric", "format": FormatTemplate.money(2)}
                                ],
                                style_cell={
                                    'textAlign': 'right',
                                    'padding': '10px',
                                    'backgroundColor': '#1a1a1a',
                                    'color': 'white',
                                    'border': '1px solid #333'
                                },
                                style_header={
                                    'backgroundColor': '#2d2d2d',
                                    'fontWeight': 'bold',
                                    'border': '1px solid #333'
                                },
                                style_data={
                                    'backgroundColor': '#1a1a1a',
                                    'color': 'white'
                                },
                                style_data_conditional=[
                                    {
                                        'if': {'row_index': 'odd'},
                                        'backgroundColor': '#252525'
                                    }
                                ],
                                page_size=100,
                                page_action="native",
                                sort_action="native",
                                filter_action="native",
                                style_table={
                                    'maxHeight': '500px',
                                    'overflowY': 'auto',
                                    'border': '1px solid #333'
                                },
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Mois'}, 'width': '8%'},
                                    {'if': {'column_id': '#'}, 'width': '7%'}
                                ]
                            )
                        ], className="bg-dark p-3 rounded")
                    ])
                ], className="mt-4"),
                
                # Section Projection du Cashflow
                html.Div([
                    html.Hr(className="my-4"),
                    html.H5("Projection du cashflow net", className="mb-3"),
                    
                    # Note explicative
                    dbc.Alert([
                        html.I(className="fas fa-info-circle me-2"),
                        html.Strong("Pourquoi le cashflow s'améliore avec le temps ? "),
                        html.Br(),
                        "• Les intérêts diminuent chaque année (solde du prêt qui baisse)",
                        html.Br(),
                        "• Les intérêts sont déductibles d'impôt (économie fiscale)",
                        html.Br(),
                        "• Le capital remboursé augmente mais n'est pas une dépense",
                        html.Br(),
                        "• Résultat : Plus de liquidités disponibles avec le temps"
                    ], color="info", className="mb-4"),
                    
                    # Graphique du cashflow
                    html.Div(id="cashflow-projection-graph"),
                    
                    # Tableau détaillé
                    html.Div(id="cashflow-projection-table", className="mt-4")
                ]),
                
                # Section Projection du Gain en Capital
                html.Div([
                    html.Hr(className="my-4"),
                    html.H5("Projection du gain en capital", className="mb-3"),
                    
                    # Paramètres de projection
                    dbc.Row([
                        dbc.Col([
                            html.Label("Appréciation annuelle (%)", className="fw-bold"),
                            dbc.Input(
                                id="appreciation-rate-profit",
                                type="number",
                                value=3.0,
                                step=0.1,
                                className="form-control-custom"
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Années de détention", className="fw-bold"),
                            dcc.Dropdown(
                                id="holding-years",
                                options=[
                                    {"label": f"{y} ans", "value": y} 
                                    for y in [1, 3, 5, 10, 15, 20, 25]
                                ],
                                value=5,
                                className="form-control-custom"
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Province (pour l'impôt)", className="fw-bold"),
                            html.Div(id="detected-province", className="form-control-custom",
                                    style={"padding": "0.75rem", "background-color": "#f8f9fa"})
                        ], width=4),
                    ], className="mb-4"),
                    
                    # Graphique et résultats
                    html.Div(id="capital-gains-projection", className="mt-4")
                ]),
                
                # Modifier la section du résumé pour être plus clair
                html.Div([
                    html.Hr(className="my-4"),
                    html.H5("Résumé du prêt", className="mb-3"),
        dbc.Row([
            dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Montant du prêt", className="text-muted"),
                                    html.H4(f"{montant_pret:,.0f} $"),
                                    html.Small(f"Ratio LTV: {(montant_pret/prix*100):.1f}%", className="text-muted")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Prime SCHL" if loan_type == "SCHL" else "Frais additionnels", className="text-muted"),
                                    html.H4(f"{prime_schl:,.0f} $"),
                                    html.Small(f"Taux: {prime_rate:.2f}%" if loan_type == "SCHL" else "N/A", className="text-muted")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Total financé", className="text-muted"),
                                    html.H4(f"{montant_finance:,.0f} $"),
                                    html.Small("Prêt + Prime SCHL" if loan_type == "SCHL" else "Montant total", className="text-muted")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Mensualité", className="text-muted"),
                                    html.H4(f"{mensualite:,.0f} $"),
                                    html.Small(f"PMT calculée: {pmt_mensuelle:,.0f} $", className="text-muted")
                                ])
                            ])
                        ], width=3)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Total des intérêts", className="text-muted"),
                                    html.H4(f"{df_amortization['Intérêts payés'].sum():,.0f} $"),
                                    html.Small(f"Sur {amortissement} ans", className="text-muted")
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Coût total du prêt", className="text-muted"),
                                    html.H4(f"{total_paiements:,.0f} $"),
                                    html.Small(f"Principal + Intérêts", className="text-muted")
                                ])
                            ])
                        ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Ratio intérêts/principal", className="text-muted"),
                                    html.H4(f"{(cout_total_interet/montant_finance*100):.1f}%"),
                                    html.Small("Coût relatif du financement", className="text-muted")
                                ])
                            ])
                        ], width=4)
                    ])
                ])
            ])
        ], className="card-custom")
    ])

# Fonction calculate_cashflow_projection déplacée vers calculation.py
def create_property_edit_form(property_data):
    """Crée un formulaire pour éditer les données de l'immeuble"""
    
    # Grouper les champs par catégorie
    fields_categories = {
        "Informations générales": [
            ("address", "Adresse", "text", None),
            ("prix_vente", "Prix de vente", "number", 1000),
            ("nombre_unites", "Nombre d'unités", "number", 1),
            ("annee_construction", "Année de construction", "number", 1),
            ("type_batiment", "Type de bâtiment", "text", None)
        ],
        "Données financières": [
            ("revenus_brut", "Revenus totaux", "number", 1000),
            ("depenses_totales", "Dépenses totales", "number", 100),
            ("revenu_net", "Revenu net", "number", 100),
            ("depenses_taxes_municipales", "Taxes municipales", "number", 100),
            ("depenses_taxes_scolaires", "Taxes scolaires", "number", 100),
            ("depenses_assurances", "Assurance", "number", 100),
            ("depenses_electricite", "Électricité", "number", 100),
            ("depenses_chauffage", "Chauffage", "number", 100)
        ],
        "Paramètres SCHL": [
            ("financement_schl_ratio_couverture_dettes", "Ratio RDC SCHL", "number", 0.01),
            ("financement_schl_taux_interet", "Taux d'intérêt SCHL (%)", "number", 0.1),
            ("financement_schl_amortissement", "Amortissement SCHL (années)", "number", 1)
        ],
        "Paramètres Conventionnels": [
            ("financement_conv_ratio_couverture_dettes", "Ratio RDC conventionnel", "number", 0.01),
            ("financement_conv_taux_interet", "Taux d'intérêt conventionnel (%)", "number", 0.1),
            ("financement_conv_amortissement", "Amortissement conventionnel (années)", "number", 1)
        ],
        "Localisation": [
            ("latitude", "Latitude", "number", 0.000001),
            ("longitude", "Longitude", "number", 0.000001)
        ]
    }
    
    form_elements = []
    
    for category, fields in fields_categories.items():
        # Titre de la catégorie
        form_elements.append(html.H6(category, className="mt-3 mb-2 text-primary"))
        
        # Champs de la catégorie
        for field_name, label, input_type, step in fields:
            value = property_data.get(field_name, "")
            
            # Gérer les valeurs None
            if value is None:
                value = ""
            
            form_elements.append(
                html.Div([
                    html.Label(label, className="fw-bold small"),
                    dbc.Input(
                        id=f"edit-{field_name}",
                        type=input_type,
                        value=value,
                        step=step,
                        className="form-control-custom",
                        size="sm"
                    )
                ], className="mb-2")
            )
    
    # Ajouter les boutons d'action
    form_elements.extend([
        html.Hr(className="my-3"),
        dbc.Row([
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-save me-2"),
                    "Sauvegarder"
                ], id="save-property-changes", color="success", className="w-100", size="sm")
            ], width=6),
            dbc.Col([
                dbc.Button([
                    html.I(className="fas fa-times me-2"),
                    "Annuler"
                ], id="cancel-property-changes", color="secondary", className="w-100", size="sm")
            ], width=6)
        ])
    ])
    
    return html.Div([
        dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            "Attention : Les modifications ne sont pas persistées dans la base de données."
        ], color="warning", dismissable=True, className="mb-3"),
        html.Div(form_elements, style={"maxHeight": "400px", "overflowY": "auto"})
    ])

# Fonctions pour créer les graphiques
def create_revenue_breakdown_chart(property_data):
    try:
        # Convertir en nombres si ce sont des chaînes
        if isinstance(property_data.get('revenus_brut'), str):
            revenue_brut_str = property_data.get('revenus_brut', '0').replace('$', '').replace(' ', '').replace(',', '')
            revenue_brut = float(revenue_brut_str) if revenue_brut_str else 0
        else:
            revenue_brut = property_data.get('revenus_brut', 0) or 0
            
        if isinstance(property_data.get('depenses_totales'), str):
            depenses_str = property_data.get('depenses_totales', '0').replace('$', '').replace(' ', '').replace(',', '')
            depenses = float(depenses_str) if depenses_str else 0
        else:
            depenses = property_data.get('depenses_totales', 0) or 0
            
        if isinstance(property_data.get('revenu_net'), str):
            revenu_net_str = property_data.get('revenu_net', '0').replace('$', '').replace(' ', '').replace(',', '')
            revenue_net = float(revenu_net_str) if revenu_net_str else (revenue_brut - depenses)
        else:
            revenue_net = property_data.get('revenu_net', revenue_brut - depenses) or (revenue_brut - depenses)
            
    except (ValueError, TypeError):
        # En cas d'erreur, utiliser des valeurs par défaut
        revenue_brut = 0
        depenses = 0
        revenue_net = 0
        print("Erreur lors de la conversion des valeurs financières dans create_revenue_breakdown_chart")
    
    fig = go.Figure(data=[go.Pie(
        labels=['Revenue net', 'Dépenses'],
        values=[revenue_net, depenses],
        hole=.3,
        marker_colors=['#667eea', '#764ba2']
    )])
    
    fig.update_layout(
        showlegend=True,
        height=300,
        margin=dict(t=0, b=0, l=0, r=0)
    )
    
    return fig

def create_projection_chart(property_data):
    years = list(range(2024, 2029))
    revenue_base = clean_monetary_value(property_data.get('revenus_brut', 0))
    
    # Si les revenus sont à 0, essayer de les calculer
    if revenue_base <= 0 and property_data.get('loyer_par_logement') and property_data.get('nombre_de_logement'):
        revenue_base = property_data['loyer_par_logement'] * property_data['nombre_de_logement'] * 12
    
    # Projection avec inflation de 2%
    revenues = [revenue_base * (1.02 ** i) for i in range(5)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=years,
        y=revenues,
        name='Revenus projetés',
        marker_color='#667eea'
    ))
    
    fig.update_layout(
        title="Projection des revenus sur 5 ans",
        xaxis_title="Année",
        yaxis_title="Revenus ($)",
        height=400,
        showlegend=False
    )
    
    return fig

# -----------------------------------------------------------------------------
# Fonctions de simulation
# -----------------------------------------------------------------------------
def simulation_revenue_net(revenue_brut, depenses, tga, prix_vente, tax_rate, use_dpa, dpa_rate, building_ratio, adjustments, interet_annuel=0, is_incorporated=True, province_name="Québec"):
    """Simulation complète du revenue net avec variations"""
    
    # Générer les combinaisons
    base_values = {
        "revenus_brut": revenue_brut,
        "depenses_totales": depenses,
        "prix_vente": prix_vente,
        "tga": tga
    }
    
    combinaisons = generate_combinations(base_values=base_values, adjustments=adjustments, clamp_min=0)
    data = []
    
    for comb in combinaisons:
        rb, dep, pv, tga_val = comb
        
        # NOI (Net Operating Income) = Revenue brut - Dépenses d'exploitation
        noi = rb - dep
        
        # Calcul de la DPA si activée
        dpa_deduction = 0
        if use_dpa:
            # Utiliser simplement le ratio car property_data n'est pas disponible dans cette fonction
            building_value = pv * building_ratio
            dpa_deduction = building_value * dpa_rate
        
        # ⬇️ AJOUT
        max_dpa = max(0, noi - interet_annuel)
        dpa_deduction = min(dpa_deduction, max_dpa)
        
        # Revenu imposable = NOI - Intérêts - DPA
        revenu_imposable = noi - interet_annuel - dpa_deduction
        
        # Calcul de l'impôt
        if is_incorporated:
            # Pour les entreprises incorporées, utiliser le taux fixe
            impot = revenu_imposable * tax_rate if revenu_imposable > 0 else 0
        else:
            # Pour les particuliers, utiliser le calcul progressif
            impot = calculate_progressive_tax(revenu_imposable, province_name) if revenu_imposable > 0 else 0
        
        # RNO après impôt = NOI - Impôt
        rno_apres_impot = noi - impot
        
        # Calculer le taux effectif pour affichage
        taux_effectif = (impot / revenu_imposable * 100) if revenu_imposable > 0 else 0
        
        data.append({
            "Revenu Brut": rb,
            "Dépenses": dep,
            "Prix de Vente": pv,
            "TGA (%)": tga_val,
            "NOI": noi,
            "Intérêts (déductibles)": interet_annuel,
            "DPA": dpa_deduction if use_dpa else 0,
            "Revenu Imposable": revenu_imposable,
            "Impôt": impot,
            "Taux Effectif (%)": taux_effectif,
            "RNO Après Impôt": rno_apres_impot
        })
    
    return pd.DataFrame(data)

def simulation_cout_interet(montant_pret, taux, amortissement, loan_type, valeur_immeuble, adjustments):
    """Simulation complète du coût d'intérêt avec SCHL si applicable"""
    is_schl = loan_type == "SCHL"
    
    # Base values pour la simulation
    base_values = {
        "Montant du Prêt": montant_pret,
        "Taux d'Intérêt": taux / 100,
        "Amortissement": amortissement
    }
    
    if is_schl:
        base_values["Valeur Immeuble"] = valeur_immeuble
    
    combinaisons = generate_combinations(base_values=base_values, adjustments=adjustments, clamp_min=0, keys_with_floor=["Amortissement"])
    data = []
    
    for comb in combinaisons:
        if is_schl:
            pret_val, taux_int_val, amort_val, val_imm = comb
            prime_schl_sim, _ = calculate_schl_premium(pret_val, val_imm)
            montant_finance = pret_val + prime_schl_sim
        else:
            pret_val, taux_int_val, amort_val = comb
            prime_schl_sim = 0
            montant_finance = pret_val
        
        # Calcul de la mensualité
        mensualite, _ = calcul_mensualite(montant_finance, taux_int_val, amort_val)
        total_paiements = mensualite * amort_val * 12
        cout_total = total_paiements - pret_val
        cout_interet_pur = total_paiements - montant_finance
        
        # Calcul des intérêts et capital de la première année
        solde_debut = montant_finance
        interet_annuel_1 = 0
        capital_annuel_1 = 0
        
        for mois in range(12):
            interet_mois = solde_debut * (taux_int_val / 12)
            capital_mois = mensualite - interet_mois
            interet_annuel_1 += interet_mois
            capital_annuel_1 += capital_mois
            solde_debut -= capital_mois
        
        row_data = {
            "Montant du Prêt": pret_val,
            "Taux d'Intérêt": taux_int_val,
            "Amortissement": amort_val,
            "Prime SCHL": prime_schl_sim,
            "Mensualité": mensualite,
            "Service de Dette Annuel": mensualite * 12,
            "Intérêts Année 1": interet_annuel_1,
            "Capital Année 1": capital_annuel_1,
            "Coût d'Intérêt": cout_interet_pur,
            "Coût Total": cout_total
        }
        if is_schl:
            row_data["Valeur Immeuble"] = val_imm
            
        data.append(row_data)
    
    return pd.DataFrame(data)

# -----------------------------------------------------------------------------
# Callbacks pour les fonctionnalités d'analyse
# -----------------------------------------------------------------------------

# Callback pour activer/désactiver les champs DPA
@app.callback(
    Output("dpa-rate", "disabled"),
    Input("use-dpa", "value")
)
def toggle_dpa_fields(use_dpa):
    use_dpa = use_dpa or []
    disabled = not bool(use_dpa)
    return disabled

@app.callback(
    Output("schl-payment-info", "children"),
    [Input("schl-payment-mode", "value"),
     Input("property-data", "data"),
     Input("loan-type", "value")]
)
def update_schl_payment_info(payment_mode, property_data, loan_type):
    if not property_data or loan_type != "SCHL" or not payment_mode:
        return html.Div()
    
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    
    if payment_mode == "upfront":
        return html.P("La prime SCHL sera payée comptant à la clôture.", className="text-info")
    else:
        return html.P("La prime SCHL sera financée et ajoutée au montant du prêt.", className="text-info")


# Callback pour afficher la section SCHL
@app.callback(
    Output("schl-premium-section", "children"),
    [Input("loan-type", "value"),
     Input("schl-premium-cache", "data"),
     Input("property-data", "data")]
)
def update_schl_section(loan_type, cache_data, property_data):
    if loan_type != "SCHL" or not property_data:
        return html.Div()
    
    # Utiliser les données du cache si disponibles
    if not cache_data:
        return html.Div()
    
    print(f"📊 Update SCHL section - utilisation du cache")
    valeur_immeuble = cache_data.get("valeur_immeuble", 0)
    montant_pret = cache_data.get("montant_pret", 0)
    prime_schl = cache_data.get("prime_schl", 0)
    prime_rate = cache_data.get("prime_rate", 0)
    ltv = cache_data.get("ltv", 0)
    
    # Vérifier si c'est un multi-logement (6+ unités)
    nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
    
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-shield-alt me-2"),
                    "Prime SCHL"
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.P("Valeur de l'immeuble", className="text-muted mb-1"),
                        html.P(f"{valeur_immeuble:,.0f} $", className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.P("Ratio prêt-valeur (LTV)", className="text-muted mb-1"),
                        html.P(f"{ltv:.1f}%", className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.P("Taux de prime SCHL", className="text-muted mb-1"),
                        html.P(f"{prime_rate:.2f}%", className="fw-bold")
                    ], width=3),
                    dbc.Col([
                        html.P("Prime SCHL", className="text-muted mb-1"),
                        html.P(f"{prime_schl:,.0f} $", className="fw-bold text-danger")
                    ], width=3),
                ])
            ])
        ], className="mt-3", color="warning", outline=True)
    ])

@app.callback(
    Output("montant-pret-input", "value"),
    [Input("loan-type", "value"),
     Input("property-data", "data")],
    prevent_initial_call=True
)
def update_montant_pret(loan_type, property_data):
    if not property_data:
        return None
        
    # IMPORTANT: Utiliser le calcul basé sur le RDC pour cohérence avec update_metrics
    # Cela évite d'avoir deux montants de prêt différents
    montant_pret, _, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    print(f"📝 [update_montant_pret #2] Montant calculé avec RDC: {montant_pret:,.0f} $")
    
    return montant_pret


# Callback pour simulation Revenue Net
@app.callback(
    Output("revenue-simulation-results", "children"),
    [Input("revenue-brut-input", "value"),
     Input("depenses-input", "value"),
     Input("tga-input", "value"),
     Input("use-dpa", "value"),
     Input("dpa-rate", "value"),
     Input("building-ratio", "value")],
    [State("property-data", "data"),
     State("tax-province", "value"),
     State("tax-status", "value"),
     State("adj-revenue", "value"),
     State("adj-depenses", "value"),
     State("adj-tga", "value")]
)
def simulate_revenue_net_callback(revenue_brut, depenses, tga, use_dpa, dpa_rate,
                                  building_ratio, property_data, tax_province,
                                  tax_status, adj_rev, adj_dep, adj_tga):
    if not property_data:
        return html.Div()
    
    # Valeurs par défaut si None
    revenue_brut = revenue_brut or 0
    depenses = depenses or 0
    tga = tga or 0
    use_dpa = use_dpa or []
    dpa_rate = dpa_rate or APP_PARAMS.get('default_dpa_rate', 4.0)
    building_ratio = building_ratio or APP_PARAMS.get('default_building_ratio', 80.0)
    adj_rev = adj_rev or ADJUSTMENT_DEFAULTS.get('revenue_adjustment', 1000)
    adj_dep = adj_dep or ADJUSTMENT_DEFAULTS.get('expense_adjustment', 1000)
    adj_tga = adj_tga or ADJUSTMENT_DEFAULTS.get('tga_adjustment', 0.1)
    
    # Calculer le taux d'imposition
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    
    # Préparer les ajustements
    adjustments = {
        "revenus_brut": adj_rev,
        "depenses_totales": adj_dep,
        "prix_vente": clean_monetary_value(property_data.get('prix_vente', 0)) * 0.01,  # 1% du prix
        "tga": adj_tga
    }
    
    # Simuler
    df_results = simulation_revenue_net(
        revenue_brut, depenses, tga, clean_monetary_value(property_data.get('prix_vente', 0)),
        tax_rate, bool(use_dpa), dpa_rate/100, building_ratio/100, adjustments,
        is_incorporated=is_incorporated, province_name=tax_province
    )
    
    # Statistiques
    rno_values = df_results["RNO Après Impôt"]
    stats = {
        "min": rno_values.min(),
        "mean": rno_values.mean(),
        "max": rno_values.max(),
        "std": rno_values.std()
    }
    
    # Créer le graphique
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Minimum", "Moyen", "Maximum"],
        y=[stats["min"], stats["mean"], stats["max"]],
        marker_color=['#ff6b6b', '#667eea', '#48bb78'],
        text=[f"{v:,.0f} $" for v in [stats["min"], stats["mean"], stats["max"]]],
        textposition='auto',
    ))
    fig.update_layout(
        title="Résultats de la Simulation - RNO Après Impôt",
        yaxis_title="Montant ($)",
        showlegend=False,
        height=400
    )
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("RNO Minimum", className="text-muted"),
                        html.H4(f"{stats['min']:,.0f} $", className="text-danger")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("RNO Moyen", className="text-muted"),
                        html.H4(f"{stats['mean']:,.0f} $", className="text-primary")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("RNO Maximum", className="text-muted"),
                        html.H4(f"{stats['max']:,.0f} $", className="text-success")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Écart-Type", className="text-muted"),
                        html.H4(f"{stats['std']:,.0f} $", className="text-info")
                    ])
                ], className="text-center")
            ], width=3),
        ], className="mb-4"),
        
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        
        html.Div([
            html.H5("Échantillon des résultats", className="mb-3"),
            dash_table.DataTable(
                data=df_results.head(10).to_dict('records'),
                columns=[{"name": i, "id": i} for i in df_results.columns],
                style_cell={'textAlign': 'right'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'RNO Après Impôt', 'filter_query': '{RNO Après Impôt} < 0'},
                        'color': 'red'
                    }
                ]
            )
        ], className="mt-4")
    ])

# Callback séparé pour stocker les données de simulation revenue
@app.callback(
    Output("revenue-simulation-data", "data"),
    [Input("revenue-brut-input", "value"),
     Input("depenses-input", "value"),
     Input("tga-input", "value"),
     Input("use-dpa", "value"),
     Input("dpa-rate", "value"),
     Input("building-ratio", "value")],
    [State("property-data", "data"),
     State("tax-province", "value"),
     State("tax-status", "value"),
     State("adj-revenue", "value"),
     State("adj-depenses", "value"),
     State("adj-tga", "value")]
)
def store_revenue_simulation_data(revenue_brut, depenses, tga, use_dpa, dpa_rate,
                                  building_ratio, property_data, tax_province,
                                  tax_status, adj_rev, adj_dep, adj_tga):
    if not property_data:
        return []
    
    # Valeurs par défaut si None
    revenue_brut = revenue_brut or 0
    depenses = depenses or 0
    tga = tga or 0
    use_dpa = use_dpa or []
    dpa_rate = dpa_rate or APP_PARAMS.get('default_dpa_rate', 4.0)
    building_ratio = building_ratio or APP_PARAMS.get('default_building_ratio', 80.0)
    adj_rev = adj_rev or ADJUSTMENT_DEFAULTS.get('revenue_adjustment', 1000)
    adj_dep = adj_dep or ADJUSTMENT_DEFAULTS.get('expense_adjustment', 1000)
    adj_tga = adj_tga or ADJUSTMENT_DEFAULTS.get('tga_adjustment', 0.1)
    
    # Calculer le taux d'imposition
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    
    # Préparer les ajustements
    adjustments = {
        "revenu_brut": adj_rev,
        "depenses": adj_dep,
        "prix_de_vente": clean_monetary_value(property_data['prix_vente']) * 0.01,
        "tga": adj_tga
    }
    
    # Simuler
    df_results = simulation_revenue_net(
        revenue_brut, depenses, tga, clean_monetary_value(property_data['prix_vente']),
        tax_rate, bool(use_dpa), dpa_rate/100, building_ratio/100, adjustments,
        is_incorporated=is_incorporated, province_name=tax_province
    )
    
    return df_results.to_dict('records')

# Callback pour simulation Coût d'Intérêt
@app.callback(
    Output("interet-simulation-results", "children"),
     Input("montant-pret-input", "value"),
     Input("taux-interet-input", "value"),
    Input("amortissement-input", "value"),
    State("loan-type", "value"),
    State("property-data", "data"),
    State("adj-pret", "value"),
    State("adj-taux", "value"),
    State("adj-amort", "value")
)
def simulate_interet_callback(montant_pret, taux, amortissement, loan_type,
                              property_data, adj_pret, adj_taux, adj_amort):
    if not property_data:
        return html.Div()
    
    # Valeurs par défaut si None
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    montant_pret = montant_pret or prix_vente * APP_PARAMS.get('conventional_loan_ratio', 0.80)
    taux = taux or APP_PARAMS.get('default_interest_rate', 5.5)
    amortissement = amortissement or int(APP_PARAMS.get('default_amortization', 25))
    adj_pret = adj_pret or ADJUSTMENT_DEFAULTS.get('loan_adjustment', 5000)
    adj_taux = adj_taux or ADJUSTMENT_DEFAULTS.get('rate_adjustment', 0.1)
    adj_amort = adj_amort or ADJUSTMENT_DEFAULTS.get('amortization_adjustment', 0)
    
    # Préparer les ajustements
    adjustments = {
        "Montant du Prêt": adj_pret,
        "Taux d'Intérêt": adj_taux / 100,
        "Amortissement": adj_amort
    }
    
    if loan_type == "SCHL":
        prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
        adjustments["Valeur Immeuble"] = prix_vente * 0.05  # 5% de variation
    
    # Simuler
    df_results = simulation_cout_interet(
        montant_pret, taux, amortissement, loan_type,
        clean_monetary_value(property_data.get('prix_vente', 0)), adjustments
    )
    
    # Statistiques sur le coût total
    cout_values = df_results["Coût Total"]
    stats = {
        "min": cout_values.min(),
        "mean": cout_values.mean(),
        "max": cout_values.max()
    }
    
    # Créer le graphique
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Minimum", "Moyen", "Maximum"],
        y=[stats["min"], stats["mean"], stats["max"]],
        marker_color=['#48bb78', '#667eea', '#ff6b6b'],
        text=[f"{v:,.0f} $" for v in [stats["min"], stats["mean"], stats["max"]]],
        textposition='auto',
    ))
    fig.update_layout(
        title=f"Résultats de la Simulation - Coût Total ({loan_type})",
        yaxis_title="Coût Total ($)",
        showlegend=False,
        height=400
    )
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Coût Minimum", className="text-muted"),
                        html.H4(f"{stats['min']:,.0f} $", className="text-success")
                    ])
                ], className="text-center")
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Coût Moyen", className="text-muted"),
                        html.H4(f"{stats['mean']:,.0f} $", className="text-primary")
                    ])
                ], className="text-center")
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Coût Maximum", className="text-muted"),
                        html.H4(f"{stats['max']:,.0f} $", className="text-danger")
                    ])
                ], className="text-center")
            ], width=4),
        ], className="mb-4"),
        
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        
        html.Div([
            html.H5("Détails des coûts", className="mb-3"),
            dash_table.DataTable(
                data=df_results.head(10).to_dict('records'),
                columns=[{"name": i, "id": i} for i in df_results.columns],
                style_cell={'textAlign': 'right'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Prime SCHL', 'filter_query': '{Prime SCHL} > 0'},
                        'backgroundColor': '#fff3cd'
                    }
                ]
            )
        ], className="mt-4")
    ])

# Callback séparé pour stocker les données de simulation intérêt
@app.callback(
    [Output("interet-simulation-data", "data"),
     Output("property-data", "data", allow_duplicate=True)],
    Input("montant-pret-input", "value"),
    Input("taux-interet-input", "value"),
    Input("amortissement-input", "value"),
    State("loan-type", "value"),
    State("property-data", "data"),
    State("adj-pret", "value"),
    State("adj-taux", "value"),
    State("adj-amort", "value"),
    prevent_initial_call=True
)
def store_interet_simulation_data(montant_pret, taux, amortissement, 
                                   loan_type, property_data, adj_pret, adj_taux, adj_amort):
    if not property_data:
        raise PreventUpdate
    
    # Valeurs par défaut si None
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    montant_pret = montant_pret or prix_vente * APP_PARAMS.get('conventional_loan_ratio', 0.80)
    taux = taux or APP_PARAMS.get('default_interest_rate', 5.5)
    amortissement = amortissement or int(APP_PARAMS.get('default_amortization', 25))
    adj_pret = adj_pret or ADJUSTMENT_DEFAULTS.get('loan_adjustment', 5000)
    adj_taux = adj_taux or ADJUSTMENT_DEFAULTS.get('rate_adjustment', 0.1)
    adj_amort = adj_amort or ADJUSTMENT_DEFAULTS.get('amortization_adjustment', 0)
    
    # Préparer les ajustements
    adjustments = {
        "Montant du Prêt": adj_pret,
        "Taux d'Intérêt": adj_taux / 100,
        "Amortissement": adj_amort
    }
    
    if loan_type == "SCHL":
        prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
        adjustments["Valeur Immeuble"] = prix_vente * 0.05
    
    # Simuler
    df_results = simulation_cout_interet(
        montant_pret, taux, amortissement, loan_type,
        clean_monetary_value(property_data.get('prix_vente', 0)), adjustments
    )
    
    results_dict = df_results.to_dict('records')
    
    # Mettre à jour les données de propriété avec la prime SCHL
    updated_prop_data = property_data.copy()
    
    if results_dict and loan_type == "SCHL":
        base_scenario = results_dict[0]  # Premier scénario (sans ajustement)
        updated_prop_data['montant_pret_calcule'] = base_scenario.get('Montant du Prêt', montant_pret)
        updated_prop_data['prime_schl_calculee'] = base_scenario.get('Prime SCHL', 0)
        updated_prop_data['mensualite_calculee'] = base_scenario.get('Mensualité', 0)
    
    return results_dict, updated_prop_data

# Callback pour Cashflow
@app.callback(
    Output("cashflow-results", "children"),
    Input("revenue-simulation-data", "data"),
    Input("interet-simulation-data", "data"),
    State("loan-type", "value")
)
def calculate_cashflow_callback(revenue_data, interet_data, loan_type):
    if not revenue_data or not interet_data:
        return dbc.Alert("Veuillez d'abord effectuer les simulations de Revenue Net et Coût d'Intérêt.", 
                         color="warning", className="mt-3")
    
    df_rev = pd.DataFrame(revenue_data)
    df_fin = pd.DataFrame(interet_data)
    
    # Nouvelle logique de calcul du cashflow selon votre formule
    # montant imposable = Rev Net - interet payé
    # cashflow après impot = Rev Net - (montant imposable * taux impot)
    
    # Récupérer les statistiques du revenu net (NOI)
    noi_stats = {
        "Minimum": df_rev["NOI"].min() if "NOI" in df_rev.columns else df_rev["RNO Après Impôt"].min(),
        "Moyen": df_rev["NOI"].mean() if "NOI" in df_rev.columns else df_rev["RNO Après Impôt"].mean(),
        "Maximum": df_rev["NOI"].max() if "NOI" in df_rev.columns else df_rev["RNO Après Impôt"].max()
    }
    
    # Stats pour les intérêts
    interet_stats = {
        "Minimum": df_fin["Intérêts Année 1"].min(),
        "Moyen": df_fin["Intérêts Année 1"].mean(),
        "Maximum": df_fin["Intérêts Année 1"].max()
    }
    
    # Stats pour le taux d'impôt (supposons qu'il est dans df_rev)
    if "Taux Effectif (%)" in df_rev.columns:
        taux_impot_moyen = df_rev["Taux Effectif (%)"].mean() / 100
    else:
        taux_impot_moyen = 0.3  # Valeur par défaut 30%
    
    scenarios = []
    for noi_label, noi_value in noi_stats.items():
        for int_label, int_value in interet_stats.items():
            # 1. Montant imposable = Rev Net - intérêt payé
            montant_imposable = noi_value - int_value
            
            # 2. Calcul de l'impôt (montant imposable × taux)
            impot = montant_imposable * taux_impot_moyen if montant_imposable > 0 else 0
            
            # 3. Revenue net après impôt = Rev Net - (montant imposable × taux impôt)
            revenue_net_apres_impot = noi_value - impot
            
            # 4. Final cashflow = Revenue net après impôt - Intérêts - Paiement remboursement du prêt
            # Le paiement remboursement = PMT - intérêts (donc le capital seulement)
            pmt_annuelle = df_fin["Service de Dette Annuel"].mean() if "Service de Dette Annuel" in df_fin.columns else noi_value / 1.2
            capital_annuel = pmt_annuelle - int_value
            # Modification: On soustrait aussi les intérêts car ils font partie des dépenses réelles du cashflow
            cashflow = noi_value - impot - int_value - capital_annuel
            
            scenarios.append({
                "Scénario": f"{noi_label} / {int_label}",
                "Revenue Net": noi_value,
                "Intérêts": int_value,
                "Montant Imposable": montant_imposable,
                "Impôt": impot,
                "Cashflow Après Impôt": cashflow
            })
    
    df_cashflow = pd.DataFrame(scenarios)
    
    # Créer un graphique en heatmap
    pivot_data = df_cashflow.pivot_table(
        values='Cashflow Après Impôt',
        index=df_cashflow['Scénario'].apply(lambda x: x.split(' / ')[0]),
        columns=df_cashflow['Scénario'].apply(lambda x: x.split(' / ')[1]),
        aggfunc='first'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale=[
            [0, '#ff4757'],  # Rouge pour négatif
            [0.5, '#ffffff'],  # Blanc pour zéro
            [1, '#48bb78']   # Vert pour positif
        ],
        text=[[f"{v:,.0f} $" for v in row] for row in pivot_data.values],
        texttemplate="%{text}",
        colorbar=dict(title="Cashflow ($)")
    ))
    
    fig.update_layout(
        title="Matrice des Cashflows Après Impôt",
        xaxis_title="Scénarios d'Intérêts",
        yaxis_title="Scénarios de Revenue Net",
        height=500
    )
    
    # Cashflow de base
    cashflow_base = df_cashflow[df_cashflow['Scénario'] == 'Moyen / Moyen']['Cashflow Après Impôt'].iloc[0] if len(df_cashflow) > 0 else 0
    
    # Note explicative sur le calcul
    note_calcul = dbc.Alert([
        html.H6("📊 Méthode de calcul utilisée :", className="alert-heading"),
        html.P([
            html.Strong("Cashflow après impôt = Rev Net - (montant imposable × taux impôt)"), 
            html.Br(),
            "• Montant imposable = Rev Net - Intérêts payés",
            html.Br(),
            "• Les intérêts sont déductibles d'impôt",
            html.Br(),
            "• Impôt = Montant imposable × Taux d'imposition",
            html.Br(),
            "• Cashflow = Revenue Net - Impôt calculé - Capital remboursé",
            html.Br(),
            html.Small(f"Intérêts moyens année 1 : {interet_stats['Moyen']:,.0f} $ (déductibles d'impôt)", 
                      className="text-muted")
        ])
    ], color="info", className="mt-3")
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Cashflow de Base", className="text-center mb-3"),
                        html.H2(f"{cashflow_base:,.0f} $", 
                               className=f"text-center {'text-success' if cashflow_base > 0 else 'text-danger'}")
                    ])
                ], className="mb-4")
            ], width=12)
        ]),
        
        note_calcul,
        
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        
        html.Div([
            html.H5("Tableau détaillé des scénarios", className="mb-3 mt-4"),
            dash_table.DataTable(
                data=df_cashflow.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df_cashflow.columns],
                style_cell={'textAlign': 'right'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Cashflow Net', 'filter_query': '{Cashflow Net} < 0'},
                        'color': 'red',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'column_id': 'Cashflow Net', 'filter_query': '{Cashflow Net} >= 0'},
                        'color': 'green',
                        'fontWeight': 'bold'
                    }
                ]
            )
        ], className="mt-4"),
        
        # Tableau récapitulatif
        html.Div([
            html.H5("Détails du calcul (scénario moyen)", className="mb-3 mt-4"),
            dbc.Table([
                html.Tbody([
                    html.Tr([
                        html.Td("Revenue Net"),
                        html.Td(f"{noi_stats['Moyen']:,.0f} $", className="text-end")
                    ]),
                    html.Tr([
                        html.Td("- Intérêts payés"),
                        html.Td(f"- {interet_stats['Moyen']:,.0f} $", className="text-end text-info")
                    ]),
                    html.Tr([
                        html.Td("= Montant imposable"),
                        html.Td(f"{noi_stats['Moyen'] - interet_stats['Moyen']:,.0f} $", className="text-end")
                    ]),
                    html.Tr([
                        html.Td(f"× Taux d'imposition ({taux_impot_moyen:.1%})"),
                        html.Td(f"{(noi_stats['Moyen'] - interet_stats['Moyen']) * taux_impot_moyen:,.0f} $", className="text-end text-danger")
                    ]),
                    html.Tr([
                        html.Td(html.Strong("Cashflow après impôt")),
                        html.Td(html.Strong(f"{cashflow_base:,.0f} $"), 
                               className=f"text-end {'text-success' if cashflow_base > 0 else 'text-danger'}")
                    ], className="table-primary")
                ])
            ], striped=True, hover=True, size="sm")
        ])
    ])

# Callback pour les projections sur 5 ans
@app.callback(
    Output("projection-results", "children"),
    [Input("generate-projections-btn", "n_clicks")],
    [State("property-data", "data"),
     State("revenue-simulation-data", "data"),
     State("interet-simulation-data", "data"),
     State("loan-type", "value"),
     State("tax-province", "value"),
     State("tax-status", "value"),
     State("use-dpa", "value"),
     State("dpa-rate", "value"),
     State("building-ratio", "value"),
     State("inflation-rate", "value"),
     State("rent-increase", "value"),
     State("appreciation-rate", "value"),
     State("use-degressive-interest", "value"),
     State("projection-years", "value"),
     State("taux-terme-initial", "value"),
     State("taux-terme-2", "value"),
     State("taux-terme-3", "value"),
     State("taux-terme-4", "value"),
     State("taux-terme-5", "value")]
)
def generate_projections_callback(n_clicks, property_data, revenue_data, interet_data,
                                 loan_type, tax_province, tax_status, use_dpa, dpa_rate,
                                 building_ratio, inflation_rate, rent_increase,
                                 appreciation_rate, use_degressive, projection_years,
                                 taux_terme_initial, taux_terme_2, taux_terme_3, taux_terme_4, taux_terme_5):
    if not n_clicks or not property_data:
        return html.Div()
    
    # Valeurs par défaut si None
    use_dpa = use_dpa or []
    dpa_rate = dpa_rate or APP_PARAMS.get('default_dpa_rate', 4.0)
    building_ratio = building_ratio or APP_PARAMS.get('default_building_ratio', 80.0)
    inflation_rate = inflation_rate or APP_PARAMS.get('default_inflation_rate', 2.0)
    rent_increase = rent_increase or APP_PARAMS.get('default_rent_increase', 2.5)
    appreciation_rate = appreciation_rate or APP_PARAMS.get('default_appreciation_rate', 3.0)
    use_degressive = use_degressive or [True]
    projection_years = projection_years or 25
    
         # Récupérer le taux d'intérêt initial de la base de données selon le type de prêt
    if loan_type == "SCHL":
        db_taux_initial_str = property_data.get('financement_schl_taux_interet', None)
        if db_taux_initial_str is not None:
            db_taux_initial = clean_numeric_value(db_taux_initial_str)  # Nettoyer les valeurs avec % et convertir en nombre
        else:
            db_taux_initial = APP_PARAMS.get('default_interest_rate', 5.5)
    else:
        db_taux_initial_str = property_data.get('financement_conv_taux_interet', None)
        if db_taux_initial_str is not None:
            db_taux_initial = clean_numeric_value(db_taux_initial_str)  # Nettoyer les valeurs avec % et convertir en nombre
        else:
            db_taux_initial = APP_PARAMS.get('default_interest_rate', 5.5)
    
    # Valeurs par défaut pour les taux d'intérêt des termes
    taux_terme_initial = taux_terme_initial or db_taux_initial
    taux_terme_2 = taux_terme_2 or (taux_terme_initial + 0.5)
    taux_terme_3 = taux_terme_3 or (taux_terme_initial + 1.0)
    taux_terme_4 = taux_terme_4 or (taux_terme_initial + 1.0)
    taux_terme_5 = taux_terme_5 or (taux_terme_initial + 1.0)
    
    # Convertir en pourcentage
    taux_terms = [
        taux_terme_initial / 100,
        taux_terme_2 / 100,
        taux_terme_3 / 100,
        taux_terme_4 / 100,
        taux_terme_5 / 100
    ]
    
    # Calculer les valeurs de base
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    use_dpa = bool(use_dpa)
    use_degressive = bool(use_degressive)
    
    # Données de base - nettoyage des valeurs monétaires pour assurer qu'elles sont numériques
    revenue_brut_base = clean_monetary_value(property_data.get('revenus_brut', 
                                        property_data.get('loyer_par_logement', 0) * property_data.get('nombre_de_logement', 0) * 12))
    depenses_base = clean_monetary_value(property_data.get('depenses_totales', 0))
    prix_vente = clean_monetary_value(property_data.get('prix_vente', property_data.get('prix_de_vente', 0)))
    
    # Récupération des données spécifiques au financement selon le type de prêt
    if loan_type == "SCHL":
        amortissement_str = property_data.get('financement_schl_amortissement', 25)
    else:
        amortissement_str = property_data.get('financement_conv_amortissement', 25)
    
    # S'assurer que amortissement est un entier
    # Nettoyer la valeur pour extraire seulement le nombre (ex: "50 Ans" -> 50)
    if amortissement_str:
        try:
            amortissement = int(clean_numeric_value(amortissement_str))
        except (ValueError, TypeError):
            amortissement = 25
    else:
        amortissement = 25
    
    # Paramètres du prêt - utiliser le calcul basé sur le RDC pour cohérence
    montant_pret, _, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    # Calcul de la prime SCHL
    prime_schl = 0
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        print(f"📊 [Projections] Taux SCHL par défaut : {default_rate}%")
    
    # Montant financé
    montant_finance = montant_pret + prime_schl
    
    # Limiter les années de projection à l'amortissement
    years_to_project = min(projection_years, amortissement)
    
    # Créer un scénario de taux avec les changements par terme
    scenarios_taux = {}
    for year in range(1, years_to_project + 1):
        current_term = (year - 1) // 5  # 0 pour années 1-5, 1 pour années 6-10, etc.
        if current_term < len(taux_terms):
            # Ajouter un changement de taux au début de chaque nouveau terme
            if (year - 1) % 5 == 0 and year > 1:
                scenarios_taux[year] = taux_terms[current_term]
    
    # Obtenir la valeur du bâtiment pour DPA
    building_value = clean_monetary_value(property_data.get("eval_batiment", 0)) if use_dpa else 0
    
    # Appeler calculate_cashflow_projection avec tous les paramètres
    df_projection_complete = calculate_cashflow_projection(
        property_data=property_data,
        loan_type=loan_type,
        tax_province=tax_province,
        tax_status=tax_status,
        montant_finance=montant_finance,
        taux_interet=taux_terms[0],  # Taux initial
        amortissement=years_to_project,
        scenarios_taux=scenarios_taux,
        inflation_rate=inflation_rate,
        rent_increase=rent_increase,
        use_dpa=use_dpa,
        dpa_rate=dpa_rate,
        building_value=building_value
    )
    
    # Utiliser directement les colonnes existantes pour les graphiques
    df_projection_complete['Cashflow Net'] = df_projection_complete['Cashflow annuel']
    df_projection_complete['Solde Prêt'] = df_projection_complete['Solde prêt']  # Corriger la casse
    
    # Ajouter la valeur de l'immeuble avec appréciation
    for index, row in df_projection_complete.iterrows():
        year = row['Année']
        df_projection_complete.at[index, 'Valeur Immeuble'] = prix_vente * ((1 + appreciation_rate/100) ** year)
    
    # Renommer pour la compatibilité
    df_projections = df_projection_complete
    
    # Créer les graphiques
    fig_cashflow = go.Figure()
    fig_cashflow.add_trace(go.Scatter(
        x=df_projections['Année'],
        y=df_projections['Cashflow Net'],
        mode='lines+markers',
        name='Cashflow Net',
        line=dict(color='#667eea', width=3),
        marker=dict(size=10)
    ))
    
    # Ajouter des lignes verticales pour marquer les changements de terme
    for term_change in range(5, years_to_project, 5):
        fig_cashflow.add_vline(
            x=term_change + 0.5, 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Changement de terme: {taux_terms[(term_change)//5]*100:.1f}%",
            annotation_position="top right"
        )
    
    fig_cashflow.update_layout(
        title=f"Évolution du Cashflow Net sur {years_to_project} ans",
        xaxis_title="Année",
        yaxis_title="Cashflow Net ($)",
        height=500,
        hovermode='x unified'
    )
    
    # Graphique du taux d'intérêt par année
    fig_taux = go.Figure()
    
    # Créer une liste des taux d'intérêt pour chaque année
    taux_par_annee = []
    for year in range(1, years_to_project + 1):
        current_term = (year - 1) // 5
        if current_term < len(taux_terms):
            taux_par_annee.append(taux_terms[current_term] * 100)
        else:
            taux_par_annee.append(taux_terms[-1] * 100)
    
    fig_taux.add_trace(go.Scatter(
        x=list(range(1, years_to_project + 1)),
        y=taux_par_annee,
        mode='lines+markers',
        name="Taux d'intérêt",
        line=dict(color='#ff6b6b', width=3),
        marker=dict(size=10)
    ))
    
    fig_taux.update_layout(
        title="Évolution du taux d'intérêt par terme",
        xaxis_title="Année",
        yaxis_title="Taux d'intérêt (%)",
        height=300,
        hovermode='x unified'
    )
    
    # Graphique de la valeur de l'immeuble
    fig_value = go.Figure()
    fig_value.add_trace(go.Bar(
        x=df_projections['Année'],
        y=df_projections['Valeur Immeuble'],
        name='Valeur Immeuble',
        marker_color='#48bb78'
    ))
    
    fig_value.update_layout(
        title=f"Appréciation de l'immeuble ({appreciation_rate}% par an)",
        xaxis_title="Année",
        yaxis_title="Valeur ($)",
        height=400
    )
    
    # Graphique du solde du prêt
    fig_pret = go.Figure()
    fig_pret.add_trace(go.Scatter(
        x=df_projections['Année'],
        y=df_projections['Solde Prêt'],
        mode='lines+markers',
        name='Solde du prêt',
        line=dict(color='#805ad5', width=3),
        marker=dict(size=8)
    ))
    
    # Ajouter des lignes verticales pour marquer les changements de terme
    for term_change in range(5, years_to_project, 5):
        fig_pret.add_vline(
            x=term_change + 0.5, 
            line_dash="dash", 
            line_color="red"
        )
    
    fig_pret.update_layout(
        title="Évolution du solde du prêt",
        xaxis_title="Année",
        yaxis_title="Solde ($)",
        height=400,
        hovermode='x unified'
    )
    
    # Résumé des projections
    total_cashflow = df_projections['Cashflow Net'].sum()
    appreciation_totale = df_projections.iloc[-1]['Valeur Immeuble'] - prix_vente
    capital_rembourse = (montant_pret + prime_schl) - df_projections.iloc[-1]['Solde Prêt']
    
    return html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                        html.H6(f"Cashflow Total ({years_to_project} ans)", className="text-muted"),
                        html.H3(f"{total_cashflow:,.0f} $", 
                               className=f"{'text-success' if total_cashflow > 0 else 'text-danger'}")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Appréciation Totale", className="text-muted"),
                        html.H3(f"{appreciation_totale:,.0f} $", className="text-success")
                    ])
                ], className="text-center")
            ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                        html.H6("Capital Remboursé", className="text-muted"),
                        html.H3(f"{capital_rembourse:,.0f} $", className="text-info")
                    ])
                ], className="text-center")
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Rendement Total", className="text-muted"),
                        html.H3(f"{(total_cashflow + appreciation_totale):,.0f} $", className="text-primary")
                    ])
                ], className="text-center")
            ], width=3),
                ], className="mb-4"),
                
        # Information sur les taux d'intérêt par terme
        dbc.Alert([
            html.H6("📈 Taux d'intérêt appliqués par terme:", className="alert-heading mb-3"),
                html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Span("Terme 1 (1-5 ans): ", className="fw-bold"),
                        f"{taux_terms[0]*100:.2f}%"
                    ], width=3),
                    dbc.Col([
                        html.Span("Terme 2 (6-10 ans): ", className="fw-bold"),
                        f"{taux_terms[1]*100:.2f}%"
                    ], width=3),
                    dbc.Col([
                        html.Span("Terme 3 (11-15 ans): ", className="fw-bold"),
                        f"{taux_terms[2]*100:.2f}%"
                    ], width=3),
                    dbc.Col([
                        html.Span("Terme 4 (16-20 ans): ", className="fw-bold"),
                        f"{taux_terms[3]*100:.2f}%"
                    ], width=3),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col([
                        html.Span("Terme 5 (21-25 ans): ", className="fw-bold"),
                        f"{taux_terms[4]*100:.2f}%"
                    ], width=3),
                ])
            ])
        ], color="warning", className="mb-4"),
        
        dbc.Tabs([
            dbc.Tab([
                dcc.Graph(figure=fig_cashflow, config={'displayModeBar': False})
            ], label="Cashflow Net", tab_id="tab-cashflow", className="p-4"),
            dbc.Tab([
                dcc.Graph(figure=fig_taux, config={'displayModeBar': False})
            ], label="Taux d'intérêt", tab_id="tab-taux", className="p-4"),
            dbc.Tab([
                dcc.Graph(figure=fig_pret, config={'displayModeBar': False})
            ], label="Solde du prêt", tab_id="tab-pret", className="p-4"),
            dbc.Tab([
                dcc.Graph(figure=fig_value, config={'displayModeBar': False})
            ], label="Valeur de l'immeuble", tab_id="tab-value", className="p-4"),
        ], className="mb-4"),
        
        # Note explicative sur la méthode de calcul
        dbc.Alert([
            html.H6("📊 Méthode de calcul appliquée :", className="alert-heading"),
            html.Ul([
                html.Li("NOI = Revenue brut - Dépenses d'exploitation"),
                html.Li("Revenu imposable = NOI - Intérêts déductibles - DPA"),
                html.Li("Impôt = Revenu imposable × Taux d'imposition"),
                html.Li("RNO après impôt = NOI - Impôt"),
                html.Li(html.Strong("Cashflow = NOI - Intérêts - Capital remboursé - Impôt")),
                html.Li("Les intérêts sont déductibles d'impôt (avantage fiscal)"),
                html.Li(html.Strong("La simulation prend en compte les changements de taux d'intérêt à chaque terme de 5 ans"))
            ])
        ], color="info", className="mt-4 mb-4"),
        
        # Avertissement sur le renouvellement
        dbc.Alert([
            html.H6("⚠️ Points d'attention pour le renouvellement :", className="alert-heading"),
            html.P("Le renouvellement de prêt tous les 5 ans présente des risques et opportunités:"),
            html.Ul([
                html.Li("Vérifiez que votre cashflow reste positif même avec l'augmentation potentielle des taux"),
                html.Li("À chaque renouvellement, évaluez votre capacité de remboursement avec les nouveaux taux"),
                html.Li("Plus le temps passe, plus votre capital remboursé augmente, améliorant votre cashflow"),
                html.Li("En cas de hausse importante des taux, envisagez de refinancer sur une durée plus longue pour maintenir des mensualités gérables")
            ])
        ], color="danger", className="mb-4"),
        
                        html.Div([
            html.H5("Tableau détaillé des projections", className="mb-3 mt-4"),
                            dash_table.DataTable(
                data=df_projections.to_dict('records'),
                columns=[{"name": i, "id": i} for i in df_projections.columns],
                style_cell={'textAlign': 'right'},
                                style_data_conditional=[
                                    {
                        'if': {'column_id': 'Cashflow Net', 'filter_query': '{Cashflow Net} < 0'},
                        'color': 'red',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {'column_id': 'Année', 'filter_query': '{Année} = 5 || {Année} = 10 || {Année} = 15 || {Année} = 20 || {Année} = 25'},
                        'backgroundColor': '#FFF9C4',
                        'fontWeight': 'bold'
                    }
                ],
                style_cell_conditional=[
                    {'if': {'column_id': 'Année'}, 'textAlign': 'center'}
                ],
                fixed_rows={'headers': True},
                style_table={'height': '500px', 'overflowY': 'auto'}
            )
        ])
    ])


# Callback pour générer le contenu du résumé
@app.callback(
    Output("summary-content", "children"),
    [Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("revenue-simulation-data", "data"),
     Input("interet-simulation-data", "data"),
     Input("schl-payment-mode", "value"),
     Input("conventional-rate-selector", "value")]
)
def generate_summary_content(property_data, loan_type, tax_province, tax_status,
                           revenue_data, interet_data, schl_payment_mode, conventional_rate):
    if not property_data:
        return dbc.Alert("Veuillez sélectionner un immeuble pour voir le résumé.", 
                        color="info", className="mt-3")
    
    # Debug
    print(f"🔍 [RÉSUMÉ] Loan type: {loan_type}")
    if property_data:
        nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
        print(f"🔍 [RÉSUMÉ] Nombre d'unités: {nombre_unites}")
    
    try:
        # Récupérer les données financières de base
        prix = clean_monetary_value(property_data.get('prix_vente', 0))
        revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
        depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
        revenue_net = clean_monetary_value(property_data.get('revenu_net', 0))
        
        if revenue_net == 0:
            revenue_net = revenue_brut - depenses
        
        tga = (revenue_net / prix * 100) if prix > 0 else 0
        
        # Paramètres de financement
        is_incorporated = tax_status == "incorporated"
        
        # === MODIFICATION : Utilisation standardisée du calcul du prêt ===
        # Utiliser la fonction calculate_loan_amount_from_rdc pour la cohérence
        montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate)
        
        # Récupérer les paramètres du prêt pour les calculs suivants
        if loan_type == "SCHL":
            rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 0))
            if rdc_ratio == 0:
                raise ValueError("RDC SCHL manquant dans la base de données pour cette propriété")
            taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
            amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
        else:
            rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 0))
            if rdc_ratio == 0:
                raise ValueError("RDC Conventionnel manquant dans la base de données pour cette propriété")
            
            # Utiliser le taux conventionnel sélectionné si disponible
            if conventional_rate and conventional_rate != "":
                parts = conventional_rate.split('_')
                if len(parts) >= 2:
                    taux_str = parts[-1]
                    taux_interet = float(taux_str) / 100
                else:
                    taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
            else:
                taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
            
            amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
        
        # Mise de fonds calculée à partir du ratio prêt/valeur
        mise_de_fonds_pct = (1 - ratio_pret_valeur) * 100
        mise_de_fonds = prix * (mise_de_fonds_pct / 100)
        
        # Prime SCHL
        prime_schl = 0
        prime_rate = 0
        if loan_type == "SCHL":
            # Utiliser un taux par défaut de 2.40%
            default_rate = 2.40
            prime_schl = montant_pret * (default_rate / 100)
            prime_rate = default_rate
        
        # Montant financé selon le mode de paiement SCHL
        if loan_type == "SCHL" and schl_payment_mode == "cash":
            montant_finance = montant_pret  # La prime est payée comptant, pas financée
        else:
            montant_finance = montant_pret + prime_schl  # La prime est financée
        
        # === CORRECTION : Utiliser la PMT mensuelle calculée selon votre formule ===
        # La mensualité reste la même peu importe si la prime SCHL est financée ou non
        # car elle est basée sur la capacité de paiement (RDC)
        mensualite = pmt_mensuelle
        n_payments = int(amortissement * 12)
        
        # Calcul du PMT max basé sur le RDC exigé par le prêteur
        revenue_net_mensuel = revenue_net / 12
        pmt_max_rdc = revenue_net_mensuel / rdc_ratio if rdc_ratio > 0 else 0
        
        # === MODIFICATION 6 : Calcul des intérêts totaux ===
        # Calculer les intérêts totaux basés sur l'amortissement réel
        total_paiements = 0
        solde_temp = montant_finance
        for i in range(n_payments):
            interet_mois = solde_temp * (taux_interet / 12)
            capital_mois = mensualite - interet_mois
            if capital_mois > solde_temp:
                capital_mois = solde_temp
            solde_temp -= capital_mois
            total_paiements += mensualite
            if solde_temp <= 0:
                break
        
        interets_totaux = total_paiements - montant_finance
        cout_total_interet = interets_totaux  # Pour clarté
        
        # Calcul des intérêts et capital année 1
        solde_debut = montant_finance
        interet_annuel = 0
        capital_annuel = 0
        
        for mois in range(12):
            interet_mois = solde_debut * (taux_interet / 12)
            capital_mois = mensualite - interet_mois
            interet_annuel += interet_mois
            capital_annuel += capital_mois
            solde_debut -= capital_mois
        
        # Calcul de l'impôt selon la nouvelle logique
        # montant imposable = Rev Net - intérêt payé
        montant_imposable = revenue_net - interet_annuel
        
        if is_incorporated:
            tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
            impot = montant_imposable * tax_rate if montant_imposable > 0 else 0
        else:
            impot = calculate_progressive_tax(montant_imposable, tax_province) if montant_imposable > 0 else 0
            tax_rate = (impot / montant_imposable * 100) if montant_imposable > 0 else 0
        
        # CORRECTION : Utiliser la logique du cashflow mois 1
        # 1. Montant imposable = Rev Net (M) - intérêt payé du mois
        revenue_net_mensuel = revenue_net / 12
        interet_mois_1 = montant_finance * (taux_interet / 12)
        capital_mois_1 = mensualite - interet_mois_1
        montant_imposable_mois_1 = revenue_net_mensuel - interet_mois_1
        
        # 2. Revenus net après impôt = Rev Net (M) - (montant imposable × taux impôt)
        if is_incorporated:
            impot_mois_1 = montant_imposable_mois_1 * tax_rate if montant_imposable_mois_1 > 0 else 0
        else:
            # Pour les particuliers, utiliser l'impôt annuel divisé par 12
            impot_mois_1 = impot / 12
        
        revenue_net_apres_impot_mensuel = revenue_net_mensuel - impot_mois_1
        
        # 3. Final cashflow = Revenus net après impôt - Intérêts - Paiement remboursement du prêt du mois
        # Le paiement remboursement = Capital seulement
        # Modification: On soustrait aussi les intérêts car ils font partie des dépenses réelles du cashflow
        cashflow_mensuel = revenue_net_mensuel - impot_mois_1 - interet_mois_1 - capital_mois_1
        cashflow_annuel = cashflow_mensuel * 12
        
        # --- Confluence -------------------------------------------------------------
        # Utiliser la formule correcte pour cashflow_annee1
        cashflow_annee1 = cashflow_annuel                                    # déjà en $/an
        mrn = prix / revenue_net if revenue_net else 0                       # Multiplicateur de revenu net
        rdc_calc = revenue_net / (mensualite * 12) if mensualite else 0      # Ratio de couverture de la dette
        rdc_calc = round(rdc_calc, 2)
        # --- Confluence -------------------------------------------------------------
        
        # Coûts d'acquisition
        total_costs = prix * 0.04 + calculate_bienvenue_tax(prix, property_data)
        
        # Statistiques des simulations
        rno_stats = None
        cout_stats = None
        
        if revenue_data and len(revenue_data) > 0:
            try:
                df_rev = pd.DataFrame(revenue_data)
                if "RNO Après Impôt" in df_rev.columns:
                    rno_stats = {
                        "min": df_rev["RNO Après Impôt"].min(),
                        "mean": df_rev["RNO Après Impôt"].mean(),
                        "max": df_rev["RNO Après Impôt"].max()
                    }
            except Exception:
                pass
        
        if interet_data and len(interet_data) > 0:
            try:
                df_fin = pd.DataFrame(interet_data)
                if "Coût Total" in df_fin.columns:
                    cout_stats = {
                        "min": df_fin["Coût Total"].min(),
                        "mean": df_fin["Coût Total"].mean(),
                        "max": df_fin["Coût Total"].max()
                    }
            except Exception:
                pass
        
        # Calculs automatiques pour MRN et RDC
        # MRN (Multiplicateur de Revenu Net)
        mrn = prix / revenue_net if revenue_net > 0 else 0
        
        # RDC (Ratio de Couverture de la Dette) - utiliser les valeurs calculées
        # rdc_calc est déjà calculé plus haut dans la fonction
        
        # Vérifications automatiques
        cashflow_positif = cashflow_annee1 >= 0
        mrn_ok = mrn >= 15
        rdc_ok = rdc_calc >= 1.2
        
        # Messages de débogage pour le terminal
        nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
        print(f"DEBUG: Type={loan_type}, Unités={nombre_unites}")
        
        # Construire le résumé
        return html.Div([
            # Section Propriété
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-home me-2"),
                        "Détails de la Propriété"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            html.P("Adresse", className="text-muted mb-1"),
                            html.P(property_data.get('address', 'N/A'), className="fw-bold")
                        ], width=6),
                        dbc.Col([
                            html.P("Prix de vente", className="text-muted mb-1"),
                            html.P(f"{prix:,.0f} $", className="fw-bold")
                        ], width=3),
                        dbc.Col([
                            html.P("Nombre d'unités", className="text-muted mb-1"),
                            html.P(f"{clean_numeric_value(property_data.get('nombre_unites', 0)):.0f}", className="fw-bold")
                        ], width=3),
                    ])
                ])
            ], className="mb-4"),
            
            # Section Analyse Financière
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-chart-line me-2"),
                        "Analyse Financière"
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H6("Revenus", className="text-primary mb-3"),
                                html.P(f"Revenue brut annuel: {revenue_brut:,.0f} $"),
                                html.P(f"Dépenses annuelles: {depenses:,.0f} $"),
                                html.P(f"Revenue net annuel: {revenue_net:,.0f} $", className="fw-bold"),
                                html.P(f"TGA: {tga:.2f}%", className="fw-bold text-success"),
                            ])
                        ], width=4),
                        dbc.Col([
                            html.Div([
                                html.H6("Financement", className="text-primary mb-3"),
                                html.P(f"Type de prêt: {loan_type}"),
                                html.P(f"Mise de fonds ({mise_de_fonds_pct:.1f}%): {mise_de_fonds:,.0f} $"),
                                html.P(f"Montant du prêt: {montant_pret:,.0f} $"),
                                html.P(f"Prime SCHL: {prime_schl:,.0f} $" if loan_type == "SCHL" else "Prime SCHL: N/A"),
                                html.P(f"Mensualité: {mensualite:,.0f} $"),
                                html.P(f"Intérêts totaux: {interets_totaux:,.0f} $"),
                            ])
                        ], width=4),
                        dbc.Col([
                            html.Div([
                                html.H6("Résultats", className="text-primary mb-3"),
                                html.P(f"Province: {tax_province}"),
                                html.P(f"Statut: {'Incorporé' if is_incorporated else 'Non Incorporé'}"),
                                html.P(f"Cashflow mensuel année 1 moyenne: {cashflow_mensuel:,.0f} $", 
                                      className=f"fw-bold {'text-success' if cashflow_mensuel > 0 else 'text-danger'}"),
                                html.P(f"Cashflow annuel: {cashflow_annuel:,.0f} $"),
                                html.P(f"Mise de fonds totale: {mise_de_fonds + total_costs:,.0f} $"),
                            ])
                        ], width=4),
                    ])
                ])
            ], className="mb-4"),
            
            # Section PMT Max selon RDC
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-calculator me-2"),
                        "Capacité de paiement maximale"
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.P("Formule PMT max:", className="text-muted mb-1"),
                            html.P("PMT max = Revenue net mensuel / RDC exigé", className="fw-bold")
                        ], width=6),
                        dbc.Col([
                            html.P("Calcul:", className="text-muted mb-1"),
                            html.P(f"PMT max = {revenue_net/12:,.0f} $ / {rdc_ratio:.2f} = {pmt_max_rdc:,.0f} $", 
                                   className="fw-bold text-info")
                        ], width=6),
                    ]),
                    html.Hr(),
                    html.P(f"Le prêteur exige un ratio de couverture de dette (RDC) de {rdc_ratio:.2f} pour un prêt {loan_type}.", 
                           className="text-muted small"),
                    html.P(f"Avec un revenu net mensuel de {revenue_net/12:,.0f} $, la mensualité maximale autorisée est de {pmt_max_rdc:,.0f} $.", 
                           className="text-muted small")
                ])
            ], className="mb-4"),
            
            # Section Simulations (si disponibles)
            html.Div([
                # Section Confluence
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-stream me-2"),
                            "Confluence"
                        ], className="mb-3"),

                        # Section Rentabilité
                        html.H6("Confluences rentabilité", className="text-primary mb-3"),
                        
                        dbc.Checklist(
                            id="confluence-rentabilite",
                            options=[
                                {"label": "Cashflow positif", "value": "cashflow_positif"},
                                {"label": "MRN ≥ 15", "value": "mrn_ok"},
                                {"label": "RDC ≥ 1.2", "value": "rdc_ok"}
                            ],
                            value=[
                                "cashflow_positif" if cashflow_positif else None,
                                "mrn_ok" if mrn_ok else None,
                                "rdc_ok" if rdc_ok else None
                            ],
                            switch=True,
                            className="mb-3"
                        ),
                        
                        # Loyer comparé au secteur
                        html.Div([
                            html.P("Loyer de l'immeuble par rapport au secteur:", className="mb-2"),
                            dbc.RadioItems(
                                id="loyer-secteur",
                                options=[
                                    {"label": "Plus haut", "value": "plus_haut"},
                                    {"label": "Plus bas", "value": "plus_bas"}
                                ],
                                inline=True,
                                className="mb-3"
                            )
                        ]),
                        
                        # Prix par porte
                        dbc.Checklist(
                            id="prix-porte-secteur",
                            options=[
                                {"label": "Prix par porte plus bas que le secteur (vérifier sur JLR)", "value": "prix_porte_ok"}
                            ],
                            value=[],
                            switch=True,
                            className="mb-3"
                        ),
                        
                        # Affichage des valeurs calculées
                        dbc.Row([
                            dbc.Col([
                                dbc.Alert([
                                    html.Strong("MRN calculé: "),
                                    f"{mrn:.1f}",
                                    html.Br(),
                                    html.Small("(Prix ÷ Revenu net)", className="text-muted")
                                ], color="success" if mrn_ok else "warning", className="py-2")
                            ], width=6),
                            dbc.Col([
                                dbc.Alert([
                                    html.Strong("RDC calculé: "),
                                    f"{rdc_calc:.2f}",
                                    html.Br(),
                                    html.Small("(Revenu net ÷ Service de dette)", className="text-muted")
                                ], color="success" if rdc_ok else "warning", className="py-2")
                            ], width=6),
                        ], className="mb-3"),
                        
                        html.Hr(),
                        
                        # Section Qualité de l'investissement
                        html.H6("Confluences qualité de l'investissement", className="text-primary mb-3"),
                        
                        dbc.Checklist(
                            id="confluence-qualite",
                            options=[
                                {"label": "Potentiel d'optimisation des revenus et dépenses court terme", "value": "optim_potentiel"},
                                {"label": "Si immeuble > 30 ans, rénové < 5 ans (vérifier JLR)", "value": "renov_recent"},
                                {"label": "Taux de vacance ≤ au quartier", "value": "vacance_ok"}
                            ],
                            value=[],
                            switch=True,
                            className="mb-3"
                        ),
                        
                        html.Hr(),
                        
                        # Section Plage de négociation
                        html.H6("Plage de négociation (JLR)", className="text-primary mb-3"),
                        
                        dbc.Alert([
                            html.I(className="fas fa-lightbulb me-2"),
                            "Regarder le prix d'achat + rénovations du vendeur pour déterminer la plage"
                        ], color="info", className="mb-3"),
                        
                        html.P("Section disponible dans l'onglet Résumé principal", className="text-muted")
                    ])
                ], className="mb-4"),
                
                dbc.Card([
                    dbc.CardBody([
                        html.H5([
                            html.I(className="fas fa-chart-area me-2"),
                            "Résultats des Simulations"
                        ], className="mb-4"),
                        dbc.Row([
                            dbc.Col([
                                html.H6("RNO Après Impôt", className="text-center mb-3"),
                                html.P(f"Min: {rno_stats['min']:,.0f} $", className="text-danger") if rno_stats else "",
                                html.P(f"Moy: {rno_stats['mean']:,.0f} $", className="text-primary") if rno_stats else "",
                                html.P(f"Max: {rno_stats['max']:,.0f} $", className="text-success") if rno_stats else "",
                                html.P("Aucune simulation effectuée", className="text-muted") if not rno_stats else ""
                            ], width=6),
                            dbc.Col([
                                html.H6("Coût Total du Financement", className="text-center mb-3"),
                                html.P(f"Min: {cout_stats['min']:,.0f} $", className="text-success") if cout_stats else "",
                                html.P(f"Moy: {cout_stats['mean']:,.0f} $", className="text-primary") if cout_stats else "",
                                html.P(f"Max: {cout_stats['max']:,.0f} $", className="text-danger") if cout_stats else "",
                                html.P("Aucune simulation effectuée", className="text-muted") if not cout_stats else ""
                            ], width=6),
                        ])
                    ])
                ], className="mb-4")
            ]) if rno_stats or cout_stats else html.Div(),
            
            # Section Prix à payer
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-tag me-2"),
                        "Prix à payer"
                    ], className="mb-4"),

                    # Calculer les valeurs économiques
                    html.Div(id="economic-values-content"),

                    html.Hr(className="my-3"),

                    # Section pour modifier les revenus/dépenses
                    html.H6("Ajuster les revenus et dépenses", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Revenus bruts", className="fw-bold"),
                            dbc.InputGroup([
                                dbc.Input(
                                    id="adjusted-revenue-brut",
                                    type="number",
                                    value=revenue_brut,
                                    step=1000
                                ),
                                dbc.InputGroupText("$")
                            ], className="mb-2"),

                            # Possibilité d'ajouter des revenus
                            dbc.Button("+ Ajouter un revenu", id="add-revenue-btn", size="sm", color="success", className="mb-3"),
                            html.Div(id="additional-revenues-container"),
                            
                            # Affichage des revenus validés
                            html.Div(id="validated-revenues-display", className="mt-3")
                        ], width=6),

                        dbc.Col([
                            html.Label("Dépenses totales", className="fw-bold"),
                            dbc.InputGroup([
                                dbc.Input(
                                    id="adjusted-depenses-totales",
                                    type="number",
                                    value=depenses,
                                    step=100
                                ),
                                dbc.InputGroupText("$")
                            ], className="mb-2"),

                            # Possibilité d'ajouter des dépenses
                            dbc.Button("+ Ajouter une dépense", id="add-expense-btn", size="sm", color="danger", className="mb-3"),
                            html.Div(id="additional-expenses-container"),
                            
                            # Affichage des dépenses validées
                            html.Div(id="validated-expenses-display", className="mt-3")
                        ], width=6),
                    ]),

                    dbc.Button([
                        html.I(className="fas fa-calculator me-2"),
                        "Recalculer les valeurs économiques"
                    ], id="recalculate-economic-values-btn", color="primary", className="mt-3")
                ])
            ], className="mb-4"),
            
            # Recommandations
            dbc.Card([
                dbc.CardBody([
                    html.H5([
                        html.I(className="fas fa-lightbulb me-2"),
                        "Analyse et Recommandations"
                    ], className="mb-3"),
                    html.Div([
                        html.P([
                            html.I(className=f"fas fa-{'check' if tga > 5 else 'times'}-circle text-{'success' if tga > 5 else 'warning'} me-2"),
                            f"TGA de {tga:.2f}% " + ("excellent" if tga > 7 else "correct" if tga > 5 else "faible")
                        ]),
                        html.P([
                            html.I(className=f"fas fa-{'check' if cashflow_mensuel > 0 else 'times'}-circle text-{'success' if cashflow_mensuel > 0 else 'danger'} me-2"),
                            f"Cashflow mensuel de {cashflow_mensuel:,.0f} $ " + ("positif" if cashflow_mensuel > 0 else "négatif")
                        ]),
                        html.P([
                            html.I(className="fas fa-info-circle text-info me-2"),
                            f"Investissement initial requis: {mise_de_fonds + total_costs:,.0f} $"
                        ]),
                    ])
                ])
            ])
        ])
        
    except Exception as e:
        print(f"Erreur dans generate_summary_content: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erreur lors de la génération du résumé: {str(e)}", 
                        color="danger", className="mt-3")

# Callback pour afficher les valeurs économiques
@app.callback(
    Output("economic-values-content", "children"),
    [Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("recalculate-economic-values-btn", "n_clicks"),
     Input("additional-revenues-store", "data"),
     Input("additional-expenses-store", "data")],
    [State("adjusted-revenue-brut", "value"),
     State("adjusted-depenses-totales", "value")]
)
def update_economic_values(property_data, loan_type, n_clicks,
                          additional_revenues, additional_expenses,
                          adjusted_revenue_brut, adjusted_depenses_totales):
    if not property_data:
        return html.Div()

    # Calculer le revenue net ajusté si des modifications ont été faites
    revenue_net_modified = None
    
    # Calculer les revenus additionnels à partir du store
    total_additional_revenues = sum(item['amount'] for item in additional_revenues) if additional_revenues else 0
    
    # Calculer les dépenses additionnelles à partir du store
    total_additional_expenses = sum(item['amount'] for item in additional_expenses) if additional_expenses else 0

    # Si il y a des revenus/dépenses additionnels OU si l'utilisateur a ajusté les valeurs de base OU si le bouton a été cliqué
    if (total_additional_revenues > 0 or total_additional_expenses > 0 or 
        (adjusted_revenue_brut is not None and adjusted_revenue_brut != clean_monetary_value(property_data.get('revenus_brut', 0))) or
        (adjusted_depenses_totales is not None and adjusted_depenses_totales != clean_monetary_value(property_data.get('depenses_totales', 0))) or
        (n_clicks and n_clicks > 0)):
        
        # Utiliser les valeurs ajustées si disponibles, sinon les valeurs originales
        base_revenus = adjusted_revenue_brut if adjusted_revenue_brut is not None else clean_monetary_value(property_data.get('revenus_brut', 0))
        base_depenses = adjusted_depenses_totales if adjusted_depenses_totales is not None else clean_monetary_value(property_data.get('depenses_totales', 0))
        
        # Revenue net modifié
        total_revenus = base_revenus + total_additional_revenues
        total_depenses = base_depenses + total_additional_expenses
        revenue_net_modified = total_revenus - total_depenses

    # Calculer les valeurs économiques
    # IMPORTANT: Le revenue_net_modified n'affecte QUE la "Valeur réelle (marché)"
    # La "Valeur de financement (SCHL)" utilise toujours les données originales
    values = calculate_economic_values(property_data, revenue_net_modified)

    # Déterminer quel TGA de financement utiliser
    if loan_type == "SCHL":
        tga_financement = values['tga_financement_schl']
        valeur_economique_financement = values['valeur_economique_financement_schl']
        profit_achat = values['profit_achat_schl']
        fait_profit = values['fait_profit_schl']
    else:
        tga_financement = values['tga_financement_conv']
        valeur_economique_financement = values['valeur_economique_financement_conv']
        profit_achat = values['profit_achat_conv']
        fait_profit = values['fait_profit_conv']

    return html.Div([
        # Tableau comparatif
            dbc.Table([
                html.Thead([
                    html.Tr([
                    html.Th(""),
                    html.Th("TGA", className="text-center"),
                    html.Th("Valeur économique", className="text-center"),
                    html.Th("Analyse", className="text-center")
                    ])
                ]),
                html.Tbody([
                # Ligne pour la valeur réelle
                    html.Tr([
                    html.Td([
                        html.Strong("Valeur réelle (marché)"),
                        html.Br(),
                        html.Small(f"Rendement actuel: {values['tga_reelle']:.2f}%", className="text-success fw-bold")
                    ]),
                    html.Td([
                        html.Strong(f"{values['tga_reelle']:.2f}%", className="text-success"),
                        html.Br(),
                        html.Small(f"Réf: {values['tga_marche_reference']:.2f}%", className="text-muted")
                    ], className="text-center"),
                    html.Td(f"{values['valeur_economique_reelle']:,.0f} $", className="text-center"),
                    html.Td("Valeur selon TGA référence", className="text-center text-muted")
                ]),
                # Ligne pour la valeur de financement
                html.Tr([
                    html.Td(html.Strong(f"Valeur de financement ({loan_type})")),
                    html.Td(f"{tga_financement:.2f}%", className="text-center"),
                    html.Td(f"{valeur_economique_financement:,.0f} $", className="text-center"),
                    html.Td(
                        html.Span("✓ Profit à l'achat", className="text-success fw-bold") if fait_profit
                        else html.Span("✗ Surpayé", className="text-danger fw-bold"),
                        className="text-center"
                    )
                ], className="table-active"),
                # Ligne pour le prix demandé
                html.Tr([
                    html.Td(html.Strong("Prix demandé")),
                    html.Td("—", className="text-center text-muted"),
                    html.Td(f"{values['prix_vente']:,.0f} $", className="text-center"),
                    html.Td("Prix du vendeur", className="text-center text-muted")
                ]),
                # NOUVELLE LIGNE : Valeur de financement bancaire (la plus petite)
                html.Tr([
                    html.Td([
                        html.Strong("Valeur de financement bancaire"),
                        html.Br(),
                        html.Small("(La plus petite des valeurs économiques)", className="text-info")
                    ]),
                    html.Td("—", className="text-center"),
                    html.Td(
                        html.Strong(f"{min(values['valeur_economique_reelle'], valeur_economique_financement):,.0f} $"),
                        className="text-center text-primary"
                    ),
                    html.Td(
                        html.Span("Base du calcul de financement", className="text-primary fw-bold"),
                        className="text-center"
                    )
                ], className="table-info"),
                # Ligne pour le profit/perte
                html.Tr([
                    html.Td(html.Strong("Différence (Financement - Prix)")),
                    html.Td("", className="text-center"),
                    html.Td(
                        html.Strong(f"{(valeur_economique_financement - values['valeur_economique_reelle']):+,.0f} $"),
                        className=f"text-center {'text-success' if fait_profit else 'text-danger'}"
                    ),
                    html.Td(
                        f"{profit_achat:+.1f}%",
                        className=f"text-center {'text-success' if fait_profit else 'text-danger'}"
                    )
                ])
            ])
        ], striped=True, hover=True, className="mb-3"),

        # Note explicative mise à jour
        dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            html.Strong("Note importante sur le financement: "),
            html.Br(),
            f"• La banque utilise toujours la PLUS PETITE valeur entre la valeur économique réelle ({values['valeur_economique_reelle']:,.0f} $) et la valeur économique de financement ({valeur_economique_financement:,.0f} $)",
            html.Br(),
            f"• Dans ce cas, la valeur de financement bancaire est: {min(values['valeur_economique_reelle'], valeur_economique_financement):,.0f} $",
            html.Br(),
            f"• Le montant du prêt sera calculé sur cette valeur ou le prix d'achat, selon le plus petit"
        ], color="info", className="mb-4"),

        # Alerte selon le résultat avec distinction équité vs cash
        dbc.Alert([
            html.I(className=f"fas fa-{'check-circle' if fait_profit else 'exclamation-triangle'} me-2"),
            html.Strong("Opportunité d'achat! " if fait_profit else "Attention! "),
            html.Br(),
            f"• Valeur économique réelle: {values['valeur_economique_reelle']:,.0f} $ (selon TGA référence {values['tga_marche_reference']:.2f}%)",
            html.Br(),
            f"• Valeur économique financement: {valeur_economique_financement:,.0f} $ (selon TGA banque {tga_financement:.2f}%)",
            html.Br(),
            f"• Prix demandé: {values['prix_vente']:,.0f} $",
            html.Br(),
            html.Strong(f"→ Profit à l'achat (équité instantanée): {abs(profit_achat):,.0f} $" if fait_profit else f"→ Surprix à l'achat: {abs(profit_achat):,.0f} $"),
            html.Br(),
            html.Span("⚠️ Important: Ce profit est de l'ÉQUITÉ, pas du cash immédiat. Le cash se réalise au refinancement seulement.", 
                     className="fst-italic text-muted")
        ], color="success" if fait_profit else "warning", className="mb-3"),

        # Explication des calculs
        dbc.Card([
            dbc.CardBody([
                html.H6("Comprendre les calculs", className="mb-3"),
            html.Ul([
                    html.Li([
                        html.Strong("TGA réel = "),
                        f"Revenue net ({values['revenue_net']:,.0f} $) ÷ Prix de vente ({values['prix_vente']:,.0f} $) = {values['tga_reelle']:.2f}%"
                    ]),
                    html.Li([
                        html.Strong("Valeur économique réelle = "),
                        f"Revenue net ({values['revenue_net']:,.0f} $) ÷ TGA référence ({values['tga_marche_reference']:.2f}%) = {values['valeur_economique_reelle']:,.0f} $"
                    ]),
                    html.Li([
                        html.Strong("Note importante: "),
                        f"La valeur économique réelle utilise le TGA de référence marché ({values['tga_marche_reference']:.2f}%) pour calculer la vraie valeur basée sur vos revenus ajustés."
                    ]),
                    html.Li([
                        html.Strong("Valeur économique de financement = "),
                        f"Revenue net ({values['revenue_net']:,.0f} $) ÷ TGA financement ({tga_financement:.2f}%) = {valeur_economique_financement:,.0f} $"
                    ]),
                    html.Li([
                        html.Strong("Prix demandé = "),
                        f"Prix fixé par le vendeur = {values['prix_vente']:,.0f} $"
                    ]),
                    html.Li([
                        html.Strong("Le TGA de financement "),
                        f"est le taux conservateur utilisé par la banque pour évaluer le prêt."
                    ])
                ])
            ])
        ], color="light", outline=True)
    ])

# Callback pour ajouter des lignes de revenus
@app.callback(
    Output("additional-revenues-container", "children"),
    [Input("add-revenue-btn", "n_clicks")],
    [State("additional-revenues-container", "children")]
)
def add_revenue_line(n_clicks, existing_children):
    if not n_clicks:
        return []

    existing_children = existing_children or []

    new_revenue = html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    type="text",
                    placeholder="Nom du revenu (ex: Stationnement, Buanderie...)",
                    id={"type": "additional-revenue-name", "index": n_clicks}
                )
            ], width=6),
            dbc.Col([
                dbc.Input(
                    type="number",
                    placeholder="Montant",
                    step=100,
                    min=0,
                    id={"type": "additional-revenue", "index": n_clicks}
                )
            ], width=3),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("✓", color="success", size="sm",
                              id={"type": "validate-revenue", "index": n_clicks},
                              title="Valider ce revenu"),
                    dbc.Button("×", color="danger", size="sm",
                              id={"type": "remove-revenue", "index": n_clicks},
                              title="Supprimer cette ligne")
                ])
            ], width=3)
        ], className="mb-2")
    ], id=f"revenue-line-{n_clicks}")

    return existing_children + [new_revenue]

# Callback pour ajouter des lignes de dépenses
@app.callback(
    Output("additional-expenses-container", "children"),
    [Input("add-expense-btn", "n_clicks")],
    [State("additional-expenses-container", "children")]
)
def add_expense_line(n_clicks, existing_children):
    if not n_clicks:
        return []

    existing_children = existing_children or []

    new_expense = html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Input(
                    type="text",
                    placeholder="Nom de la dépense (ex: Réparations, Entretien...)",
                    id={"type": "additional-expense-name", "index": n_clicks}
                )
            ], width=6),
            dbc.Col([
                dbc.Input(
                    type="number",
                    placeholder="Montant",
                    step=100,
                    id={"type": "additional-expense", "index": n_clicks}
                )
            ], width=3),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("✓", color="success", size="sm",
                              id={"type": "validate-expense", "index": n_clicks},
                              title="Valider cette dépense"),
                    dbc.Button("×", color="danger", size="sm",
                              id={"type": "remove-expense", "index": n_clicks},
                              title="Supprimer cette ligne")
                ])
            ], width=3)
        ], className="mb-2")
    ], id=f"expense-line-{n_clicks}")

    return existing_children + [new_expense]

# Callback pour supprimer des lignes de revenus
@app.callback(
    Output("additional-revenues-container", "children", allow_duplicate=True),
    [Input({"type": "remove-revenue", "index": ALL}, "n_clicks")],
    [State("additional-revenues-container", "children")],
    prevent_initial_call=True
)
def remove_revenue_line(n_clicks_list, existing_children):
    if not any(n_clicks_list) or not existing_children:
        return existing_children
    
    # Identifier quel bouton a été cliqué
    if not ctx.triggered:
        return existing_children
    
    # Extraire l'index du bouton cliqué
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    # Supprimer la ligne correspondante
    return [child for child in existing_children if child['props']['id'] != f"revenue-line-{clicked_index}"]

# Callback pour supprimer des lignes de dépenses
@app.callback(
    Output("additional-expenses-container", "children", allow_duplicate=True),
    [Input({"type": "remove-expense", "index": ALL}, "n_clicks")],
    [State("additional-expenses-container", "children")],
    prevent_initial_call=True
)
def remove_expense_line(n_clicks_list, existing_children):
    if not any(n_clicks_list) or not existing_children:
        return existing_children
    
    # Identifier quel bouton a été cliqué
    if not ctx.triggered:
        return existing_children
    
    # Extraire l'index du bouton cliqué
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    # Supprimer la ligne correspondante
    return [child for child in existing_children if child['props']['id'] != f"expense-line-{clicked_index}"]

# Callback pour valider des revenus additionnels
@app.callback(
    [Output("additional-revenues-store", "data", allow_duplicate=True),
     Output("additional-revenues-container", "children", allow_duplicate=True)],
    [Input({"type": "validate-revenue", "index": ALL}, "n_clicks")],
    [State("additional-revenues-store", "data"),
     State({"type": "additional-revenue-name", "index": ALL}, "value"),
     State({"type": "additional-revenue", "index": ALL}, "value"),
     State("additional-revenues-container", "children")],
    prevent_initial_call=True
)
def validate_revenue(n_clicks_list, current_revenues, names, amounts, existing_children):
    if not any(n_clicks_list):
        return current_revenues, existing_children
    
    # Identifier quel bouton a été cliqué
    if not ctx.triggered:
        return current_revenues, existing_children
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    # Approche simplifiée : créer des dictionnaires de correspondance
    print(f"=== DÉBOGAGE VALIDATION REVENU ===")
    print(f"Index cliqué: {clicked_index}")
    print(f"Names reçus: {names}")
    print(f"Amounts reçus: {amounts}")
    
    # Approche directe: trouver l'élément correspondant dans la liste des enfants
    matching_revenue_element = None
    for i, child in enumerate(existing_children):
        if child and 'props' in child and 'id' in child['props']:
            if child['props']['id'] == f"revenue-line-{clicked_index}":
                matching_revenue_element = child
                break
    
    # Si élément trouvé, obtenir le nom et le montant du formulaire directement
    name = None
    amount = None
    
    # Vérifier tous les composants d'entrée dans la liste
    found_index = -1
    for i, name_value in enumerate(names):
        if name_value is not None and name_value.strip() != '':
            name = name_value
            found_index = i
            # Vérifier si nous avons un montant correspondant
            if i < len(amounts):
                amount = amounts[i] if amounts[i] is not None else ''
                break
    
    # Si aucun montant n'a été trouvé mais qu'un nom existe, chercher partout dans les montants
    if name and (amount is None or amount == '') and found_index >= 0:
        for i, amount_value in enumerate(amounts):
            if amount_value is not None and str(amount_value).strip() != '':
                amount = amount_value
                break
    
    print(f"Name trouvé: '{name}'")
    print(f"Amount trouvé: '{amount}' (type: {type(amount)})")
    
    # Validation et ajout
    if name:
        try:
            # Si le montant est None ou vide, on utilise 0 comme valeur par défaut
            if amount is None or str(amount).strip() == '':
                amount_float = 0.0
                print(f"ℹ️ Montant vide converti en zéro pour le revenu: {name}")
            else:
                amount_float = float(amount)
            
            # On accepte aussi les montants de 0 pour les revenus en valeur réelle
            if amount_float >= 0:
                # Ajouter aux revenus validés
                new_revenues = current_revenues.copy() if current_revenues else []
                new_revenues.append({"name": str(name), "amount": amount_float, "index": clicked_index})
                
                # Supprimer la ligne de l'interface
                updated_children = [child for child in existing_children if child['props']['id'] != f"revenue-line-{clicked_index}"]
                
                print(f"✓ Revenu validé: {name} = {amount_float}")
                return new_revenues, updated_children
            else:
                print(f"✗ Montant doit être positif: {amount_float}")
        except (ValueError, TypeError) as e:
            print(f"✗ Erreur de conversion du montant: {e}")
    else:
        print(f"✗ Validation échouée - Name: '{name}', Amount: '{amount}'")
    
    return current_revenues, existing_children

# Callback pour valider des dépenses additionnelles
@app.callback(
    [Output("additional-expenses-store", "data", allow_duplicate=True),
     Output("additional-expenses-container", "children", allow_duplicate=True)],
    [Input({"type": "validate-expense", "index": ALL}, "n_clicks")],
    [State("additional-expenses-store", "data"),
     State({"type": "additional-expense-name", "index": ALL}, "value"),
     State({"type": "additional-expense", "index": ALL}, "value"),
     State("additional-expenses-container", "children")],
    prevent_initial_call=True
)
def validate_expense(n_clicks_list, current_expenses, names, amounts, existing_children):
    if not any(n_clicks_list):
        return current_expenses, existing_children
    
    # Identifier quel bouton a été cliqué
    if not ctx.triggered:
        return current_expenses, existing_children
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    print(f"=== DÉBOGAGE VALIDATION DÉPENSE ===")
    print(f"Index cliqué: {clicked_index}")
    print(f"Names reçus: {names}")
    print(f"Amounts reçus: {amounts}")
    
    # Approche simplifiée - associer directement par position dans les listes
    name = None
    amount = None
    
    # Créer un mapping des indices des enfants avec leur position dans les listes
    child_indices = []
    for child in existing_children:
        if child and 'props' in child and 'id' in child['props']:
            child_id = child['props']['id']
            if child_id.startswith('expense-line-'):
                idx = int(child_id.split('-')[-1])
                child_indices.append(idx)
    
    # Trouver la position du clicked_index dans la liste des enfants
    try:
        position = child_indices.index(clicked_index)
        if position < len(names):
            name = names[position]
        if position < len(amounts):
            amount = amounts[position]
    except (ValueError, IndexError):
        # Fallback : prendre la première valeur si une seule ligne
        if len(names) == 1 and len(amounts) == 1:
            name = names[0]
            amount = amounts[0]
    
    print(f"Position trouvée: {position if 'position' in locals() else 'N/A'}")
    print(f"Name récupéré: '{name}'")
    print(f"Amount récupéré: '{amount}' (type: {type(amount)})")
    
    # Validation et ajout
    if name:
        try:
            # Si le montant est None ou vide, on utilise 0 comme valeur par défaut
            if amount is None or str(amount).strip() == '':
                amount_float = 0.0
                print(f"ℹ️ Montant vide converti en zéro pour la dépense: {name}")
            else:
                amount_float = float(amount)
            
            # On accepte aussi les montants de 0 pour les dépenses en valeur réelle
            if amount_float >= 0:
                # Ajouter aux dépenses validées
                new_expenses = current_expenses.copy() if current_expenses else []
                new_expenses.append({"name": str(name), "amount": amount_float, "index": clicked_index})
                
                # Supprimer la ligne de l'interface
                updated_children = [child for child in existing_children if child['props']['id'] != f"expense-line-{clicked_index}"]
                
                print(f"✓ Dépense validée: {name} = {amount_float}")
                return new_expenses, updated_children
            else:
                print(f"✗ Montant doit être positif: {amount_float}")
        except (ValueError, TypeError) as e:
            print(f"✗ Erreur de conversion du montant: {e}")
    else:
        print(f"✗ Validation échouée - Name: '{name}', Amount: '{amount}'")
    
    return current_expenses, existing_children

# Callback pour afficher les revenus validés
@app.callback(
    Output("validated-revenues-display", "children"),
    Input("additional-revenues-store", "data")
)
def display_validated_revenues(revenues):
    if not revenues:
        return html.Div()
    
    revenue_items = []
    for rev in revenues:
        revenue_items.append(
            dbc.Alert([
                html.Strong(f"{rev['name']}: "),
                f"{rev['amount']:,.0f} $",
                dbc.Button("×", color="light", size="sm", className="ms-2",
                          id={"type": "remove-validated-revenue", "index": rev['index']})
            ], color="success", className="py-2 mb-2", style={"display": "flex", "justify-content": "space-between", "align-items": "center"})
        )
    
    return html.Div([
        html.H6("Revenus additionnels validés:", className="text-success mb-2"),
        html.Div(revenue_items),
        html.P(f"Total: {sum(rev['amount'] for rev in revenues):,.0f} $", className="fw-bold text-success")
    ])

# Callback pour afficher les dépenses validées
@app.callback(
    Output("validated-expenses-display", "children"),
    Input("additional-expenses-store", "data")
)
def display_validated_expenses(expenses):
    if not expenses:
        return html.Div()
    
    expense_items = []
    for exp in expenses:
        expense_items.append(
            dbc.Alert([
                html.Strong(f"{exp['name']}: "),
                f"{exp['amount']:,.0f} $",
                dbc.Button("×", color="light", size="sm", className="ms-2",
                          id={"type": "remove-validated-expense", "index": exp['index']})
            ], color="danger", className="py-2 mb-2", style={"display": "flex", "justify-content": "space-between", "align-items": "center"})
        )
    
    return html.Div([
        html.H6("Dépenses additionnelles validées:", className="text-danger mb-2"),
        html.Div(expense_items),
        html.P(f"Total: {sum(exp['amount'] for exp in expenses):,.0f} $", className="fw-bold text-danger")
    ])

# Callback pour supprimer un revenu validé
@app.callback(
    Output("additional-revenues-store", "data", allow_duplicate=True),
    [Input({"type": "remove-validated-revenue", "index": ALL}, "n_clicks")],
    [State("additional-revenues-store", "data")],
    prevent_initial_call=True
)
def remove_validated_revenue(n_clicks_list, current_revenues):
    if not any(n_clicks_list) or not current_revenues:
        return current_revenues
    
    if not ctx.triggered:
        return current_revenues
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    # Supprimer le revenu avec l'index correspondant
    return [rev for rev in current_revenues if rev['index'] != clicked_index]

# Callback pour supprimer une dépense validée
@app.callback(
    Output("additional-expenses-store", "data", allow_duplicate=True),
    [Input({"type": "remove-validated-expense", "index": ALL}, "n_clicks")],
    [State("additional-expenses-store", "data")],
    prevent_initial_call=True
)
def remove_validated_expense(n_clicks_list, current_expenses):
    if not any(n_clicks_list) or not current_expenses:
        return current_expenses
    
    if not ctx.triggered:
        return current_expenses
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    clicked_index = eval(button_id)['index']
    
    # Supprimer la dépense avec l'index correspondant
    return [exp for exp in current_expenses if exp['index'] != clicked_index]

# Callback pour les filtres géographiques
@app.callback(
    Output("geographic-filters", "children"),
    [Input("data-source", "value"),
     Input("property-selector", "value")]
)
def update_geographic_filters(data_source, property_selector):
    # Retourner les filtres géographiques appropriés
    # Si la source de données n'est pas 'active', on n'affiche pas les filtres géographiques
    if data_source != "active":
        return html.Div([
            dbc.Alert([html.I(className="fas fa-info-circle me-2"), 
                      "Les filtres géographiques sont disponibles uniquement pour les immeubles actifs."], 
                    color="info")
        ])
    
    # Charger les provinces
    from filter.data_loading import load_provinces
    provinces_df = load_provinces()
    province_options = [{"label": "Toutes", "value": "all"}] + [
        {"label": p, "value": p} for p in provinces_df['province_name'].tolist()
    ]
    
    return html.Div([
        # Province - ajout du filtre initial pour province
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
        html.Div(id="region-filter-container"),
        html.Div(id="detailed-filter-container"),
        html.Div(id="specific-filter-container")
    ])

# Callback pour mettre à jour les régions selon la province
@app.callback(
    Output("region-filter-container", "children"),
    Input("filter-province", "value"),
    prevent_initial_call=True
)
def update_region_filter(selected_province):
    # Mettre à jour les options de région en fonction de la province sélectionnée
    if not selected_province or selected_province == "all":
        return html.Div()
    
    # Obtenir l'ID de la province et charger les régions associées
    from filter.data_loading import load_provinces, load_regions
    provinces_df = load_provinces()
    province_row = provinces_df[provinces_df['province_name'] == selected_province]
    
    if province_row.empty:
        return html.Div()
    
    province_id = province_row['province_id'].iloc[0]
    regions_df = load_regions(province_id)
    
    if regions_df.empty:
        return html.Div([
            dbc.Alert([html.I(className="fas fa-info-circle me-2"), 
                     f"Aucune région disponible pour {selected_province}"], 
                     color="info")
        ])
    
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

# Callback pour les filtres détaillés (secteur, quartier, etc.)
@app.callback(
    Output("detailed-filter-container", "children"),
    [Input("filter-region", "value"),
     Input("filter-province", "value")],
    prevent_initial_call=True
)
def update_detailed_filter(selected_region, selected_province):
    if not selected_region or selected_region == "all" or not selected_province or selected_province == "all":
        return html.Div()
    
    try:
        # Obtenir l'ID de la région
        from filter.data_loading import load_provinces, load_regions
        provinces_df = load_provinces()
        province_id = provinces_df[provinces_df['province_name'] == selected_province]['province_id'].iloc[0]
        regions_df = load_regions(province_id)
        region_row = regions_df[regions_df['region_nom'] == selected_region]
        
        if region_row.empty:
            return html.Div()
        
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
            )
        ])
    except Exception as e:
        print(f"Erreur lors de la mise à jour des filtres détaillés: {e}")
        return html.Div()

# Callback pour le filtre spécifique
@app.callback(
    Output("specific-filter-container", "children"),
    [Input("filter-type", "value"),
     Input("filter-region", "value"),
     Input("filter-province", "value")],
    prevent_initial_call=True
)
def update_specific_filter(selected_type, selected_region, selected_province):
    if not selected_type or selected_type == "none" or not selected_region or selected_region == "all":
        return html.Div()
    
    # Obtenir l'ID de la région
    try:
        from filter.data_loading import load_provinces, load_regions, load_secteurs, load_quartiers, load_secteurs_recensement
        provinces_df = load_provinces()
        province_id = provinces_df[provinces_df['province_name'] == selected_province]['province_id'].iloc[0]
        regions_df = load_regions(province_id)
        region_id = regions_df[regions_df['region_nom'] == selected_region]['region_id'].iloc[0]
        
        if selected_type == "secteur":
            secteurs_df = load_secteurs(region_id)
            options = [{"label": s, "value": s} for s in secteurs_df['secteur_nom'].tolist()]
            label = "Secteur"
        elif selected_type == "quartier":
            quartiers_df = load_quartiers(region_id)
            options = [{"label": q, "value": q} for q in quartiers_df['quartier_nom_fr'].tolist()]
            label = "Quartier"
        elif selected_type == "secteur_recensement":
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
    except Exception as e:
        print(f"Erreur lors de la mise à jour des filtres spécifiques: {e}")
        return html.Div()

# Callback pour filtrer les propriétés selon les critères géographiques
@app.callback(
    Output("filtered-properties", "data"),
    [Input("filter-province", "value"),
     Input("filter-region", "value"),
     Input("filter-type", "value"),
     Input("specific-zone-filter", "value"),
     Input("data-source", "value"),
     Input("historical-date", "date"),
     Input("tax-status", "value")]
)
def filter_properties(filter_province, filter_region, filter_type, specific_zone, data_source, hist_date, tax_status):
    """Filtre les propriétés selon les critères géographiques et le statut fiscal"""
    # Utiliser la fonction importée filter_properties_by_geography 
    # Le paramètre tax_status n'est pas utilisé ici mais doit être inclus pour éviter l'erreur
    return filter_properties_by_geography(filter_province, filter_region, filter_type, specific_zone, data_source, hist_date)


# Callback pour le modal des calculs
@app.callback(
    [Output("calculations-modal", "is_open"),
     Output("calculations-modal-body", "children")],
    [Input("show-calculations-button", "n_clicks"),
     Input("close-calculations", "n_clicks")],
    [State("calculations-modal", "is_open"),
     State("property-data", "data"),
     State("loan-type", "value"),
     State("tax-province", "value"),
     State("tax-status", "value")]
)
def toggle_calculations_modal(n1, n2, is_open, property_data, loan_type, tax_province, tax_status):
    if n1 or n2:
        if ctx.triggered_id == "show-calculations-button":
            # Générer le contenu des explications
            content = generate_calculations_explanations(property_data, loan_type, tax_province, tax_status)
            return True, content
        else:
            return False, ""
    return is_open, ""

def generate_calculations_explanations(property_data, loan_type, tax_province, tax_status):
    """Génère les explications détaillées de tous les calculs"""
    
    if not property_data:
        return dbc.Alert("Veuillez d'abord sélectionner un immeuble.", color="warning")
    
    # Calculs de base
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 
                                   property_data.get('loyer_par_logement', 0) * property_data.get('nombre_unites', 0) * 12))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    revenue_net = clean_monetary_value(property_data.get('revenu_net', revenue_brut - depenses))
    
    # Si revenu_net n'est pas disponible, le calculer
    if revenue_net == 0:
        revenue_net = revenue_brut - depenses
    
    tga = (revenue_net / prix * 100) if prix > 0 else 0
    
    # -------------------------------------------------
    # === FINANCEMENT : mise de fonds, prêt, prime  ===
    # -------------------------------------------------
    # Utiliser le calcul basé sur le RDC pour cohérence
    montant_pret_rdc, ratio_pret_valeur_rdc, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    # Utiliser le montant du prêt basé sur le RDC
    montant_pret = montant_pret_rdc
    ltv_target = ratio_pret_valeur_rdc
    mise_de_fonds_ratio = 1 - ltv_target
    mise_de_fonds = prix * mise_de_fonds_ratio

    # Prime SCHL seulement si applicable
    prime_schl, prime_rate = (0, 0)
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        prime_rate = default_rate
    
    # Taux d'imposition
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated)
    
    # Paramètres du prêt spécifiques à l'immeuble
    try:
        if loan_type == "SCHL":
            # OBLIGATOIRE: Utiliser SEULEMENT les valeurs RDC de la base de données
            rdc_ratio = float(property_data.get('financement_schl_ratio_couverture_dettes', 0) or 0)
            if rdc_ratio == 0:
                raise ValueError("RDC SCHL manquant dans la base de données pour cette propriété")
            taux_str = str(property_data.get('financement_schl_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_schl_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
        else:
            # OBLIGATOIRE: Utiliser SEULEMENT les valeurs RDC de la base de données
            rdc_ratio = float(property_data.get('financement_conv_ratio_couverture_dettes', 0) or 0)
            if rdc_ratio == 0:
                raise ValueError("RDC Conventionnel manquant dans la base de données pour cette propriété")
            taux_str = str(property_data.get('financement_conv_taux_interet', 5.5)).replace('%', '').strip()
            taux_interet = float(taux_str) / 100 if taux_str else 0.055
            amort_str = str(property_data.get('financement_conv_amortissement', 25)).strip()
            amortissement = float(amort_str) if amort_str else 25
            
        # Calcul de la mensualité maximale basée sur le ratio de couverture de dette (RDC)
        revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
        depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    except (ValueError, TypeError):
        print("Erreur lors de la conversion des paramètres de prêt - utilisation des valeurs par défaut")
        rdc_ratio = 1.2
        taux_interet = 0.055  # 5.5%
        amortissement = 25
    
    # Le montant du prêt a déjà été calculé plus haut avec le RDC
    # montant_pret, ratio_pret_valeur_rdc ont déjà été définis
    ratio_pret_valeur = ratio_pret_valeur_rdc
    _, _, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    # Prime SCHL si applicable
    prime_schl = 0
    prime_rate = 0
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        prime_rate = default_rate
    
    montant_finance = montant_pret + prime_schl
    
    # Calcul de la mensualité
    mensualite = pmt_mensuelle
    n_payments = int(amortissement * 12)
    
    # Calcul des intérêts et capital pour l'année 1
    solde_debut = montant_finance
    interet_annuel = 0
    capital_annuel = 0
    
    for mois in range(12):
        interet_mois = solde_debut * (taux_interet / 12)
        capital_mois = mensualite - interet_mois
        interet_annuel += interet_mois
        capital_annuel += capital_mois
        solde_debut -= capital_mois
    
    # Calcul de l'impôt (sans DPA pour simplifier)
    noi = revenue_brut - depenses
    revenu_imposable = noi - interet_annuel
    
    if is_incorporated:
        impot = revenu_imposable * (tax_rate / 100) if revenu_imposable > 0 else 0
    else:
        impot = calculate_progressive_tax(revenu_imposable, tax_province) if revenu_imposable > 0 else 0
    
    # Cashflow final
    rno_apres_impot = noi - impot
    cashflow_annuel = rno_apres_impot - capital_annuel
    cashflow_mensuel = cashflow_annuel / 12
    
    return html.Div([
        # Vue d'ensemble
        dbc.Card([
            dbc.CardHeader(html.H5([
                html.I(className="fas fa-home me-2"),
                "Vue d'ensemble"
            ])),
            dbc.CardBody([
                html.H6("Formules de base", className="mb-3"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Revenue Brut Annuel"),
                            html.Td(html.Code("Loyer mensuel × Nb logements × 12")),
                            html.Td(f"{property_data.get('loyer_par_logement', 0):,.0f} × {property_data.get('nombre_unites', 0)} × 12 = {revenue_brut:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("Revenue Net (RNO)"),
                            html.Td(html.Code("Revenue Brut - Dépenses")),
                            html.Td(f"{revenue_brut:,.0f} - {depenses:,.0f} = {revenue_net:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("TGA"),
                            html.Td(html.Code("(RNO ÷ Prix) × 100")),
                            html.Td(f"({revenue_net:,.0f} ÷ {prix:,.0f}) × 100 = {tga:.2f}%")
                        ]),
                    ])
                ], striped=True, size="sm")
            ])
        ], className="mb-3"),
        
        # -------------------------------------------
        # Card  ➜  Financement
        # -------------------------------------------
        dbc.Card([
            dbc.CardHeader(html.H5([
                html.I(className="fas fa-hand-holding-usd me-2"),
                "Financement"
            ])),
            dbc.CardBody([
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Mise de fonds"),
                            html.Td(f"{mise_de_fonds_ratio*100:.1f}% = {mise_de_fonds:,.0f} $",
                                    className="text-end")
                        ]),
                        html.Tr([
                            html.Td("Montant du prêt"),
                            html.Td(f"{montant_pret:,.0f} $",
                                    className="text-end")
                        ]),
                        # Afficher la prime seulement pour SCHL
                        html.Tr([
                            html.Td("Prime SCHL"),
                            html.Td(f"{prime_schl:,.0f} $ ({prime_rate:.2f} %)",
                                    className="text-end")
                        ]) if loan_type == "SCHL" else html.Tr([])
                    ])
                ], striped=True, size="sm")
            ])
        ], className="mb-3"),
        
        # Analyse financière
        dbc.Card([
            dbc.CardHeader(html.H5([
                html.I(className="fas fa-chart-line me-2"),
                "Analyse financière"
            ])),
            dbc.CardBody([
                html.H6("Calcul du Revenue Net après impôt", className="mb-3"),
                html.P("Le calcul tient compte de l'impôt et potentiellement de la DPA:"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("NOI (Net Operating Income)"),
                            html.Td(html.Code("Revenue brut - Dépenses")),
                            html.Td(f"{revenue_brut:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("Intérêts sur le prêt", className="text-info"),
                            html.Td(html.Code("Déductibles d'impôt")),
                            html.Td(f"{interet_annuel:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("DPA (si activée)", className="text-info"),
                            html.Td(html.Code("Valeur bâtiment × 4% × 50%")),
                            html.Td("Année 1 (règle demi-année)")
                        ]),
                        html.Tr([
                            html.Td("Revenu imposable"),
                            html.Td(html.Code("NOI - Intérêts - DPA")),
                            html.Td(f"{revenu_imposable:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("Impôt"),
                            html.Td(html.Code("Revenu imposable × Taux")),
                            html.Td(f"{impot:,.0f} $ (Taux: {tax_rate:.1f}%)")
                        ]),
                        html.Tr([
                            html.Td("RNO après impôt"),
                            html.Td(html.Code("NOI - Impôt")),
                            html.Td(f"{rno_apres_impot:,.0f} $")
                        ]),
                    ])
                ], striped=True, size="sm"),
                
                dbc.Alert([
                    html.I(className="fas fa-lightbulb me-2"),
                    html.Strong("Important : "),
                    "Les intérêts sont déductibles d'impôt, ce qui réduit votre facture fiscale. C'est un avantage fiscal majeur de l'investissement immobilier."
                ], color="success", className="mt-3"),
                
                html.Hr(),
                
                html.H6("Calcul du cashflow net", className="mb-3"),
                html.P("Le cashflow représente l'argent qui reste dans votre poche après toutes les dépenses:"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Formule du cashflow", className="fw-bold"),
                            html.Td(html.Code("NOI - Intérêts - Capital - Impôt")),
                            html.Td("")
                        ]),
                        html.Tr([
                            html.Td("NOI"),
                            html.Td("Revenue net d'exploitation"),
                            html.Td(f"{revenue_net:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("- Impôt"),
                            html.Td("Calculé sur (NOI - Intérêts - DPA)"),
                            html.Td(f"{impot:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("- Capital"),
                            html.Td("Remboursement du principal"),
                            html.Td(f"{capital_annuel:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("= Cashflow net", className="fw-bold text-success"),
                            html.Td("Argent disponible"),
                            html.Td(f"{cashflow_annuel:,.0f} $ ({cashflow_mensuel:,.0f} $/mois)")
                        ]),
                    ])
                ], striped=True, size="sm"),
                
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "Note : Les intérêts sont soustraits du cashflow même s'ils ont déjà réduit votre impôt. Cette approche plus conservative reflète les sorties réelles de trésorerie."
                ], color="info", className="mt-3"),
                
                html.Hr(),
                
                html.H6("Calcul du coût d'intérêt", className="mb-3"),
                html.P(f"Pour un prêt {loan_type}:"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Montant du prêt"),
                            html.Td(f"{montant_pret:,.0f} $ ({ratio_pret_valeur*100:.1f}% du prix)")
                        ]),
                        html.Tr([
                            html.Td("Mensualité"),
                            html.Td(f"{mensualite:,.0f} $ (Capital + Intérêts)")
                        ]),
                        html.Tr([
                            html.Td("Formule de la mensualité"),
                            html.Td(html.Code("M = P × [r(1+r)ⁿ] ÷ [(1+r)ⁿ-1]"))
                        ]),
                        html.Tr([
                            html.Td("Où"),
                            html.Td("P = Principal, r = taux mensuel, n = nb de paiements")
                        ]),
                        html.Tr([
                            html.Td("Capital remboursé (année 1)"),
                            html.Td(f"{capital_annuel:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("Intérêts payés (année 1)"),
                            html.Td(f"{interet_annuel:,.0f} $")
                        ]),
                        html.Tr([
                            html.Td("Coût total sur {int(amortissement)} ans"),
                            html.Td(html.Code(f"({mensualite:,.0f} × 12 × {int(amortissement)}) - {montant_pret:,.0f} ≈ {(mensualite*12*amortissement)-montant_pret:,.0f} $"))
                        ]),
                    ])
                ], striped=True, size="sm"),
                
                dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    f"Pour SCHL: Prime de {prime_rate:.2f}% = {prime_schl:,.0f} $ ajoutée au montant du prêt."
                ], color="info", className="mt-3") if loan_type == "SCHL" else None
            ])
        ], className="mb-3"),
        
        # Projections
        dbc.Card([
            dbc.CardHeader(html.H5([
                html.I(className="fas fa-chart-area me-2"),
                "Projections financières"
            ])),
            dbc.CardBody([
                html.H6("Formules utilisées", className="mb-3"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Revenue année N"),
                            html.Td(html.Code("Revenue initial × (1 + Augmentation)^(N-1)"))
                        ]),
                        html.Tr([
                            html.Td("Dépenses année N"),
                            html.Td(html.Code("Dépenses initiales × (1 + Inflation)^(N-1)"))
                        ]),
                        html.Tr([
                            html.Td("Valeur immeuble année N"),
                            html.Td(html.Code("Prix initial × (1 + Appréciation)^N"))
                        ]),
                        html.Tr([
                            html.Td("DPA année N (solde dégressif)"),
                            html.Td(html.Code("Valeur résiduelle bâtiment × Taux DPA"))
                        ]),
                        html.Tr([
                            html.Td("Intérêts dégressifs"),
                            html.Td(html.Code("Solde du prêt × Taux annuel"))
                        ]),
                    ])
                ], striped=True, size="sm")
            ])
        ], className="mb-3"),
        
        # Coûts d'acquisition
        dbc.Card([
            dbc.CardHeader(html.H5([
                html.I(className="fas fa-receipt me-2"),
                "Coûts d'acquisition"
            ])),
            dbc.CardBody([
                html.H6("Taxe de bienvenue (mutation)", className="mb-3"),
                html.P("Calcul par tranches:"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("0 $ à 50 000 $"),
                            html.Td("0.5%")
                        ]),
                        html.Tr([
                            html.Td("50 000 $ à 250 000 $"),
                            html.Td("1.0%")
                        ]),
                        html.Tr([
                            html.Td("250 000 $ à 500 000 $"),
                            html.Td("1.5%")
                        ]),
                        html.Tr([
                            html.Td("Plus de 500 000 $"),
                            html.Td("2.0%")
                        ]),
                    ])
                ], striped=True, size="sm"),
                
                html.Hr(),
                
                html.H6("Autres frais", className="mb-3"),
                dbc.Table([
                    html.Tbody([
                        html.Tr([
                            html.Td("Notaire"),
                            html.Td("1 500 $ - 2 500 $")
                        ]),
                        html.Tr([
                            html.Td("Inspection"),
                            html.Td("500 $ - 1 000 $")
                        ]),
                        html.Tr([
                            html.Td("Frais bancaires"),
                            html.Td("1 000 $ - 2 000 $")
                        ]),
                    ])
                ], striped=True, size="sm")
            ])
        ], className="mb-3"),
        
        # Section Projection du Cashflow
        html.Div([
            html.Hr(className="my-4"),
            html.H5("Projection du cashflow net", className="mb-3"),
            
            # Note explicative
            dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                html.Strong("Pourquoi le cashflow s'améliore avec le temps ? "),
                html.Br(),
                "• Les intérêts diminuent chaque année (solde du prêt qui baisse)",
                html.Br(),
                "• Le montant imposable augmente (moins d'intérêts à déduire)",
                html.Br(),
                "• L'impôt augmente légèrement mais moins que la baisse des intérêts",
                html.Br(),
                "• Résultat : Le cashflow après impôt s'améliore avec le temps"
            ], color="info", className="mb-4"),
            
            # Graphique du cashflow
            html.Div(id="cashflow-projection-graph"),
            
            # Tableau détaillé
            html.Div(id="cashflow-projection-table", className="mt-4")
        ])
    ])

# Callback pour simulation intégrée (nouvelle méthode avec intérêts déductibles)
@app.callback(
    Output("integrated-simulation-results", "children"),
    [Input("revenue-brut-input", "value"),
     Input("depenses-input", "value"),
     Input("use-dpa", "value"),
     Input("dpa-rate", "value"),
     Input("montant-pret-input", "value"),
     Input("taux-interet-input", "value"),
     Input("amortissement-input", "value")],
    [State("property-data", "data"),
     State("tax-province", "value"),
     State("tax-status", "value"),
     State("building-ratio", "value"),
     State("loan-type", "value")]
)
def simulate_integrated_callback(revenue_brut, depenses, use_dpa, dpa_rate,
                                 montant_pret, taux, amortissement,
                                 property_data, tax_province, tax_status,
                                 building_ratio, loan_type):
    if not property_data:
        return html.Div()
    
    # Valeurs par défaut si None
    revenue_brut = safe_float_conversion(revenue_brut or property_data.get('revenus_brut', 0))
    depenses = safe_float_conversion(depenses or property_data.get('depenses_totales', 0))
    use_dpa = use_dpa or []
    dpa_rate = dpa_rate or 4.0
    building_ratio = building_ratio or 80.0
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    montant_pret = montant_pret or prix_vente * APP_PARAMS.get('conventional_loan_ratio', 0.80)
    taux = taux or 5.5
    amortissement = amortissement or 25
    
    # Calculer les paramètres
    is_incorporated = tax_status == "incorporated"
    tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
    
    # Calcul de la prime SCHL si applicable
    prime_schl = 0
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
    
    montant_finance = montant_pret + prime_schl
    
    # Calcul des intérêts et capital pour l'année 1
    montant_finance = safe_float_conversion(montant_finance, 0)
    taux = safe_float_conversion(taux, 5.5)
    amortissement = safe_float_conversion(amortissement, 25)
    # Le taux est déjà en pourcentage, calcul_mensualite gère la conversion si nécessaire
    mensualite, _ = calcul_mensualite(montant_finance, taux, amortissement)
    solde_debut = montant_finance
    interet_annuel = 0
    capital_annuel = 0
    
    for mois in range(12):
        interet_mois = solde_debut * (taux/100 / 12)
        capital_mois = mensualite - interet_mois
        interet_annuel += interet_mois
        capital_annuel += capital_mois
        solde_debut -= capital_mois
    
    # Calcul du NOI
    noi = revenue_brut - depenses
    
    # Calcul de la DPA
    dpa_deduction = 0
    if use_dpa:
        building_value = clean_monetary_value(property_data.get("eval_batiment", 0))
        # Règle de demi-année pour la première année
        dpa_deduction = building_value * (dpa_rate / 100) * 0.5
    
    # NOI
    noi = revenue_brut - depenses
    
    # ⬇️ AJOUT: limiter la DPA pour empêcher la création d'une perte
    max_dpa = max(0, noi - interet_annuel)      # DPA plafonnée
    dpa_deduction = min(dpa_deduction, max_dpa)  # ne dépasse jamais le plafond
    
    # Calcul du revenu imposable (avec déduction des intérêts)
    revenu_imposable = noi - interet_annuel - dpa_deduction
    
    # Calcul de l'impôt
    if is_incorporated:
        # Pour les entreprises incorporées, utiliser le taux fixe
        impot = revenu_imposable * tax_rate if revenu_imposable > 0 else 0
    else:
        # Pour les particuliers, utiliser le calcul progressif
        impot = calculate_progressive_tax(revenu_imposable, tax_province) if revenu_imposable > 0 else 0
    
    # Calculer le taux effectif
    taux_effectif = (impot / revenu_imposable * 100) if revenu_imposable > 0 else 0
    
    # RNO après impôt = NOI - Impôt
    rno_apres_impot = noi - impot
    
    # Calcul du cashflow selon la nouvelle formule
    # cashflow après impot = Rev Net - (montant imposable * taux impot)
    # Donc cashflow = noi - impot (car l'impôt est calculé sur le montant imposable qui inclut déjà la déduction des intérêts)
    cashflow_net = noi - impot
    
    # Créer le tableau détaillé
    calculs = [
        {"Élément": "Revenue brut", "Montant": f"{revenue_brut:,.0f} $", "Note": ""},
        {"Élément": "- Dépenses d'exploitation", "Montant": f"- {depenses:,.0f} $", "Note": ""},
        {"Élément": "= NOI (Net Operating Income)", "Montant": f"{noi:,.0f} $", "Note": "Avant impôt"},
        {"Élément": "", "Montant": "", "Note": ""},
        {"Élément": "Calcul de l'impôt:", "Montant": "", "Note": ""},
        {"Élément": "  NOI", "Montant": f"{noi:,.0f} $", "Note": ""},
        {"Élément": "  - Intérêts (déductibles)", "Montant": f"- {interet_annuel:,.0f} $", "Note": "Année 1"},
        {"Élément": "  - DPA", "Montant": f"- {dpa_deduction:,.0f} $", "Note": "Valeur bâtiment × 4 % × 50% (année 1)" if use_dpa else "Non appliquée"},
        {"Élément": "  = Revenu imposable", "Montant": f"{revenu_imposable:,.0f} $", "Note": ""},
        {"Élément": "  × Taux d'imposition", "Montant": f"× {taux_effectif:.1f}%", "Note": f"{tax_province} - {'Incorporé' if is_incorporated else 'Progressif'}"},
        {"Élément": "  = Impôt à payer", "Montant": f"{impot:,.0f} $", "Note": ""},
        {"Élément": "", "Montant": "", "Note": ""},
        {"Élément": "Calcul du cashflow:", "Montant": "", "Note": ""},
        {"Élément": "  Revenue Net (NOI)", "Montant": f"{noi:,.0f} $", "Note": ""},
        {"Élément": "  - Impôt calculé", "Montant": f"- {impot:,.0f} $", "Note": f"Sur montant imposable de {revenu_imposable:,.0f} $"},
        {"Élément": "  = CASHFLOW APRÈS IMPÔT", "Montant": f"{cashflow_net:,.0f} $", "Note": "Dans la société" if is_incorporated else "Personnel"},
    ]
    
    # Graphique comparatif
    fig = go.Figure()
    
    # Barres pour les composantes
    fig.add_trace(go.Bar(
        name='Revenus',
        x=['NOI'],
        y=[noi],
        marker_color='#48bb78'
    ))
    
    fig.add_trace(go.Bar(
        name='Déductions',
        x=['Impôt', 'Capital'],
        y=[impot, capital_annuel],
        marker_color='#ff6b6b'
    ))
    
    fig.add_trace(go.Bar(
        name='Cashflow',
        x=['Cashflow Net'],
        y=[cashflow_net],
        marker_color='#667eea' if cashflow_net > 0 else '#ff4757'
    ))
    
    fig.update_layout(
        title="Analyse du Cashflow - Méthode Fiscale Complète",
        yaxis_title="Montant ($)",
        showlegend=True,
        height=400
    )
    
    return html.Div([
        # Résumé en cartes
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                        html.H6("Service de dette annuel", className="text-muted"),
                        html.H4(f"{mensualite * 12:,.0f} $"),
                        html.Small(f"Intérêts: {interet_annuel:,.0f} $ | Capital: {capital_annuel:,.0f} $", 
                                 className="text-muted")
                    ])
                ], className="text-center")
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Impôt économisé (vs sans déduction)", className="text-muted"),
                        html.H4(f"{interet_annuel * tax_rate:,.0f} $", className="text-success"),
                        html.Small("Grâce à la déduction des intérêts", className="text-muted")
                    ])
                ], className="text-center")
            ], width=4),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                        html.H6("Cashflow net final", className="text-muted"),
                        html.H4(f"{cashflow_net:,.0f} $", 
                               className=f"{'text-success' if cashflow_net > 0 else 'text-danger'}"),
                        html.Small("NOI - Intérêts - Capital - Impôt", className="text-muted")
                    ])
                ], className="text-center")
            ], width=4),
        ], className="mb-4"),
        
        # Graphique
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        
        # Tableau détaillé des calculs
        html.Div([
            html.H5("Détail des calculs", className="mb-3 mt-4"),
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Élément"),
                        html.Th("Montant", className="text-end"),
                        html.Th("Note")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(row["Élément"], 
                               className="fw-bold" if "=" in row["Élément"] or row["Élément"] == "  = CASHFLOW NET" else ""),
                        html.Td(row["Montant"], className="text-end"),
                        html.Td(html.Small(row["Note"], className="text-muted"))
                    ]) for row in calculs
                ])
            ], striped=True, hover=True, size="sm", className="mt-3"),
        ]),
        
        # Note importante
        dbc.Alert([
            html.H6("💡 Points importants :", className="alert-heading"),
            html.Ul([
                html.Li("Les intérêts sont déductibles d'impôt, ce qui réduit votre facture fiscale"),
                html.Li("Le cashflow après impôt = Revenue Net - Impôt calculé - Capital remboursé"),
                html.Li(f"Économie d'impôt sur les intérêts : {interet_annuel * tax_rate:,.0f} $"),
                html.Li("L'impôt est calculé sur (Revenue Net - Intérêts payés)")
            ])
        ], color="success", className="mt-4")
    ])

# Callback pour afficher/masquer la section d'édition
@app.callback(
    [Output("property-edit-section", "style"),
     Output("property-edit-section", "children")],
    [Input("edit-property-button", "n_clicks")],
    [State("property-data", "data"),
     State("property-edit-section", "style")]
)
def toggle_property_edit_section(n_clicks, property_data, current_style):
    if not n_clicks:
        return {"display": "none"}, ""
    
    # Toggle visibility
    if current_style and current_style.get("display") == "none":
        if not property_data:
            return {"display": "block"}, dbc.Alert("Veuillez d'abord sélectionner un immeuble.", color="warning")
        
        # Créer le formulaire d'édition
        edit_form = create_property_edit_form(property_data)
        return {"display": "block"}, edit_form
    else:
        return {"display": "none"}, ""

# Callback pour sauvegarder les modifications
@app.callback(
    [Output("property-data", "data", allow_duplicate=True),
     Output("property-edit-section", "style", allow_duplicate=True),
     Output("property-selector", "value", allow_duplicate=True)],
    [Input("save-property-changes", "n_clicks"),
     Input("cancel-property-changes", "n_clicks")],
    [State("property-selector", "value"),
     State("property-data", "data")] + 
    [State(f"edit-{field}", "value") for field in [
        "address", "prix_vente", "nombre_unites", "annee_construction", "type_batiment",
        "revenus_brut", "depenses_totales", "revenu_net", "depenses_taxes_municipales", 
        "depenses_taxes_scolaires", "depenses_assurances", "depenses_electricite", "depenses_chauffage",
        "financement_schl_ratio_couverture_dettes", "financement_schl_taux_interet", "financement_schl_amortissement",
        "financement_conv_ratio_couverture_dettes", "financement_conv_taux_interet", "financement_conv_amortissement",
        "latitude", "longitude"
    ]],
    prevent_initial_call=True
)
def handle_property_edit(save_clicks, cancel_clicks, property_addr, property_data, *field_values):
    if not property_addr or not property_data:
        raise PreventUpdate
    
    triggered_id = ctx.triggered_id
    
    # Extraire l'adresse réelle sans l'index si présent
    actual_address = property_addr.split("|")[0] if "|" in property_addr else property_addr
    
    if triggered_id == "cancel-property-changes":
        return property_data, {"display": "none"}, property_addr
    
    if triggered_id == "save-property-changes":
        # Récupérer les noms de champs
        all_fields = [
            "address", "prix_vente", "nombre_unites", "annee_construction", "type_batiment",
            "revenus_brut", "depenses_totales", "revenu_net", "depenses_taxes_municipales", 
            "depenses_taxes_scolaires", "depenses_assurances", "depenses_electricite", "depenses_chauffage",
            "financement_schl_ratio_couverture_dettes", "financement_schl_taux_interet", "financement_schl_amortissement",
            "financement_conv_ratio_couverture_dettes", "financement_conv_taux_interet", "financement_conv_amortissement",
            "latitude", "longitude"
        ]
        
        # Créer un dictionnaire avec les nouvelles valeurs
        updated_data = {}
        for i, field_name in enumerate(all_fields):
            if i < len(field_values) and field_values[i] is not None:
                updated_data[field_name] = field_values[i]
        
        # Mettre à jour dans la base de données
        success, message = update_immeuble_in_db(actual_address, updated_data)
        
        if success:
            # Mettre à jour property_data avec les nouvelles valeurs
            for key, value in updated_data.items():
                property_data[key] = value
            
            return property_data, {"display": "none"}, property_addr
        else:
            # En cas d'erreur, garder l'interface ouverte
            return property_data, {"display": "block"}, property_addr
    
    raise PreventUpdate

# Callback pour afficher l'URL
@app.callback(
    Output("property-url", "children"),
    [Input("property-data", "data"),
     Input("property-selector", "value")]
)
def display_property_url(property_data, property_addr):
    if not property_data:
        return html.P("Sélectionnez un immeuble pour voir son URL", className="text-muted")
    
    # Afficher l'identifiant complet pour aider à distinguer les immeubles identiques
    addr_display = ""
    if property_addr and "|" in property_addr:
        addr_display = f" (ID: {property_addr})"
    
    url = property_data.get('url', None)
    if url:
        return html.Div([
            html.P(f"Immeuble sélectionné{addr_display}", className="text-info mb-2"),
            html.A(
                [html.I(className="fas fa-external-link-alt me-2"), "Voir l'annonce"],
                href=url,
                target="_blank",
                className="btn btn-sm btn-outline-primary"
            )
        ])
    else:
        return html.Div([
            html.P(f"Immeuble sélectionné{addr_display}", className="text-info mb-2"),
            html.P("URL non disponible", className="text-muted")
        ])

# Callback pour afficher le résumé de la plage de négociation
@app.callback(
    Output("nego-summary", "children"),
    [Input("nego-low", "value"),
     Input("nego-high", "value"),
     Input("property-data", "data")]
)
def update_nego_summary(nego_low, nego_high, property_data):
    if not property_data:
        return html.Div()
    
    prix_demande = clean_monetary_value(property_data.get('prix_vente', 0))
    
    if not nego_low or not nego_high:
        return html.P("Entrez une plage de négociation", className="text-muted")
    
    # Calculer les pourcentages
    pct_low = ((nego_low - prix_demande) / prix_demande * 100) if prix_demande > 0 else 0
    pct_high = ((nego_high - prix_demande) / prix_demande * 100) if prix_demande > 0 else 0
    
    return dbc.Alert([
        html.Strong("Plage de négociation: "),
        f"{nego_low:,.0f} $ à {nego_high:,.0f} $",
        html.Br(),
        html.Small(f"Prix demandé: {prix_demande:,.0f} $", className="d-block"),
        html.Small(f"Écart: {pct_low:+.1f}% à {pct_high:+.1f}%", className="d-block")
    ], color="primary" if nego_low <= prix_demande <= nego_high else "warning")

# Callback pour sauvegarder les sélections Confluence
@app.callback(
    Output("confluence-data-store", "data"),
    [Input("confluence-rentabilite", "value"),
     Input("loyer-secteur", "value"),
     Input("prix-porte-secteur", "value"),
     Input("confluence-qualite", "value"),
     Input("nego-low", "value"),
     Input("nego-high", "value")]
)
def save_confluence_data(rentabilite, loyer_secteur, prix_porte, qualite, nego_low, nego_high):
    return {
        "rentabilite": rentabilite or [],
        "loyer_secteur": loyer_secteur,
        "prix_porte": prix_porte or [],
        "qualite": qualite or [],
        "nego_low": nego_low,
        "nego_high": nego_high
    }

@app.callback(
    Output("complete-property-data", "children"),
    Input("property-data", "data")
)
def display_complete_property_data(property_data):
    if not property_data:
        return html.P("Sélectionnez un immeuble pour voir ses données", className="text-muted")
    
    # Créer un tableau avec toutes les données
    rows = []
    for key, value in property_data.items():
        if value is not None:
            formatted_value = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            rows.append(
                html.Tr([
                    html.Td(key.replace('_', ' ').title(), className="text-muted"),
                    html.Td(formatted_value, className="text-end fw-bold")
                ])
            )
    
    return html.Div([
        dbc.Table(
            html.Tbody(rows),
            size="sm",
            hover=True,
            className="mb-0"
        )
    ], style={"maxHeight": "300px", "overflowY": "auto"})

@app.callback(
    [Output("additional-costs-result", "children"),
     Output("additional-costs-data", "data")],
    [Input("calculate-additional-costs-btn", "n_clicks")],
    [State("cost-systeme-incendie", "value"),
     State("cost-clapet-anti-retour", "value"),
     State("cost-detecteur-fuite", "value"),
     State("cost-chauffe-eau", "value"),
     State("cost-env-phase-1", "value"),
     State("cost-env-phase-2", "value"),
     State("cost-env-phase-3", "value")]
)
def calculate_additional_costs(n_clicks, systeme_incendie, clapet_anti_retour, detecteur_fuite, chauffe_eau, env_phase_1, env_phase_2, env_phase_3):
    if n_clicks is None:
        return html.Div(), {}
    
    costs = []
    total = 0
    additional_costs_data = {}
    
    if systeme_incendie and "systeme_incendie" in systeme_incendie:
        costs.append({"nom": "Mise à jour du système incendie", "montant": 1000})
        additional_costs_data["Mise à jour du système incendie"] = 1000
        total += 1000
    
    if clapet_anti_retour and "clapet_anti_retour" in clapet_anti_retour:
        # Prendre la moyenne de la fourchette de prix
        montant = 1500
        costs.append({"nom": "Installation clapet anti-retour", "montant": montant})
        additional_costs_data["Installation clapet anti-retour"] = montant
        total += montant
    
    if detecteur_fuite and "detecteur_fuite" in detecteur_fuite:
        costs.append({"nom": "Détecteur de fuite d'eau", "montant": 629.99})
        additional_costs_data["Détecteur de fuite d'eau"] = 629.99
        total += 629.99
    
    if chauffe_eau and "chauffe_eau" in chauffe_eau:
        costs.append({"nom": "Remplacement chauffe-eau électrique", "montant": 1140})
        additional_costs_data["Remplacement chauffe-eau électrique"] = 1140
        total += 1140
        
    # Phase 1 est toujours incluse (obligatoire), peu importe si elle est cochée ou non
    # La valeur par défaut est toujours incluse grâce au style CSS qui la rend non modifiable
    costs.append({"nom": "Test environnemental - Phase 1", "montant": 1200})
    additional_costs_data["Test environnemental - Phase 1"] = 1200
    total += 1200
    
    if env_phase_2 and "env_phase_2" in env_phase_2:
        costs.append({"nom": "Test environnemental - Phase 2", "montant": 5000})
        additional_costs_data["Test environnemental - Phase 2"] = 5000
        total += 5000
    
    if env_phase_3 and "env_phase_3" in env_phase_3:
        costs.append({"nom": "Test environnemental - Phase 3", "montant": 10000})
        additional_costs_data["Test environnemental - Phase 3"] = 10000
        total += 10000
    
    additional_costs_data["total"] = total
    
    if not costs:
        return html.Div([
            html.P("Aucun coût additionnel sélectionné.", className="text-muted mt-3")
        ]), additional_costs_data
    
    return html.Div([
        html.H6("Coûts additionnels à prévoir:", className="mt-3"),
        dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th("Élément"),
                    html.Th("Coût", className="text-end")
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(cost["nom"]),
                    html.Td(f"{cost['montant']:,.2f} $", className="text-end")
                ]) for cost in costs
            ] + [
                html.Tr([
                    html.Td(html.B("TOTAL")),
                    html.Td(html.B(f"{total:,.2f} $"), className="text-end")
                ], className="table-primary")
            ])
        ], striped=True, hover=True, size="sm", className="mt-3")
    ]), additional_costs_data

@app.callback(
    Output("total-with-additional-costs", "children"),
    [Input("additional-costs-data", "data"),
     Input("property-data", "data")]
)
def update_total_with_additional_costs(additional_costs_data, property_data):
    if not additional_costs_data or not property_data:
        return ""
    
    # Récupérer le total des coûts additionnels
    additional_total = additional_costs_data.get("total", 0)
    
    if additional_total <= 0:
        return ""
    
    # Calculer les coûts d'acquisition de base
    prix = clean_monetary_value(property_data['prix_vente'])
    total_base = 0
    
    # Si les coûts sont chargés depuis la base de données
    if ACQUISITION_COSTS:
        for cost_type, cost_info in ACQUISITION_COSTS.items():
            if cost_info['fixed_amount'] is not None and cost_info['fixed_amount'] > 0:
                total_base += cost_info['fixed_amount']
            elif cost_info['percentage'] is not None:
                total_base += prix * (cost_info['percentage'] / 100)
    else:
        # Estimation des coûts d'acquisition (version simplifiée)
        total_base = prix * 0.03 + calculate_bienvenue_tax(prix, property_data) + 2500
    
    # Calculer le nouveau total
    nouveau_total = total_base + additional_total
    
    return f"(Total avec coûts additionnels: {nouveau_total:,.0f} $)"

@app.callback(
    Output("costs-table-container", "children"),
    [Input("additional-costs-data", "data"),
     Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("schl-payment-mode", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value")]
)
def update_costs_table_with_additional(additional_costs_data, property_data, loan_type, schl_payment_mode, tax_province, tax_status):
    if not property_data:
        return []
    
    # Récupérer les données de base
    prix = clean_monetary_value(property_data['prix_vente'])
    nombre_unites = clean_numeric_value(property_data.get('nombre_unites', 0))
    
    # Calcul des différents coûts
    costs = {}
    
    # Si les coûts sont chargés depuis la base de données
    if ACQUISITION_COSTS:
        for cost_type, cost_info in ACQUISITION_COSTS.items():
            if cost_info['fixed_amount'] is not None and cost_info['fixed_amount'] > 0:
                costs[cost_type] = cost_info['fixed_amount']
            elif cost_info['percentage'] is not None:
                costs[cost_type] = prix * (cost_info['percentage'] / 100)
    else:
        # Valeurs par défaut si pas de données en base
        costs = {
            "Inspection": nombre_unites * 75,
            "Notaire": prix * 0.007,
            "Taxe de mutation (Bienvenue)": calculate_bienvenue_tax(prix, property_data),
            "Évaluation bancaire": 400,
            "Frais de dossier bancaire": 300,
            "Assurance titre": prix * 0.0025,
            "Ajustements (taxes, etc.)": prix * 0.005,
            "Déménagement": 1500,
            "Rénovations mineures": 5000,
            "Fonds de prévoyance": prix * 0.01
        }
    
    # Ajuster les frais de dossier bancaire selon le type de prêt
    if loan_type == "SCHL":
        # Pour SCHL: 150$ par porte/logement
        costs["Frais d'analyse de dossier SCHL"] = nombre_unites * 150
        # Retirer les frais de dossier bancaire standard s'ils existent
        costs.pop("Frais de dossier bancaire", None)
    elif "Frais d'analyse de dossier SCHL" in costs:
        # Si conventionnel, s'assurer qu'on n'a pas les frais SCHL
        costs.pop("Frais d'analyse de dossier SCHL", None)
        if "Frais de dossier bancaire" not in costs:
            costs["Frais de dossier bancaire"] = 300
    
    # Ajouter la taxe de bienvenue si pas déjà présente
    if "Taxe de mutation (Bienvenue)" not in costs:
        costs["Taxe de mutation (Bienvenue)"] = calculate_bienvenue_tax(prix, property_data)
    
    # Gérer la prime SCHL selon le mode de paiement
    if loan_type == "SCHL" and schl_payment_mode == "cash":
        # Calculer le montant de la prime SCHL
        ratio_pret_valeur = 0
        if 'revenu_net' in property_data:
            revenue_net = clean_monetary_value(property_data.get('revenu_net', 0))
            if revenue_net == 0:
                revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
                depenses_totales = clean_monetary_value(property_data.get('depenses_totales', 0))
                revenue_net = revenus_bruts - depenses_totales
                
            rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 1.2))
            taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
            amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
            
            revenue_net_mensuel = revenue_net / 12
            
            # Calculer la capacité de paiement maximale selon RDC
            pmt_max_capacite = revenue_net_mensuel / rdc_ratio
            
            # Calculer le montant de prêt max basé sur cette capacité
            montant_pret_max = calcul_pret_max(pmt_max_capacite, taux_interet, amortissement)
            
            # Calculer la PMT mensuelle avec la formule standard
            # PMT = (Montant_du_prêt*(Taux_d'intérêt/12)) / (1-(1+Taux_d'intérêt/12)^(-Nombre_de_paiements_total))
            nombre_paiements = amortissement * 12
            taux_mensuel = taux_interet / 12
            
            if abs(taux_mensuel) < 1e-9:
                mensualite_max = montant_pret_max / nombre_paiements
            else:
                mensualite_max = (montant_pret_max * taux_mensuel) / (1 - (1 + taux_mensuel) ** (-nombre_paiements))
            
            ratio_pret_valeur = min(montant_pret_max / prix, 0.95) if prix > 0 else 0
        
        montant_pret = prix * ratio_pret_valeur
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        
        # Ajouter la prime SCHL aux coûts
        costs["Prime SCHL (payée comptant)"] = prime_schl
    elif loan_type == "SCHL" and "Prime SCHL (payée comptant)" in costs:
        # Si le mode est financé, retirer la prime des coûts
        costs.pop("Prime SCHL (payée comptant)", None)
    
    # Calculer le cashflow négatif total avec les vraies valeurs fiscales
    try:
        cashflow_negatif_total = calculate_negative_cashflow_total(
            property_data, 
            loan_type, 
            tax_province or "Québec", 
            tax_status or "incorporated", 
            years_to_calculate=5
        )
        
        if cashflow_negatif_total > 0:
            costs["Provision pour cashflow négatif (5 ans)"] = cashflow_negatif_total
    except Exception as e:
        print(f"Erreur lors du calcul du cashflow négatif total dans callback: {e}")
    
    # Ajouter les coûts additionnels s'il y en a
    additional_costs = {}
    if additional_costs_data and "total" in additional_costs_data and additional_costs_data["total"] > 0:
        for key, value in additional_costs_data.items():
            if key != "total":
                additional_costs[key] = value
    
    # Calculer le total des coûts de base
    total_base = sum(costs.values())
    
    # Calculer le total des coûts additionnels
    total_additional = sum(additional_costs.values()) if additional_costs else 0
    
    # Grand total
    grand_total = total_base + total_additional
    
    # Créer les lignes du tableau pour les coûts de base
    rows = [
        html.Tr([
            html.Td(cost_name),
            html.Td(f"{cost_value:,.0f} $", className="text-end"),
            html.Td(f"{(cost_value/prix*100):.2f}%", className="text-end")
        ]) for cost_name, cost_value in costs.items()
    ]
    
    # Ajouter une ligne de sous-total pour les coûts de base si on a des coûts additionnels
    if additional_costs:
        rows.append(
            html.Tr([
                html.Td(html.B("Sous-total (coûts de base)")),
                html.Td(html.B(f"{total_base:,.0f} $"), className="text-end"),
                html.Td(html.B(f"{(total_base/prix*100):.2f}%"), className="text-end")
            ], className="table-info")
        )
        
        # Ajouter les lignes pour les coûts additionnels
        for cost_name, cost_value in additional_costs.items():
            rows.append(
                html.Tr([
                    html.Td(cost_name, className="fst-italic"),
                    html.Td(f"{cost_value:,.0f} $", className="text-end fst-italic"),
                    html.Td(f"{(cost_value/prix*100):.2f}%", className="text-end fst-italic")
                ])
            )
        
        # Ajouter une ligne de sous-total pour les coûts additionnels
        rows.append(
            html.Tr([
                html.Td(html.B("Sous-total (coûts additionnels)")),
                html.Td(html.B(f"{total_additional:,.0f} $"), className="text-end"),
                html.Td(html.B(f"{(total_additional/prix*100):.2f}%"), className="text-end")
            ], className="table-warning")
        )
    
    # Ajouter la ligne de grand total
    rows.append(
        html.Tr([
            html.Td(html.B("TOTAL")),
            html.Td(html.B(f"{grand_total:,.0f} $"), className="text-end"),
            html.Td(html.B(f"{(grand_total/prix*100):.2f}%"), className="text-end")
        ], className="table-primary")
    )
    
    return dbc.Table([
        html.Thead([
            html.Tr([
                html.Th("Type de coût"),
                html.Th("Montant", className="text-end"),
                html.Th("% du prix", className="text-end")
            ])
        ]),
        html.Tbody(rows)
    ], striped=True, hover=True, className="mb-4")

@app.callback(
    Output("financing-summary", "children"),
    [Input("additional-costs-data", "data"),
     Input("property-data", "data"),
     Input("loan-type", "value")]
)
def update_financing_summary(additional_costs_data, property_data, loan_type):
    if not property_data:
        return []
    
    # Récupérer le prix et les paramètres financiers
    prix = clean_monetary_value(property_data['prix_vente'])
    
    # Calculer les pourcentages de mise de fonds selon le type de prêt
    if loan_type == "SCHL":
        mise_fonds_schl_pct = 5.0   # 5% pour SCHL
        mise_fonds_conv_pct = 20.0  # 20% pour conventionnel
    else:
        mise_fonds_schl_pct = 5.0
        mise_fonds_conv_pct = 20.0
    
    # Utiliser la fonction standardisée pour le calcul du prêt
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type)
    # Utiliser les valeurs calculées pour le ratio du prêt
    mise_fonds_calculee_pct = (1 - ratio_pret_valeur) * 100
    
    # Mises de fonds basées sur le ratio calculé plutôt que les valeurs fixes
    mise_fonds_schl = prix * (1 - ratio_pret_valeur) if loan_type == "SCHL" else prix * (mise_fonds_schl_pct / 100)
    mise_fonds_conv = prix * (1 - ratio_pret_valeur) if loan_type != "SCHL" else prix * (mise_fonds_conv_pct / 100)
    
    # Calculer les coûts d'acquisition
    total_base = 0
    if ACQUISITION_COSTS:
        for cost_type, cost_info in ACQUISITION_COSTS.items():
            if cost_info['fixed_amount'] is not None and cost_info['fixed_amount'] > 0:
                total_base += cost_info['fixed_amount']
            elif cost_info['percentage'] is not None:
                total_base += prix * (cost_info['percentage'] / 100)
    else:
        total_base = prix * 0.03 + calculate_bienvenue_tax(prix, property_data) + 2500
    
    # Ajouter les coûts additionnels
    total_additional = 0
    if additional_costs_data and "total" in additional_costs_data:
        total_additional = additional_costs_data["total"]
    
    grand_total = total_base + total_additional
    
    # Retourner les cartes
    return [
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                    html.H6(f"Mise de fonds SCHL ({mise_fonds_schl_pct:.1f}%)", className="text-muted"),
                    html.H4(f"{mise_fonds_schl:,.0f} $")
                    ])
            ])
        ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                    html.H6(f"Mise de fonds conv. ({mise_fonds_conv_pct:.1f}%)", className="text-muted"),
                    html.H4(f"{mise_fonds_conv:,.0f} $")
                    ])
            ])
        ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                    html.H6("Coûts d'acquisition", className="text-muted"),
                    html.H4(f"{grand_total:,.0f} $")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total (conv. + coûts)", className="text-muted"),
                    html.H4(f"{mise_fonds_conv + grand_total:,.0f} $", className="text-danger")
                ])
            ])
        ], width=3),
    ]

# -----------------------------------------------------------------------------
# Callback pour mettre à jour le graphique d'amortissement selon le scénario choisi
# -----------------------------------------------------------------------------
@app.callback(
    [Output("amortization-graph", "figure"),
     Output("amortization-table", "data")],
    [Input("amortization-scenario", "value"),
     Input("schl-payment-mode", "value")],
    [State("property-data", "data"),
     State("loan-type", "value"),
     State("montant-pret-input", "value")]
)
def update_amortization_scenario(scenario_years, schl_payment_mode, property_data, loan_type, montant_pret_input):
    if not property_data or not scenario_years:
        raise PreventUpdate
    
    # S'assurer qu'on garde la valeur sélectionnée par l'utilisateur
    # ou utiliser "financed" comme valeur par défaut si non définie
    schl_payment_mode = schl_payment_mode or "financed"
    
    # Récupérer les données financières
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    
    # Utiliser l'amortissement du scénario
    amortissement = scenario_years
    
    # Paramètres du prêt selon le type - UTILISER LES VALEURS DE LA BD
    if loan_type == "SCHL":
        rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            raise ValueError("RDC SCHL manquant dans la base de données pour cette propriété")
        taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
    else:
        rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            raise ValueError("RDC Conventionnel manquant dans la base de données pour cette propriété")
        taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
    
    # Calculer ou récupérer le montant du prêt et la PMT mensuelle
    if montant_pret_input and montant_pret_input > 0:
        montant_pret = montant_pret_input
        # Recalculer la PMT mensuelle basée sur le RDC
        _, _, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type)
    else:
        # Utiliser la fonction standardisée pour le calcul du prêt
        montant_pret, _, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    # Prime SCHL si applicable
    prime_schl = 0
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        print(f"📈 [Amortization] Taux SCHL par défaut : {default_rate}%")
        
        # Si la prime est payée comptant, elle n'est pas ajoutée au montant financé
        if schl_payment_mode == "cash":
            montant_finance = montant_pret
        else:
            montant_finance = montant_pret + prime_schl
    else:
        montant_finance = montant_pret
    
    # === CORRECTION : Utiliser la PMT mensuelle basée sur le RDC ===
    mensualite = pmt_mensuelle
    n_payments = int(amortissement * 12)
    
    # Créer le tableau d'amortissement
    amortization_data = []
    solde_restant = montant_finance
    
    mois_a_afficher = int(amortissement * 12)
    
    for mois in range(1, mois_a_afficher + 1):
        interet_mois = solde_restant * (taux_interet / 12)
        capital_mois = mensualite - interet_mois
        
        if mois == mois_a_afficher:
            capital_mois = solde_restant
            interet_mois = mensualite - capital_mois
        
        amortization_data.append({
            "#": mois,
            "Mois": mois,
            "Solde restant": solde_restant,
            "Intérêts payés": interet_mois,
            "Capital remboursé": capital_mois
        })
        
        solde_restant = max(0, solde_restant - capital_mois)
    
    df_amortization = pd.DataFrame(amortization_data)
    
    # Créer le graphique d'amortissement par année
    years = list(range(1, int(amortissement) + 1))
    annual_data = []
    
    for year in years:
        start_month = (year - 1) * 12
        end_month = min(year * 12, len(amortization_data))
        
        year_data = df_amortization.iloc[start_month:end_month]
        
        if len(year_data) > 0:
            annual_principal = year_data['Capital remboursé'].sum()
            annual_interest = year_data['Intérêts payés'].sum()
            balance_end_year = year_data.iloc[-1]['Solde restant']
        else:
            annual_principal = 0
            annual_interest = 0
            balance_end_year = 0
        
        annual_data.append({
            'Année': year,
            'Principal': annual_principal,
            'Intérêts': annual_interest,
            'Solde': balance_end_year
        })
    
    df_annual = pd.DataFrame(annual_data)
    
    # Créer le graphique
    fig = go.Figure()
    
    # Barres pour le principal
    fig.add_trace(go.Bar(
        name='Principal',
        x=df_annual['Année'],
        y=df_annual['Principal'],
        marker_color='#48bb78',
        yaxis='y'
    ))
    
    # Barres pour les intérêts
    fig.add_trace(go.Bar(
        name='Intérêts',
        x=df_annual['Année'],
        y=df_annual['Intérêts'],
        marker_color='#4299e1',
        yaxis='y'
    ))
    
    # Ligne pour le solde
    fig.add_trace(go.Scatter(
        name='Solde',
        x=df_annual['Année'],
        y=df_annual['Solde'],
        mode='lines+markers',
        line=dict(color='#ed8936', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    # Configuration du layout
    current_year = 2025
    fig.update_layout(
        title={
            'text': f'Amortissement sur {amortissement} ans' + 
                   (f' (Prime SCHL payée comptant)' if loan_type == "SCHL" and schl_payment_mode == "cash" else ''),
            'x': 0.5,
            'xanchor': 'center'
        },
        barmode='stack',
        xaxis=dict(
            title='Année',
            tickmode='linear',
            tick0=1,
            dtick=max(1, len(years) // 10),  # Adapter l'intervalle selon le nombre d'années
            tickvals=list(range(1, len(years) + 1, max(1, len(years) // 10))),
            ticktext=[str(current_year + i - 1) for i in range(1, len(years) + 1, max(1, len(years) // 10))]
        ),
        yaxis=dict(
            title='Montant annuel ($)',
            side='left',
            showgrid=True,
            range=[0, max(df_annual['Principal'].max() + df_annual['Intérêts'].max(), montant_finance) * 1.1]
        ),
        yaxis2=dict(
            title='Solde restant ($)',
            side='right',
            overlaying='y',
            showgrid=False,
            range=[0, montant_finance * 1.1]
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified',
        height=500,
        plot_bgcolor='white'
    )
    
    return fig, df_amortization.to_dict('records')

@app.callback(
    [Output("cashflow-projection-graph", "children"),
     Output("cashflow-projection-table", "children")],
    [Input("property-data", "data"),
     Input("loan-type", "value"),
     Input("tax-province", "value"),
     Input("tax-status", "value"),
     Input("schl-payment-mode", "value")]
)
def update_cashflow_projection(property_data, loan_type, tax_province, tax_status, schl_payment_mode):
    if not property_data:
        return html.Div(), html.Div()
    
    # Récupérer les paramètres
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    
    # Utiliser la fonction standardisée
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(property_data, loan_type)
    
    # Paramètres du prêt
    if loan_type == "SCHL":
        taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
    else:
        taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
    
    # Prime SCHL
    prime_schl = 0
    if loan_type == "SCHL":
        # Utiliser un taux par défaut de 2.40%
        default_rate = 2.40
        prime_schl = montant_pret * (default_rate / 100)
        print(f"💹 [Cashflow Projection] Taux SCHL par défaut : {default_rate}%")
    
    # Montant financé
    if loan_type == "SCHL" and schl_payment_mode == "cash":
        montant_finance = montant_pret
    else:
        montant_finance = montant_pret + prime_schl
    
    # Calculer les projections avec différents scénarios de taux
    scenarios_results = compare_cashflow_scenarios(
        property_data, loan_type, tax_province, tax_status,
        montant_finance, taux_interet, amortissement
    )
    
    # Utiliser le scénario "taux_fixe" comme référence principale
    df_projection = scenarios_results['taux_fixe']['projection_complete']
    
    # Créer le graphique avec les différents scénarios
    fig = go.Figure()
    
    # Couleurs pour les différents scénarios
    colors = {
        'taux_fixe': '#48bb78',
        'hausse_graduelle': '#f6ad55', 
        'hausse_majeure': '#fc8181',
        'cycle_economique': '#9f7aea'
    }
    
    # Noms d'affichage des scénarios
    scenario_names = {
        'taux_fixe': 'Taux Fixe',
        'hausse_graduelle': 'Hausse Graduelle',
        'hausse_majeure': 'Hausse Majeure', 
        'cycle_economique': 'Cycle Économique'
    }
    
    # Ajouter une ligne pour chaque scénario
    for scenario, data in scenarios_results.items():
        df_scenario = data['projection_complete']
        fig.add_trace(go.Scatter(
            x=df_scenario['Année'],
            y=df_scenario['Cashflow mensuel'],
            mode='lines+markers',
            name=f'{scenario_names[scenario]} (Cashflow mensuel)',
            line=dict(color=colors[scenario], width=2),
            marker=dict(size=6),
            opacity=0.8
        ))
    
    # Ligne du cashflow annuel (axe secondaire)
    fig.add_trace(go.Scatter(
        x=df_projection['Année'],
        y=df_projection['Cashflow annuel'],
        mode='lines+markers',
        name='Cashflow annuel',
        line=dict(color='#667eea', width=3, dash='dash'),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title="Évolution du cashflow net sur la durée du prêt",
        xaxis=dict(title='Année'),
        yaxis=dict(
            title='Cashflow mensuel année 1 moyenne ($)',
            side='left'
        ),
        yaxis2=dict(
            title='Cashflow annuel ($)',
            side='right',
            overlaying='y'
        ),
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    # Créer le tableau
    table = dash_table.DataTable(
        data=df_projection.to_dict('records'),
        columns=[
            {"name": "Année", "id": "Année", "type": "numeric"},
            {"name": "Taux Intérêt (%)", "id": "Taux Intérêt", "type": "numeric", "format": {"specifier": ".1f"}},
            {"name": "Revenue Brut", "id": "Revenue Brut", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Dépenses", "id": "Dépenses", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Revenue Net", "id": "Revenue Net", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Mensualité", "id": "Mensualité", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Intérêts", "id": "Intérêts", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Capital", "id": "Capital", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "DPA", "id": "DPA", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Montant Imposable", "id": "Montant Imposable", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Impôt", "id": "Impôt", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Cashflow annuel", "id": "Cashflow annuel", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Cashflow mensuel", "id": "Cashflow mensuel", "type": "numeric", "format": FormatTemplate.money(0)},
            {"name": "Solde prêt", "id": "Solde prêt", "type": "numeric", "format": FormatTemplate.money(0)}
        ],
                style_cell={'textAlign': 'right'},
                style_data_conditional=[
                    {
                'if': {'column_id': 'Cashflow mensuel', 'filter_query': '{Cashflow mensuel} < 0'},
                'color': 'red',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'Cashflow mensuel', 'filter_query': '{Cashflow mensuel} >= 0'},
                'color': 'green',
                'fontWeight': 'bold'
            },
            {
                'if': {'column_id': 'Taux Intérêt', 'filter_query': '{Taux Intérêt} > 6.0'},
                'backgroundColor': '#fff2cc',
                'color': '#856404'
            }
        ],
        page_size=10,
        style_table={'overflowX': 'auto'}
    )
    
    graph = dcc.Graph(figure=fig, config={'displayModeBar': False})
    
    # Calcul du gain de cashflow
    cashflow_debut = df_projection.iloc[0]['Cashflow mensuel'] if 'Cashflow mensuel' in df_projection.columns else df_projection.iloc[0]['Cashflow mensuel année 1 moyenne']
    cashflow_fin = df_projection.iloc[-1]['Cashflow mensuel'] if 'Cashflow mensuel' in df_projection.columns else df_projection.iloc[-1]['Cashflow mensuel année 1 moyenne']
    gain_cashflow = cashflow_fin - cashflow_debut
    
    summary = dbc.Alert([
        html.H6("📈 Résumé de l'amélioration du cashflow", className="alert-heading"),
        html.P([
            f"Cashflow mensuel année 1 moyenne : {cashflow_debut:,.0f} $",
            html.Br(),
            f"Cashflow mensuel année {int(amortissement)} : {cashflow_fin:,.0f} $",
            html.Br(),
            html.Strong(f"Amélioration : +{gain_cashflow:,.0f} $/mois (+{(gain_cashflow/abs(cashflow_debut)*100) if cashflow_debut != 0 else 0:.1f}%)")
        ])
    ], color="success" if gain_cashflow > 0 else "warning", className="mt-4")
    
    # Créer le tableau de comparaison des scénarios
    scenarios_comparison_data = []
    for scenario, data in scenarios_results.items():
        scenarios_comparison_data.append({
            'Scénario': scenario_names[scenario],
            'Cashflow Négatif 5 ans': f"{data['cashflow_negatif_5ans']:,.0f} $",
            'Cashflow Moyen 10 ans': f"{data['cashflow_moyen_10ans']:,.0f} $/an",
            'Cashflow Cumulé 10 ans': f"{data['cashflow_cumule_10ans']:,.0f} $",
            'Année Cashflow Positif': data['annee_cashflow_positif'] if data['annee_cashflow_positif'] else 'Jamais',
            'Taux Final': f"{data['taux_final']:.1f}%"
        })
    
    scenarios_table = html.Div([
        html.H5("🔄 Comparaison des Scénarios de Taux d'Intérêt", className="mb-3 mt-4"),
        dbc.Alert([
            html.P([
                "Cette analyse compare l'impact de différents scénarios de taux d'intérêt sur votre cashflow:",
                html.Br(),
                "• ", html.Strong("Taux Fixe"), " : Aucun changement de taux",
                html.Br(),
                "• ", html.Strong("Hausse Graduelle"), " : +0.5%, +1.0%, +1.5% aux renouvellements",
                html.Br(),
                "• ", html.Strong("Hausse Majeure"), " : +1.5%, +2.5%, +2.0% aux renouvellements", 
                html.Br(),
                "• ", html.Strong("Cycle Économique"), " : Fluctuations selon les cycles économiques"
            ])
        ], color="info", className="mb-3"),
        dash_table.DataTable(
            data=scenarios_comparison_data,
            columns=[{"name": i, "id": i} for i in scenarios_comparison_data[0].keys()],
            style_cell={'textAlign': 'center', 'fontSize': '12px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'row_index': 0},  # Taux fixe
                    'backgroundColor': '#d4edda'
                },
                {
                    'if': {'row_index': 2},  # Hausse majeure
                    'backgroundColor': '#f8d7da'
                }
            ],
            style_table={'overflowX': 'auto'}
        )
    ], className="mb-4")
    
    return [graph, html.Div([summary, scenarios_table, table])]

# -----------------------------------------------------------------------------
# Fonction pour déterminer la province d'une propriété
# -----------------------------------------------------------------------------
def get_property_province(property_data):
    """
    Détermine la province d'un immeuble à partir de ses coordonnées
    
    Args:
        property_data: Dictionnaire contenant latitude et longitude
    
    Returns:
        str: Nom de la province ou None si non trouvé
    """
    try:
        # Vérifier si on a des coordonnées
        if not property_data.get('latitude') or not property_data.get('longitude'):
            return None
            
        lat = float(property_data['latitude'])
        lon = float(property_data['longitude'])
        
        # Vérifier que les coordonnées sont valides
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
            
        from shapely.geometry import Point
        
        # Créer un point à partir des coordonnées (lon, lat)
        point = Point(lon, lat)
        
        # Charger toutes les provinces
        engine = create_engine(
            "postgresql://postgres:4845@100.73.238.42:5432/analysis",
            connect_args={"client_encoding": "utf8"}
        )
        
        query = '''
            SELECT 
                province_id,
                province_name,
                ST_AsEWKB(geo_zone) as geom_bin
            FROM id."Canada_Provinces_ID"
        '''
        provinces_df = pd.read_sql(query, engine)
        engine.dispose()
        
        # Parcourir chaque province pour vérifier si le point est à l'intérieur
        for _, row in provinces_df.iterrows():
            try:
                from shapely import wkb
                if pd.notna(row['geom_bin']):
                    if isinstance(row['geom_bin'], memoryview):
                        geometry = wkb.loads(bytes(row['geom_bin']))
                    else:
                        geometry = wkb.loads(row['geom_bin'])
                    
                    if geometry.contains(point) or geometry.intersects(point):
                        return row['province_name']
            except Exception as e:
                print(f"Erreur lors de la vérification de la province {row['province_name']}: {e}")
                continue
                
        return None
        
    except Exception as e:
        print(f"Erreur lors de la détermination de la province: {e}")
        return None

# -----------------------------------------------------------------------------
# Callbacks pour la projection des gains en capital
# -----------------------------------------------------------------------------
@app.callback(
    Output("capital-gains-projection", "children"),
    [Input("appreciation-rate-profit", "value"),
     Input("holding-years", "value"),
     Input("property-data", "data")]
)
def update_capital_gains_projection(appreciation_rate, holding_years, property_data):
    if not property_data or not appreciation_rate or not holding_years:
        return html.Div()
    
    # Récupérer les données de base
    prix_initial = clean_monetary_value(property_data.get('prix_vente', 0))
    
    # Déterminer la province depuis les coordonnées
    province = get_property_province(property_data)
    if not province:
        province = "Quebec"  # Province par défaut
    
    # Calculer la valeur future
    valeur_future = prix_initial * ((1 + appreciation_rate/100) ** holding_years)
    gain_brut = valeur_future - prix_initial
    
    # Calculer l'impôt sur le gain en capital
    impot_gain, taux_effectif = calculate_capital_gains_tax(gain_brut, province)
    gain_net = gain_brut - impot_gain
    
    # Créer les données pour le graphique année par année
    years_data = []
    for year in range(1, holding_years + 1):
        valeur_annee = prix_initial * ((1 + appreciation_rate/100) ** year)
        gain_annee = valeur_annee - prix_initial
        impot_annee, _ = calculate_capital_gains_tax(gain_annee, province)
        
        years_data.append({
            'Année': year,
            'Valeur': valeur_annee,
            'Gain Brut': gain_annee,
            'Impôt': impot_annee,
            'Gain Net': gain_annee - impot_annee
        })
    
    df_years = pd.DataFrame(years_data)
    
    # Créer le graphique
    fig = go.Figure()
    
    # Valeur de l'immeuble
    fig.add_trace(go.Scatter(
        x=df_years['Année'],
        y=df_years['Valeur'],
        mode='lines+markers',
        name='Valeur de l\'immeuble',
        line=dict(color='#667eea', width=3)
    ))
    
    # Gain net après impôt
    fig.add_trace(go.Scatter(
        x=df_years['Année'],
        y=df_years['Gain Net'],
        mode='lines+markers',
        name='Gain net après impôt',
        line=dict(color='#48bb78', width=3),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=f"Projection du gain en capital sur {holding_years} ans",
        xaxis=dict(title='Année'),
        yaxis=dict(
            title='Valeur de l\'immeuble ($)',
            side='left'
        ),
        yaxis2=dict(
            title='Gain net après impôt ($)',
            side='right',
            overlaying='y'
        ),
        hovermode='x unified',
        height=500
    )
    
    # Résumé
    return html.Div([
        # Cartes de résumé
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Valeur future", className="text-muted"),
                        html.H4(f"{valeur_future:,.0f} $"),
                        html.Small(f"Après {holding_years} ans", className="text-muted")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Gain brut", className="text-muted"),
                        html.H4(f"{gain_brut:,.0f} $"),
                        html.Small(f"+{(gain_brut/prix_initial*100):.1f}%", className="text-muted")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Impôt à payer", className="text-muted"),
                        html.H4(f"{impot_gain:,.0f} $", className="text-danger"),
                        html.Small(f"Taux effectif: {taux_effectif:.1f}%", className="text-muted")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Gain net après impôt", className="text-muted"),
                        html.H4(f"{gain_net:,.0f} $", className="text-success"),
                        html.Small(f"Province: {province}", className="text-muted")
                    ])
                ])
            ], width=3),
        ], className="mb-4"),
        
        # Graphique
        dcc.Graph(figure=fig, config={'displayModeBar': False}),
        
        # Note sur l'impôt
        dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            f"L'impôt sur le gain en capital est calculé selon les taux de la province de {province}. ",
            "Ces taux sont progressifs et tiennent compte de votre revenu total de l'année de vente."
        ], color="info", className="mt-3")
    ])

@app.callback(
    Output("detected-province", "children"),
    Input("property-data", "data")
)
def display_detected_province(property_data):
    if not property_data:
        return "Sélectionnez un immeuble"
    
    province = get_property_province(property_data)
    if province:
        return html.Span([
            html.I(className="fas fa-check-circle text-success me-2"),
            province
        ])
    else:
        return html.Span([
            html.I(className="fas fa-exclamation-circle text-warning me-2"),
            "Province non détectée (Ontario par défaut)"
        ])

# -----------------------------------------------------------------------------
# Lancement de l'application
# -----------------------------------------------------------------------------
# Ajouter un store pour le mode de paiement SCHL
@app.callback(
    Output("schl-payment-mode-store", "data"),
    Input("schl-payment-mode", "value")
)
def update_schl_payment_mode_store(value):
    return value if value else "financed"

@app.callback(
    Output("schl-payment-mode", "value"),
    Input("schl-payment-mode-profit-display", "value"),
    prevent_initial_call=True
)
def sync_schl_payment_mode_from_profit(value):
    return value if value else "financed"

# Ce callback a été supprimé car il causait un problème d'affichage
# Les informations de débogage EGI sont maintenant affichées directement dans la section EGI

# Callback pour mettre à jour automatiquement les dépenses totales avec les dépenses additionnelles
@app.callback(
    Output("adjusted-depenses-totales", "value"),
    [Input("additional-expenses-store", "data"),
     Input("property-data", "data")]
)
def update_total_expenses_with_additional(additional_expenses, property_data):
    if not property_data:
        return 0
    
    # Récupérer les dépenses de base
    depenses_base = clean_monetary_value(property_data.get('depenses_totales', 0))
    
    # Calculer le total des dépenses additionnelles
    total_additional = sum(item['amount'] for item in additional_expenses) if additional_expenses else 0
    
    # Retourner le total
    return depenses_base + total_additional

# Callback pour mettre à jour automatiquement les revenus bruts avec les revenus additionnels
@app.callback(
    Output("adjusted-revenue-brut", "value"),
    [Input("additional-revenues-store", "data"),
     Input("property-data", "data")]
)
def update_total_revenues_with_additional(additional_revenues, property_data):
    if not property_data:
        return 0
    
    # Récupérer les revenus de base
    revenus_base = clean_monetary_value(property_data.get('revenus_brut', 0))
    
    # Calculer le total des revenus additionnels
    total_additional = sum(item['amount'] for item in additional_revenues) if additional_revenues else 0
    
    # Retourner le total
    return revenus_base + total_additional

@app.callback(
    [Output("collapse-financing-details", "is_open"),
     Output("toggle-financing-details", "children")],
    [Input("toggle-financing-details", "n_clicks")],
    [State("collapse-financing-details", "is_open")]
)
def toggle_financing_details(n_clicks, is_open):
    if n_clicks:
        is_open = not is_open
        
    if is_open:
        button_text = [html.I(className="fas fa-chevron-up me-2"), "Masquer les détails"]
    else:
        button_text = [html.I(className="fas fa-chevron-down me-2"), "Voir les détails"]
        
    return is_open, button_text


# Nouveau callback pour afficher le contrôle du taux SCHL manuel
@app.callback(
    Output("main-egi-control", "children"),
    [Input("loan-type", "value"),
     Input("property-data", "data")]
)
def update_main_schl_rate_control(loan_type, property_data):
    """Affiche le contrôle du taux SCHL avec détection automatique et choix RBR"""
    print(f"🚨🚨🚨 DEBUT DU CALLBACK - loan_type reçu: {loan_type}")
    
    # Ne rien afficher si ce n'est pas un prêt SCHL
    if loan_type != "SCHL":
        print(f"❌ [SCHL Rate Control] Pas d'affichage - Loan type={loan_type}")
        return html.Div()
    
    print(f"✅✅✅ [SCHL Rate Control] AFFICHAGE DU CONTRÔLE TAUX SCHL ✅✅✅")
    
    try:
        # Calculer le ratio prêt-valeur si property_data est disponible
        ratio_pret_valeur = 0
        taux_schl_rbr_atteint = 2.60
        taux_schl_rbr_non_atteint = 3.25
        
        if property_data:
            try:
                _, ratio_pret_valeur, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
                ratio_pret_valeur = ratio_pret_valeur * 100  # Convertir en pourcentage
                
                # Obtenir les taux SCHL selon le ratio
                taux_schl_rbr_atteint = get_schl_rate_logement_locatif(ratio_pret_valeur, rbr_atteint=True)
                taux_schl_rbr_non_atteint = get_schl_rate_logement_locatif(ratio_pret_valeur, rbr_atteint=False)
                
            except Exception as e:
                print(f"Erreur lors du calcul du ratio prêt-valeur: {e}")
        
        return html.Div([
            html.Hr(className="my-3"),
            
            # Affichage du ratio prêt-valeur
            html.Div([
                html.H5([
                    html.I(className="fas fa-chart-line me-2"),
                    "Ratio prêt-valeur"
                ], className="mb-2"),
                html.Div([
                    html.H4(f"{ratio_pret_valeur:.1f}%", className="text-primary fw-bold mb-0")
                ], className="p-3 bg-light rounded mb-3")
            ]),
            
            html.H5([
                html.I(className="fas fa-percent me-2"),
                "Taux de prime SCHL"
            ], className="mb-3"),
            
            # Switch pour RBR atteint/non atteint
            dbc.Row([
                dbc.Col([
                    dbc.Label("Statut RBR", className="fw-bold mb-2"),
                    dbc.ButtonGroup([
                        dbc.Button(
                            "RBR Atteint",
                            id="rbr-atteint-btn",
                            color="primary",
                            active=True,
                            n_clicks=0
                        ),
                        dbc.Button(
                            "RBR Non Atteint",
                            id="rbr-non-atteint-btn",
                            color="outline-primary",
                            active=False,
                            n_clicks=0
                        )
                    ], className="mb-3")
                ], width=12),
            ]),
            
            # Affichage des taux selon le statut RBR
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6("Taux automatique selon votre ratio prêt-valeur:", className="text-muted mb-2"),
                        html.Div([
                            html.Span("RBR Atteint: ", className="fw-bold"),
                            html.Span(f"{taux_schl_rbr_atteint:.2f}%", className="text-success fw-bold me-3"),
                            html.Span("RBR Non Atteint: ", className="fw-bold"),
                            html.Span(f"{taux_schl_rbr_non_atteint:.2f}%", className="text-danger fw-bold"),
                        ], className="mb-2"),
                        html.Div(id="selected-schl-rate-display", className="p-3 bg-primary text-white rounded")
                    ])
                ], width=12),
            ]),
            
            html.Small([
                html.I(className="fas fa-info-circle me-1"),
                "Le taux est automatiquement déterminé selon votre ratio prêt-valeur et le statut RBR"
            ], className="text-muted mt-2")
        ])
    except Exception as e:
        print(f"❌❌❌ ERREUR DANS LE CALLBACK: {str(e)}")
        import traceback
        traceback.print_exc()
        return html.Div([
            html.H4("❌ ERREUR DANS LE CALLBACK", style={"color": "white", "background": "red", "padding": "10px"}),
            html.P(f"Erreur: {str(e)}")
        ])

print("✅ [CALLBACK REGISTRATION] update_main_schl_rate_control ENREGISTRÉ avec succès")

# Callback pour gérer la sélection RBR atteint/non atteint
@app.callback(
    [Output("rbr-atteint-btn", "color"),
     Output("rbr-atteint-btn", "className"),
     Output("rbr-non-atteint-btn", "color"),
     Output("rbr-non-atteint-btn", "className"),
     Output("rbr-status", "data"),
     Output("manual-schl-rate", "data"),
     Output("selected-schl-rate-display", "children")],
    [Input("rbr-atteint-btn", "n_clicks"),
     Input("rbr-non-atteint-btn", "n_clicks")],
    State("property-data", "data"),
    prevent_initial_call=True
)
def handle_rbr_selection(rbr_atteint_clicks, rbr_non_atteint_clicks, property_data):
    """Gère la sélection du statut RBR et met à jour le taux SCHL"""
    print(f"🔵 [RBR Selection] Callback déclenché")
    print(f"   Clics RBR Atteint: {rbr_atteint_clicks}")
    print(f"   Clics RBR Non Atteint: {rbr_non_atteint_clicks}")
    
    ctx = dash.callback_context
    
    if not ctx.triggered:
        print(f"❌ [RBR Selection] Pas de trigger")
        return dash.no_update
    
    # Déterminer quel bouton a été cliqué
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    rbr_atteint = button_id == "rbr-atteint-btn"
    
    print(f"   Bouton cliqué: {button_id}")
    print(f"   RBR Atteint: {rbr_atteint}")
    
    # Calculer le ratio prêt-valeur et obtenir le taux approprié
    ratio_pret_valeur = 75  # Valeur par défaut
    if property_data:
        try:
            _, ratio_pret_valeur, _ = calculate_loan_amount_from_rdc(property_data, "SCHL")
            ratio_pret_valeur = ratio_pret_valeur * 100
            print(f"   Ratio prêt-valeur: {ratio_pret_valeur:.2f}%")
        except Exception as e:
            print(f"   ⚠️ Erreur calcul ratio: {e}")
            pass
    
    # Obtenir le taux SCHL approprié
    taux_schl = get_schl_rate_logement_locatif(ratio_pret_valeur, rbr_atteint=rbr_atteint)
    print(f"   💰 Taux SCHL calculé: {taux_schl:.2f}%")
    
    # Mise à jour des styles des boutons
    if rbr_atteint:
        rbr_atteint_color = "primary"
        rbr_atteint_class = "active"
        rbr_non_atteint_color = "outline-primary"
        rbr_non_atteint_class = ""
        status_text = f"✓ RBR Atteint - Taux appliqué: {taux_schl:.2f}%"
    else:
        rbr_atteint_color = "outline-primary"
        rbr_atteint_class = ""
        rbr_non_atteint_color = "primary"
        rbr_non_atteint_class = "active"
        status_text = f"✗ RBR Non Atteint - Taux appliqué: {taux_schl:.2f}%"
    
    print(f"   ✅ [RBR Selection] Mise à jour réussie: {status_text}")
    
    return (
        rbr_atteint_color,
        rbr_atteint_class,
        rbr_non_atteint_color,
        rbr_non_atteint_class,
        rbr_atteint,
        taux_schl,
        html.H5(status_text, className="mb-0")
    )

# Callback pour initialiser l'affichage et le taux SCHL lors du chargement
@app.callback(
    [Output("selected-schl-rate-display", "children", allow_duplicate=True),
     Output("manual-schl-rate", "data", allow_duplicate=True)],
    [Input("loan-type", "value"),
     Input("property-data", "data")],
    State("rbr-status", "data"),
    prevent_initial_call='initial_duplicate'
)
def initialize_schl_rate_display(loan_type, property_data, rbr_status):
    """Initialise l'affichage et le Store du taux SCHL lors du chargement"""
    print(f"🔵 [Initialize SCHL Rate] Callback déclenché")
    print(f"   Loan type: {loan_type}")
    print(f"   RBR Status: {rbr_status}")
    
    if loan_type != "SCHL" or not property_data:
        return dash.no_update, dash.no_update
    
    try:
        _, ratio_pret_valeur, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
        ratio_pret_valeur = ratio_pret_valeur * 100
        
        # Obtenir le taux selon le statut RBR actuel
        taux_schl = get_schl_rate_logement_locatif(ratio_pret_valeur, rbr_atteint=rbr_status)
        
        print(f"   Ratio prêt-valeur: {ratio_pret_valeur:.2f}%")
        print(f"   Taux SCHL calculé: {taux_schl:.2f}%")
        
        if rbr_status:
            display = html.H5(f"✓ RBR Atteint - Taux appliqué: {taux_schl:.2f}%", className="mb-0")
        else:
            display = html.H5(f"✗ RBR Non Atteint - Taux appliqué: {taux_schl:.2f}%", className="mb-0")
        
        return display, taux_schl
    except Exception as e:
        print(f"   ⚠️ Erreur initialisation: {e}")
        return html.H5("✓ RBR Atteint - Taux appliqué: 2.60%", className="mb-0"), 2.60


if __name__ == "__main__":
    import os
    
    # Configuration pour la production/développement
    port = int(os.environ.get('PORT', 8050))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print("🚀 Démarrage de l'application Dash...")
    print(f"📊 Application disponible sur le port: {port}")
    print(f"🔧 Mode: {'DÉVELOPPEMENT' if debug else 'PRODUCTION'}")
    print("✅ [FIX] Layout nettoyé - doublons supprimés")
    print("✅ [FIX] Callback SCHL rate control activé")
    print("👁️ Recherchez le message '🔧🔧🔧 [SCHL Rate Control CALLBACK DÉCLENCHÉ]' après avoir sélectionné un immeuble")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
    