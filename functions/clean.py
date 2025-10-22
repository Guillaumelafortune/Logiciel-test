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



def safe_float_conversion(value, default=0, remove_chars=None):
    """
    Convertit une valeur en float de manière sécurisée
    
    Args:
        value: La valeur à convertir
        default: Valeur par défaut si la conversion échoue
        remove_chars: Liste de caractères à supprimer avant conversion
    
    Returns:
        float: La valeur convertie ou la valeur par défaut
    """
    if value is None:
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Supprimer les caractères spécifiés
        if remove_chars is None:
            remove_chars = ['$', ' ', ',']
        
        cleaned = value
        for char in remove_chars:
            cleaned = cleaned.replace(char, '')
        
        # Remplacer la virgule décimale française par un point
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            # Essayer d'extraire les nombres avec regex
            import re
            numbers = re.findall(r'[\d.]+', cleaned)
            if numbers:
                try:
                    return float(numbers[0])
                except ValueError:
                    return default
            return default
    
    return default


def clean_monetary_value(value):
    """Convertit une valeur monétaire en string vers un float"""
    if value is None or value == '':
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    # Nettoyer la string : enlever $, espaces, virgules
    clean_value = str(value).replace('$', '').replace(' ', '').replace(',', '').strip()
    try:
        return float(clean_value)
    except ValueError:
        return 0
    
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

def clean_numeric_value(value):
    """Convertit une valeur numérique en string vers un float - Version améliorée"""
    if value is None or value == '':
        return 0
    if isinstance(value, (int, float)):
        return float(value)
    
    # Nettoyer et extraire les nombres
    clean_value = str(value).replace(' ', '').replace(',', '.').replace('%', '').strip()
    
    # Gérer les cas spéciaux (texte descriptif)
    if clean_value.lower() in ['none', 'null', 'n/a', 'na', '']:
        return 0
    
    # Extraire seulement les chiffres et le point décimal
    import re
    numbers = re.findall(r'\d+\.?\d*', clean_value)
    if numbers:
        try:
            return float(numbers[0])
        except ValueError:
            return 0
    
    return 0
