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

from functions.clean import (
    clean_monetary_value, clean_percentage_value, clean_numeric_value, safe_float_conversion
)

from functions.calculation import (
    calculate_schl_premium, calculate_loan_amount_from_rdc
)

def update_loan_amount(loan_type, property_data):
    if not property_data:
        return None
    
    # Utiliser la fonction standardisée pour le calcul du prêt
    try:
        montant_pret, _, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    except Exception as e:
        print(f"Erreur dans update_loan_amount: {e}")
        # En cas d'erreur, utiliser une valeur par défaut pour le prêt
        prix = clean_monetary_value(property_data.get('prix_vente', 0))
        montant_pret = prix * 0.75  # 75% de la valeur de l'immeuble par défaut
    
    return montant_pret

def update_schl_payment_info(payment_mode, property_data, loan_type):
    if not property_data or loan_type != "SCHL":
        return html.Div()
    
    # Calculer la prime SCHL avec taux par défaut
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    montant_pret, _, _ = calculate_loan_amount_from_rdc(property_data, loan_type)
    # Utiliser un taux par défaut de 2.40%
    default_rate = 2.40
    prime_schl = montant_pret * (default_rate / 100)
    prime_rate = default_rate
    
    if payment_mode == "cash":
        return dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            f"Prime SCHL de {prime_schl:,.0f} $ sera payée comptant chez le notaire. ",
            html.Strong("Le montant financé sera donc de "),
            f"{montant_pret:,.0f} $ (sans la prime)."
        ], color="info", className="mb-0")
    else:
        return dbc.Alert([
            html.I(className="fas fa-info-circle me-2"),
            f"Prime SCHL de {prime_schl:,.0f} $ sera ajoutée au prêt. ",
            html.Strong("Le montant total financé sera de "),
            f"{montant_pret + prime_schl:,.0f} $."
        ], color="warning", className="mb-0")

def update_schl_section(loan_type, montant_pret, property_data):
    if loan_type != "SCHL" or not property_data:
        return html.Div()
    
    montant_pret = montant_pret or 0
    valeur_immeuble = clean_monetary_value(property_data.get('prix_vente', 0))
    
    if valeur_immeuble == 0:
        return html.Div()
    
    # Utiliser un taux par défaut de 2.40%
    default_rate = 2.40
    prime_schl = montant_pret * (default_rate / 100)
    prime_rate = default_rate
    ltv = (montant_pret / valeur_immeuble * 100) if valeur_immeuble > 0 else 0
    
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

def sync_schl_payment_mode_from_profit(value):
    if value:
        return value
    raise PreventUpdate
