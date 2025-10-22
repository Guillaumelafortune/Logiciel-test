"""
Module de calculs pour l'application de simulation immobilière
Contient toutes les fonctions de calcul déplacées depuis main2.py
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from shapely.geometry import Point
from shapely import wkb, wkt
import re


# Import des fonctions de chargement de données
from filter.data_loading import (
    load_tax_rates_particulier, load_tax_rates_entreprise,
    load_taxation_municipale, load_schl_rates, load_taxe_bienvenue,
    clean_percentage_value
)

from functions.clean import (
    clean_monetary_value, clean_percentage_value, clean_numeric_value, safe_float_conversion
)

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

def get_schl_rate_logement_locatif(ltv_ratio, rbr_atteint=True):
    """
    Détermine le taux de prime SCHL pour les logements locatifs ordinaires
    selon le ratio prêt-valeur et le statut RBR
    
    Args:
        ltv_ratio: Ratio prêt-valeur en pourcentage (ex: 75 pour 75%)
        rbr_atteint: True si le RBR est atteint, False sinon
    
    Returns:
        float: Taux de prime SCHL en pourcentage
    """
    # Tableau des taux selon l'image fournie
    taux_schl = {
        65: {"rbr_atteint": 2.60, "rbr_non_atteint": 3.25},
        70: {"rbr_atteint": 2.85, "rbr_non_atteint": 3.75},
        75: {"rbr_atteint": 3.35, "rbr_non_atteint": 4.25},
        80: {"rbr_atteint": 4.35, "rbr_non_atteint": 5.00},
        85: {"rbr_atteint": 5.35, "rbr_non_atteint": 6.00}
    }
    
    # Déterminer la tranche du ratio prêt-valeur
    if ltv_ratio <= 65:
        tranche = 65
    elif ltv_ratio <= 70:
        tranche = 70
    elif ltv_ratio <= 75:
        tranche = 75
    elif ltv_ratio <= 80:
        tranche = 80
    elif ltv_ratio <= 85:
        tranche = 85
    else:
        # Si le ratio est supérieur à 85%, retourner le taux maximum
        tranche = 85
    
    # Retourner le taux approprié
    if rbr_atteint:
        return taux_schl[tranche]["rbr_atteint"]
    else:
        return taux_schl[tranche]["rbr_non_atteint"]

def calculate_schl_premium(montant_pret, valeur_immeuble, property_data=None, use_egi_met=True):
    """
    Calcule la prime SCHL en fonction du montant du prêt, de la valeur de l'immeuble,
    du nombre d'unités et du critère EGI
    
    Args:
        montant_pret: Montant du prêt
        valeur_immeuble: Valeur de l'immeuble
        property_data: Données de la propriété (pour récupérer le nombre d'unités)
        use_egi_met: True pour utiliser le taux EGI met, False pour EGI not met (pour 6+ unités)
    
    Returns:
        tuple: (prime_schl, prime_rate)
    """
    # Éviter d'afficher les logs si les données ne sont pas complètes
    if property_data is None or montant_pret == 0 or valeur_immeuble == 0:
        return 0, 0
        
    print(f"\n=== CALCULATE_SCHL_PREMIUM ===")
    print(f"Montant prêt: {montant_pret:,.0f} $")
    print(f"Valeur immeuble: {valeur_immeuble:,.0f} $")
    print(f"Use EGI MET: {use_egi_met}")
    
    # S'assurer que les valeurs sont des nombres
    montant_pret = safe_float_conversion(montant_pret, 0)
    valeur_immeuble = safe_float_conversion(valeur_immeuble, 0)
    
    if valeur_immeuble <= 0:
        print("❌ Valeur immeuble invalide")
        return 0, 0
    
    # Calcul du ratio prêt-valeur
    ltv = (montant_pret / valeur_immeuble) * 100
    
    # Si le ratio est supérieur à 95%, fixer à 95% (mise de fonds minimale de 5%)
    if ltv > 95.0:
        ltv = 95.0
        montant_pret = valeur_immeuble * 0.95
    
    # Déterminer le nombre d'unités
    nombre_unites = 0
    print(f"📋 Données de propriété disponibles: {property_data is not None}")
    
    if property_data is not None:
        # Gérer différents types de données
        if isinstance(property_data, dict):
            raw_units = property_data.get('nombre_unites')
            print(f"📊 Valeur brute nombre_unites (dict): {raw_units}")
            if raw_units is not None:
                nombre_unites = clean_numeric_value(raw_units)
        elif isinstance(property_data, pd.Series):
            if 'nombre_unites' in property_data.index:
                raw_units = property_data['nombre_unites']
                print(f"📊 Valeur brute nombre_unites (Series): {raw_units}")
                nombre_unites = clean_numeric_value(raw_units)
        elif hasattr(property_data, 'get'):
            raw_units = property_data.get('nombre_unites')
            print(f"📊 Valeur brute nombre_unites (object): {raw_units}")
            if raw_units is not None:
                nombre_unites = clean_numeric_value(raw_units)
        
        print(f"📊 Valeur nettoyée nombre_unites: {nombre_unites}")
    
    # Debug complet avec le critère EGI
    if nombre_unites > 0:
        print(f"✅ Nombre de logements trouvé: {nombre_unites}")
        if nombre_unites >= 6:
            print(f"📊 Multi-logement détecté - Critère EGI: {'MET' if use_egi_met else 'NOT MET'}")
        else:
            print(f"📊 Plex détecté (≤5 unités) - Pas d'EGI")
    
    # Si aucun nombre d'unités trouvé, retourner 0
    if nombre_unites == 0:
        print("❌ Aucun nombre d'unités trouvé")
        return 0, 0
    
    # Si 6 unités et plus, utiliser la table multi-logement
    if nombre_unites >= 6:
        print(f"🏢 Traitement multi-logement - LTV initial: {ltv:.2f}%")
        
        # Pour multi-logements, le ratio max est 85%
        if ltv > 85.0:
            print(f"⚠️ LTV plafonné à 85% (était {ltv:.2f}%)")
            ltv = 85.0
            montant_pret = valeur_immeuble * 0.85
        
        # Charger les taux multi-logement
        try:
            schl_df = load_schl_rates_multi_logement()
            print(f"✅ Table multi-logement chargée avec succès")
            
            # Déterminer la colonne à utiliser selon le critère EGI
            prime_column = 'prime_montant_total_egi_met' if use_egi_met else 'prime_montant_total_egi_not_met'
            print(f"📌 Utilisation de la colonne: {prime_column}")
            
            # Trouver le bon taux selon le LTV
            if ltv <= 65.0:
                raw_rate = schl_df.iloc[0][prime_column]
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤65%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 70.0:
                raw_rate = schl_df.iloc[1][prime_column]
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤70%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 75.0:
                raw_rate = schl_df.iloc[2][prime_column]
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤75%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 80.0:
                raw_rate = schl_df.iloc[3][prime_column]
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤80%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 85.0:
                raw_rate = schl_df.iloc[4][prime_column]
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤85%: taux brut {raw_rate} → {prime_rate}%")
            else:
                prime_rate = 0
                print(f"❌ LTV > 85% non supporté pour multi-logement")
                
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des taux multi-logement: {e}")
            print(f"🔄 Utilisation des valeurs par défaut pour multi-logement")
            
            # Valeurs par défaut pour multi-logement
            if use_egi_met:
                print(f"📊 Utilisation des taux EGI MET par défaut")
                if ltv <= 65.0:
                    prime_rate = 2.60
                elif ltv <= 70.0:
                    prime_rate = 2.85
                elif ltv <= 75.0:
                    prime_rate = 3.35
                elif ltv <= 80.0:
                    prime_rate = 4.35
                elif ltv <= 85.0:
                    prime_rate = 5.35
                else:
                    prime_rate = 0
            else:
                print(f"📊 Utilisation des taux EGI NOT MET par défaut")
                if ltv <= 65.0:
                    prime_rate = 3.25
                elif ltv <= 70.0:
                    prime_rate = 3.75
                elif ltv <= 75.0:
                    prime_rate = 4.25
                elif ltv <= 80.0:
                    prime_rate = 5.00
                elif ltv <= 85.0:
                    prime_rate = 6.00
                else:
                    prime_rate = 0
            print(f"📊 Taux par défaut sélectionné: {prime_rate}%")
    
    # Si 5 unités et moins, utiliser la table plex
    else:
        print(f"🏠 Traitement plex - LTV: {ltv:.2f}%")
        
        try:
            schl_df = load_schl_rates_plex()
            print(f"✅ Table plex chargée avec succès")
            
            # Nettoyer les valeurs de pourcentage
            if ltv <= 65.0:
                raw_rate = schl_df.iloc[0]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤65%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 75.0:
                raw_rate = schl_df.iloc[1]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤75%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 80.0:
                raw_rate = schl_df.iloc[2]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤80%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 85.0:
                raw_rate = schl_df.iloc[3]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤85%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 90.0:
                raw_rate = schl_df.iloc[4]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤90%: taux brut {raw_rate} → {prime_rate}%")
            elif ltv <= 95.0:
                raw_rate = schl_df.iloc[5]['prime_montant_total']
                prime_rate = clean_percentage_value(raw_rate)
                print(f"📊 LTV ≤95%: taux brut {raw_rate} → {prime_rate}%")
            else:
                prime_rate = 0
                print(f"❌ LTV > 95% non supporté pour plex")
            
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des taux plex: {e}")
            print(f"🔄 Utilisation des valeurs par défaut pour plex")
            
            # Utiliser les valeurs fixes existantes comme fallback
            if ltv <= 65.0:
                prime_rate = 0.60
            elif ltv <= 75.0:
                prime_rate = 1.70
            elif ltv <= 80.0:
                prime_rate = 2.40
            elif ltv <= 85.0:
                prime_rate = 2.80
            elif ltv <= 90.0:
                prime_rate = 3.10
            elif ltv <= 95.0:
                prime_rate = 4.00
            else:
                prime_rate = 0
            print(f"📊 Taux par défaut sélectionné: {prime_rate}%")
    
    # Calcul de la prime
    prime_schl = montant_pret * (prime_rate / 100)
    
    # Déterminer quelle table a été utilisée et quel critère
    if nombre_unites >= 6:
        table_used = f"multi-logement (EGI {'MET' if use_egi_met else 'NOT MET'})"
    else:
        table_used = "plex"
    
    # Afficher la prime trouvée
    print(f"🏦 Prime SCHL calculée: {prime_schl:,.2f} $ (taux: {prime_rate}% - LTV: {ltv:.2f}% - {nombre_unites} unités - table: {table_used})")
    print(f"=== FIN CALCULATE_SCHL_PREMIUM ===\n")
    
    return prime_schl, prime_rate

def calculate_schl_premium_manual(montant_pret, valeur_immeuble, manual_rate):
    """
    Calcule la prime SCHL avec un taux manuel spécifié par l'utilisateur
    
    Args:
        montant_pret: Montant du prêt
        valeur_immeuble: Valeur de l'immeuble
        manual_rate: Taux de prime SCHL en pourcentage (ex: 2.40 pour 2.40%)
    
    Returns:
        tuple: (prime_schl, prime_rate)
    """
    # S'assurer que les valeurs sont des nombres
    montant_pret = safe_float_conversion(montant_pret, 0)
    valeur_immeuble = safe_float_conversion(valeur_immeuble, 0)
    manual_rate = safe_float_conversion(manual_rate, 2.40)  # Taux par défaut 2.40%
    
    if valeur_immeuble <= 0 or montant_pret <= 0:
        return 0, 0
    
    # Calcul du ratio prêt-valeur pour information
    ltv = (montant_pret / valeur_immeuble) * 100
    
    # Si le ratio est supérieur à 95%, fixer à 95% (mise de fonds minimale de 5%)
    if ltv > 95.0:
        ltv = 95.0
        montant_pret = valeur_immeuble * 0.95
    
    # Calcul de la prime avec le taux manuel
    prime_schl = montant_pret * (manual_rate / 100)
    
    print(f"\n=== CALCULATE_SCHL_PREMIUM_MANUAL ===")
    print(f"Montant prêt: {montant_pret:,.0f} $")
    print(f"Valeur immeuble: {valeur_immeuble:,.0f} $")
    print(f"LTV: {ltv:.2f}%")
    print(f"Taux manuel: {manual_rate:.2f}%")
    print(f"Prime SCHL: {prime_schl:,.2f} $")
    print(f"=== FIN CALCULATE_SCHL_PREMIUM_MANUAL ===\n")
    
    return prime_schl, manual_rate

def calculate_loan_amount_from_rdc(property_data, loan_type, conventional_rate=None):
    """
    Calcule le montant du prêt basé sur le RDC
    Retourne: (montant_pret, ratio_pret_valeur, pmt_mensuelle)
    """
    # Récupérer les données
    prix = clean_monetary_value(property_data.get('prix_vente', 0))
    # Toujours calculer le revenue net à partir de revenus_brut - depenses_totales
    revenue_brut = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    revenue_net = revenue_brut - depenses
    
    # Paramètres selon le type de prêt - TOUJOURS utiliser les valeurs de la base de données
    if loan_type == "SCHL":
        # OBLIGATOIRE: Utiliser SEULEMENT les valeurs RDC de la base de données
        rdc_ratio = clean_numeric_value(property_data.get('financement_schl_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            print(f"ERREUR CRITIQUE: RDC SCHL manquant dans la base de données pour cette propriété!")
            print(f"Colonnes attendues: financement_schl_ratio_couverture_dettes")
            print(f"Données reçues: {property_data.get('financement_schl_ratio_couverture_dettes', 'NON TROUVÉ')}")
            raise ValueError("RDC SCHL manquant dans la base de données - impossible de calculer le PMT")
            
        taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
    else:
        # OBLIGATOIRE: Utiliser SEULEMENT les valeurs RDC de la base de données
        rdc_ratio = clean_numeric_value(property_data.get('financement_conv_ratio_couverture_dettes', 0))
        if rdc_ratio == 0:
            print(f"ERREUR CRITIQUE: RDC Conventionnel manquant dans la base de données pour cette propriété!")
            print(f"Colonnes attendues: financement_conv_ratio_couverture_dettes")
            print(f"Données reçues: {property_data.get('financement_conv_ratio_couverture_dettes', 'NON TROUVÉ')}")
            raise ValueError("RDC Conventionnel manquant dans la base de données - impossible de calculer le PMT")
        
        # Utiliser le taux sélectionné si disponible
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
    
    # Validation finale: S'assurer que le RDC est valide
    if rdc_ratio <= 0:
        print(f"ERREUR: RDC invalide ({rdc_ratio}) - doit être > 0")
        raise ValueError(f"RDC invalide: {rdc_ratio}")
    
    print(f"=== RDC UTILISÉ DEPUIS LA BASE DE DONNÉES ===")
    print(f"Type de prêt: {loan_type}")
    print(f"RDC ratio: {rdc_ratio}")
    print(f"Source: {'financement_schl_ratio_couverture_dettes' if loan_type == 'SCHL' else 'financement_conv_ratio_couverture_dettes'}")
    
    # Calcul selon la formule correcte
    revenue_net_mensuel = revenue_net / 12
    
    # Calculer PMT selon la formule standard: PMT = (P*(r/12)) / (1-(1+r/12)^(-n))
    # Où P = montant_du_prêt, r = taux_d'intérêt, n = nombre_de_paiements_total
    # Nous devons d'abord calculer le montant de prêt max basé sur la capacité de paiement
    pmt_max_capacite = revenue_net_mensuel / rdc_ratio
    
    # Nombre_Total_Paiements = amortissement*12
    nombre_total_paiements = amortissement * 12
    
    # Calculer montant de prêt max basé sur la capacité de paiement
    taux_mensuel = taux_interet / 12
    if abs(taux_mensuel) < 1e-9:
        montant_pret_max_capacite = pmt_max_capacite * nombre_total_paiements
    else:
        montant_pret_max_capacite = pmt_max_capacite * (1 - (1 + taux_mensuel) ** (-nombre_total_paiements)) / taux_mensuel
    
    # Calculer la PMT mensuelle avec la formule standard
    # PMT = (Montant_du_prêt*(Taux_d'intérêt/12)) / (1-(1+Taux_d'intérêt/12)^(-Nombre_de_paiements_total))
    if abs(taux_mensuel) < 1e-9:
        pmt_mensuelle = montant_pret_max_capacite / nombre_total_paiements
    else:
        pmt_mensuelle = (montant_pret_max_capacite * taux_mensuel) / (1 - (1 + taux_mensuel) ** (-nombre_total_paiements))
    
    # pret max = PMT mensuelle * (1 - (1 + (taux_interet/12))^-Nombre_Total_Paiements) / (taux_interet/12)
    taux_mensuel = taux_interet / 12
    if abs(taux_mensuel) < 1e-9:
        montant_pret = pmt_mensuelle * nombre_total_paiements
    else:
        montant_pret = pmt_mensuelle * (1 - (1 + taux_mensuel) ** (-nombre_total_paiements)) / taux_mensuel
    
    # Ratio prêt/valeur
    ratio_pret_valeur = montant_pret / prix if prix > 0 else 0
    
    # Pour les prêts SCHL, le ratio prêt-valeur ne peut pas dépasser 95%
    if loan_type == "SCHL" and ratio_pret_valeur > 0.95:
        ratio_pret_valeur = 0.95
        montant_pret = prix * ratio_pret_valeur
        # Recalculer la PMT si on a limité le prêt
        pmt_mensuelle = montant_pret * taux_mensuel / (1 - (1 + taux_mensuel) ** (-nombre_total_paiements)) if taux_mensuel > 0 else montant_pret / nombre_total_paiements
    elif loan_type != "SCHL" and ratio_pret_valeur > 0.80:
        ratio_pret_valeur = 0.80
        montant_pret = prix * ratio_pret_valeur
        # Recalculer la PMT si on a limité le prêt
        pmt_mensuelle = montant_pret * taux_mensuel / (1 - (1 + taux_mensuel) ** (-nombre_total_paiements)) if taux_mensuel > 0 else montant_pret / nombre_total_paiements
    
    return montant_pret, ratio_pret_valeur, pmt_mensuelle


def calculate_progressive_tax(revenu_imposable, province_name):
    """
    Calcule l'impôt progressif total (fédéral + provincial) pour les particuliers selon les tranches d'imposition
    """
    if revenu_imposable <= 0:
        return 0
    
    # Charger les tranches d'imposition
    tax_df = load_tax_rates_particulier()
    
    # Calculer l'impôt fédéral
    federal_df = tax_df[tax_df['province'] == 'fédéral'].copy()
    federal_df = federal_df.sort_values('id')
    
    # Calculer l'impôt provincial
    province_df = tax_df[tax_df['province'] == province_name].copy()
    
    # Si la province n'est pas trouvée, utiliser seulement le fédéral
    if province_df.empty:
        print(f"⚠️ ATTENTION: Province '{province_name}' non trouvée dans la base de données!")
        print("Calcul avec impôt fédéral seulement - le résultat sera sous-estimé!")
        province_df = pd.DataFrame()  # DataFrame vide
    else:
        province_df = province_df.sort_values('id')
    
    # Afficher des informations de débogage
    print("=== CALCUL IMPÔT PROGRESSIF (FÉDÉRAL + PROVINCIAL) ===")
    print(f"Province: {province_name}")
    print(f"Revenu imposable: {revenu_imposable:,.0f} $")
    print(f"Tranches fédérales trouvées: {len(federal_df)}")
    print(f"Tranches provinciales trouvées: {len(province_df)}")
    
    # Calculer l'impôt fédéral
    impot_federal = 0
    impot_federal = _calculate_tax_for_jurisdiction(revenu_imposable, federal_df, "FÉDÉRAL")
    
    # Calculer l'impôt provincial
    impot_provincial = 0
    if not province_df.empty:
        impot_provincial = _calculate_tax_for_jurisdiction(revenu_imposable, province_df, province_name.upper())
    
    # Total
    impot_total = impot_federal + impot_provincial
    
    print(f"Impôt fédéral: {impot_federal:,.0f} $")
    print(f"Impôt provincial ({province_name}): {impot_provincial:,.0f} $")
    print(f"Impôt total (fédéral + provincial): {impot_total:,.0f} $")
    if revenu_imposable > 0:
        print(f"Taux effectif combiné: {(impot_total/revenu_imposable):.1%}")
        
    return impot_total


def _calculate_tax_for_jurisdiction(revenu_imposable, tax_df, jurisdiction_name):
    """
    Calcule l'impôt pour une juridiction spécifique (fédéral ou provincial)
    """
    if tax_df.empty or revenu_imposable <= 0:
        return 0
    
    impot_total = 0
    montant_impose_precedent = 0
    
    print(f"\n--- Calcul {jurisdiction_name} ---")
    
    # Parcourir les tranches d'imposition
    for idx, row in tax_df.iterrows():
        try:
            # Convertir le taux en nombre décimal
            taux = row.get('taux_marginal', 0)
            if isinstance(taux, str) and '%' in taux:
                tax_rate = float(taux.replace('%', '').replace(',', '.').strip()) / 100
            else:
                tax_rate = float(str(taux).replace(',', '.')) / 100
                
            # Extraire les limites de la tranche à partir de la description
            description = row['tranche']
            
            # Traitement par cas selon le format de description
            if "ou moins" in description:
                # Format "X $ ou moins"
                limit = float(description.split("$")[0].replace(" ", "").replace(",", "."))
                if revenu_imposable <= limit:
                    # Tout le revenu est dans cette tranche
                    montant_dans_tranche = revenu_imposable - montant_impose_precedent
                    impot_tranche = montant_dans_tranche * tax_rate
                    impot_total += impot_tranche
                    print(f"{jurisdiction_name}: {description} - Taux: {tax_rate:.2%} - Base: {montant_dans_tranche:,.2f} $ - Impôt: {impot_tranche:,.2f} $")
                    break  # On a fini car tout le revenu est imposé
                else:
                    # Seulement la partie jusqu'à la limite
                    montant_dans_tranche = limit - montant_impose_precedent
                    impot_tranche = montant_dans_tranche * tax_rate
                    impot_total += impot_tranche
                    print(f"{jurisdiction_name}: {description} - Taux: {tax_rate:.2%} - Base: {montant_dans_tranche:,.2f} $ - Impôt: {impot_tranche:,.2f} $")
                    montant_impose_precedent = limit
            elif "jusqu'à" in description:
                # Format "dépassant X $ jusqu'à Y $"
                parts = description.split("dépassant")[1].split("jusqu'à")
                lower_limit = float(parts[0].split("$")[0].replace(" ", "").replace(",", "."))
                upper_limit = float(parts[1].split("$")[0].replace(" ", "").replace(",", "."))
                
                if revenu_imposable > lower_limit:
                    # Calculer le montant dans cette tranche
                    if revenu_imposable <= upper_limit:
                        montant_dans_tranche = revenu_imposable - lower_limit
                    else:
                        montant_dans_tranche = upper_limit - lower_limit
                    
                    impot_tranche = montant_dans_tranche * tax_rate
                    impot_total += impot_tranche
                    print(f"{jurisdiction_name}: {description} - Taux: {tax_rate:.2%} - Base: {montant_dans_tranche:,.2f} $ - Impôt: {impot_tranche:,.2f} $")
                    
                    if revenu_imposable <= upper_limit:
                        break  # On a fini
                    montant_impose_precedent = upper_limit
            elif "à" in description and not "jusqu'à" in description:
                # Format "X $ à Y $"
                parts = description.split("à")
                lower_limit = float(parts[0].split("$")[0].replace(" ", "").replace(",", "."))
                upper_limit = float(parts[1].split("$")[0].replace(" ", "").replace(",", "."))
                
                if revenu_imposable > lower_limit:
                    # Calculer le montant dans cette tranche
                    if revenu_imposable <= upper_limit:
                        montant_dans_tranche = revenu_imposable - lower_limit
                    else:
                        montant_dans_tranche = upper_limit - lower_limit
                    
                    impot_tranche = montant_dans_tranche * tax_rate
                    impot_total += impot_tranche
                    print(f"{jurisdiction_name}: {description} - Taux: {tax_rate:.2%} - Base: {montant_dans_tranche:,.2f} $ - Impôt: {impot_tranche:,.2f} $")
                    
                    if revenu_imposable <= upper_limit:
                        break  # On a fini
                    montant_impose_precedent = upper_limit
            elif "Plus de" in description or "dépassant" in description:
                # Format "Plus de X $" ou "dépassant X $"
                if "Plus de" in description:
                    limit = float(description.split("Plus de")[1].split("$")[0].replace(" ", "").replace(",", "."))
                else:
                    limit = float(description.split("dépassant")[1].split("$")[0].replace(" ", "").replace(",", "."))
                
                if revenu_imposable > limit:
                    montant_dans_tranche = revenu_imposable - limit
                    impot_tranche = montant_dans_tranche * tax_rate
                    impot_total += impot_tranche
                    print(f"{jurisdiction_name}: {description} - Taux: {tax_rate:.2%} - Base: {montant_dans_tranche:,.2f} $ - Impôt: {impot_tranche:,.2f} $")
            else:
                # Autres cas non gérés
                print(f"Format de tranche non reconnu: {description}")
                
        except Exception as e:
            print(f"Erreur conversion taux: {row['tranche']} - {e}")
    
    print(f"Total {jurisdiction_name}: {impot_total:,.0f} $")
    return impot_total


def get_tax_rate_for_province(province_name, is_incorporated):
    """
    Récupère le taux d'imposition selon la province et le statut fiscal
    """
    if is_incorporated:
        # Pour les entreprises incorporées, utiliser la table entreprise
        tax_df = load_tax_rates_entreprise()
        
        # Chercher la province dans la table
        province_row = tax_df[tax_df['province'] == province_name]
        
        if not province_row.empty:
            # Utiliser la colonne 'pourcentage'
            taux = province_row['pourcentage'].iloc[0]
            
            # Nettoyer la valeur si c'est une chaîne
            if isinstance(taux, str):
                taux_clean = taux.replace('%', '').replace(',', '.').strip()
                return float(taux_clean)
            else:
                return float(taux)
        else:
            # Si la province n'est pas trouvée, essayer de trouver une valeur par défaut
            print(f"Province '{province_name}' non trouvée dans la table entreprise")
            # Chercher la ligne "Fédéral" comme valeur par défaut
            federal_row = tax_df[tax_df['province'] == 'Fédéral']
            if not federal_row.empty:
                taux = federal_row['pourcentage'].iloc[0]
                if isinstance(taux, str):
                    taux_clean = taux.replace('%', '').replace(',', '.').strip()
                    return float(taux_clean)
                else:
                    return float(taux)
            
            # Valeur par défaut si rien n'est trouvé
            return 26.5
    else:
        # Pour les particuliers non-incorporés, le taux est progressif
        # On retourne une valeur indicative qui sera recalculée avec calculate_progressive_tax
        tax_df = load_tax_rates_particulier()
        
        province_row = tax_df[tax_df['province'] == province_name]
        
        if not province_row.empty:
            if 'combine' in province_row.columns and pd.notna(province_row['combine'].iloc[0]):
                return float(str(province_row['combine'].iloc[0]).replace(',', '.'))
            elif 'pourcentage' in province_row.columns and pd.notna(province_row['pourcentage'].iloc[0]):
                return float(str(province_row['pourcentage'].iloc[0]).replace(',', '.'))
        
        return 45.0  # Taux marginal maximal approximatif


def get_municipal_tax_rate(region_name, property_type='residentiel'):
    """
    Récupère le taux de taxation municipal pour une région et un type de propriété donnés
    
    Args:
        region_name: Nom de la région
        property_type: Type de propriété ('residentiel', 'commercial', 'industriel', etc.)
    
    Returns:
        float: Taux de taxation en pourcentage
    """
    try:
        df_tax = load_taxation_municipale()
        
        if df_tax.empty:
            return None
            
        # Normaliser le nom de la région pour la comparaison
        region_name_normalized = region_name.strip().lower()
        
        # Chercher la région dans le DataFrame
        region_match = df_tax[df_tax['region'].str.lower() == region_name_normalized]
        
        if region_match.empty:
            # Essayer une correspondance partielle
            region_match = df_tax[df_tax['region'].str.lower().str.contains(region_name_normalized, na=False)]
        
        if not region_match.empty and property_type in region_match.columns:
            # Récupérer la valeur du taux
            taux_str = region_match[property_type].iloc[0]
            
            # Parser le taux (peut contenir des conditions comme "1.7575 ou (30 000 000 et plus = 2.6022)")
            if isinstance(taux_str, str):
                # Extraire le premier taux (taux de base)
                import re
                match = re.match(r'(\d+\.?\d*)', str(taux_str))
                if match:
                    return float(match.group(1))
            else:
                return float(taux_str)
        
        return None
        
    except Exception as e:
        print(f"Erreur lors de la récupération du taux de taxation municipal: {e}")
        return None


def get_property_region(property_data):
    """
    Détermine la région d'un immeuble à partir de ses coordonnées
    
    Args:
        property_data: Dictionnaire contenant les données de l'immeuble
    
    Returns:
        str: Nom de la région ou None si non trouvé
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
        
        # Créer un point à partir des coordonnées
        point = Point(lon, lat)
        
        # Charger toutes les régions du Québec
        from filter.data_loading import get_db_connection_string
        engine = create_engine(
            get_db_connection_string('analysis'),
            connect_args={"client_encoding": "utf8"}
        )
        
        query = '''
            SELECT 
                region_id,
                region_nom,
                ST_AsEWKB(geo_zone) as geom_bin
            FROM id."Province_Quebec_Regions_ID"
        '''
        regions_df = pd.read_sql(query, engine)
        engine.dispose()
        
        # Parcourir chaque région pour vérifier si le point est à l'intérieur
        for _, row in regions_df.iterrows():
            try:
                from shapely import wkb
                if pd.notna(row['geom_bin']):
                    if isinstance(row['geom_bin'], memoryview):
                        geometry = wkb.loads(bytes(row['geom_bin']))
                    else:
                        geometry = wkb.loads(row['geom_bin'])
                    
                    if geometry.contains(point) or geometry.intersects(point):
                        return row['region_nom']
            except Exception as e:
                print(f"Erreur lors de la vérification de la région {row['region_nom']}: {e}")
                continue
                
        return None
        
    except Exception as e:
        print(f"Erreur lors de la détermination de la région: {e}")
        return None


def compare_municipal_taxes(property_data, region_name=None):
    """
    Compare les taxes municipales de la BD avec les taux officiels
    
    Args:
        property_data: Dictionnaire contenant les données de l'immeuble
        region_name: Nom de la région (optionnel, sera déterminé automatiquement si non fourni)
    
    Returns:
        dict: Comparaison des taxes
    """
    try:
        # Déterminer la région si non fournie
        if not region_name:
            region_name = get_property_region(property_data)
            
        if not region_name:
            return {
                'region': 'Non déterminée',
                'taux_officiel': None,
                'taxes_bd': None,
                'eval_municipale': None,
                'taxes_calculees': None,
                'difference': None,
                'difference_pct': None
            }
        
        # Récupérer le taux officiel
        taux_officiel = get_municipal_tax_rate(region_name, 'residentiel')
        
        # Récupérer les données de la BD
        taxes_bd = clean_monetary_value(property_data.get('depenses_taxes_municipales', 0))
        eval_municipale = clean_monetary_value(property_data.get('eval_municipale_totale', 0))
        
        # Calculer les taxes théoriques
        taxes_calculees = None
        if taux_officiel and eval_municipale > 0:
            taxes_calculees = eval_municipale * (taux_officiel / 100)
        
        # Calculer la différence
        difference = None
        difference_pct = None
        if taxes_calculees and taxes_bd > 0:
            difference = taxes_calculees - taxes_bd
            difference_pct = (difference / taxes_bd) * 100
        
        return {
            'region': region_name,
            'taux_officiel': taux_officiel,
            'taxes_bd': taxes_bd,
            'eval_municipale': eval_municipale,
            'taxes_calculees': taxes_calculees,
            'difference': difference,
            'difference_pct': difference_pct
        }
        
    except Exception as e:
        print(f"Erreur lors de la comparaison des taxes municipales: {e}")
        return {
            'region': 'Erreur',
            'taux_officiel': None,
            'taxes_bd': None,
            'eval_municipale': None,
            'taxes_calculees': None,
            'difference': None,
            'difference_pct': None
        }


def calcul_pret_max(mensualite_max, taux_annuel, amortissement):
    """
    Calcule le prêt maximal en utilisant la formule d'annuité.
    """
    N = int(amortissement * 12)
    taux_mensuel = taux_annuel / 12
    if abs(taux_mensuel) < 1e-9:
        return mensualite_max * N
    return mensualite_max * (1 - (1 + taux_mensuel) ** (-N)) / taux_mensuel


def calcul_mensualite(montant_pret, taux_annuel, amortissement_annees):
    """
    Calcule la mensualité d'un prêt selon la formule PMT standard.
    
    PMT = (Montant_du_prêt * (Taux_d'intérêt/12)) / (1-(1+Taux_d'intérêt/12)^(-Nombre_de_paiements_total))
    
    Args:
        montant_pret: Montant du prêt en dollars
        taux_annuel: Taux d'intérêt annuel en format décimal (ex: 0.055 pour 5.5%)
        amortissement_annees: Période d'amortissement en années
        
    Returns:
        tuple: (mensualite, nombre_de_paiements_total)
    """
    # Validation des entrées
    montant_pret = safe_float_conversion(montant_pret, 0)
    taux_annuel = safe_float_conversion(taux_annuel, 0)
    amortissement_annees = safe_float_conversion(amortissement_annees, 25)
    
    # Si le taux semble être en pourcentage (>1), le convertir en décimal
    if taux_annuel > 1:
        print(f"⚠️ Taux d'intérêt reçu en pourcentage ({taux_annuel}%), conversion en décimal")
        taux_annuel = taux_annuel / 100
    
    # Calcul du nombre de paiements
    n_payments = int(amortissement_annees * 12)
    
    # Calcul du taux mensuel
    taux_mensuel = taux_annuel / 12
    
    # Si le taux est très proche de zéro, éviter la division par zéro
    if abs(taux_mensuel) < 1e-9:
        mensualite = montant_pret / n_payments
    else:
        # Formule PMT standard
        mensualite = (montant_pret * taux_mensuel) / (1 - (1 + taux_mensuel) ** (-n_payments))
    
    return mensualite, n_payments




def calculate_cashflow_projection(property_data, loan_type, tax_province, tax_status, montant_finance, taux_interet, amortissement, scenarios_taux=None, inflation_rate=None, rent_increase=None, use_dpa=False, dpa_rate=None, building_value=None):
    """
    Calcule la projection du cashflow sur la durée de l'amortissement avec support des taux variables
    
    Args:
        property_data: Données de la propriété
        loan_type: Type de prêt
        tax_province: Province pour taxation
        tax_status: Statut fiscal
        montant_finance: Montant financé
        taux_interet: Taux d'intérêt initial
        amortissement: Période d'amortissement
        scenarios_taux: Dict avec les changements de taux par année
                       Ex: {5: 0.065, 10: 0.070} = 6.5% à partir de l'année 5, 7% à partir de l'année 10
        inflation_rate: Taux d'inflation annuel (optionnel)
        rent_increase: Augmentation annuelle des loyers (optionnel)
        use_dpa: Utiliser la DPA ou non
        dpa_rate: Taux de DPA
        building_value: Valeur du bâtiment pour DPA
    """
    
    # Récupérer les données de base
    revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    
    # Valeurs par défaut pour inflation et augmentation des loyers
    if inflation_rate is None:
        inflation_rate = 0
    if rent_increase is None:
        rent_increase = 0
    
    is_incorporated = tax_status == "incorporated"
    
    # Calculer pour chaque année
    projection_data = []
    solde_restant = montant_finance
    remaining_building_value = building_value if use_dpa and building_value else 0
    
    # === CORRECTION : Utiliser la PMT mensuelle basée sur le RDC ===
    # IMPORTANT: Cohérence avec l'onglet profit
    # La mensualité doit être basée sur la capacité de paiement (RDC) et non sur le montant financé
    # Cela garantit que les calculs d'intérêts, capital et montant imposable sont cohérents
    # entre toutes les sections de l'application (profit, projections, etc.)
    _, _, pmt_mensuelle_rdc = calculate_loan_amount_from_rdc(property_data, loan_type)
    pmt_mensuelle_initiale = pmt_mensuelle_rdc
    
    print(f"🔧 CORRECTION: Utilisation PMT basée sur RDC: {pmt_mensuelle_initiale:,.2f} $ (cohérent avec onglet profit)")
    
    # Taux actuel (peut changer selon les scénarios)
    taux_actuel = taux_interet
    
    for annee in range(1, int(amortissement) + 1):
        # Calculer les revenus et dépenses avec inflation et augmentation
        revenus_annee = revenus_bruts * ((1 + rent_increase/100) ** (annee - 1))
        depenses_annee = depenses * ((1 + inflation_rate/100) ** (annee - 1))
        revenue_net = revenus_annee - depenses_annee
        
        # Vérifier s'il y a un changement de taux pour cette année
        if scenarios_taux and annee in scenarios_taux:
            nouveau_taux = scenarios_taux[annee]
            print(f"📊 Changement de taux année {annee}: {taux_actuel:.1%} → {nouveau_taux:.1%}")
            taux_actuel = nouveau_taux
            
            # Recalculer la mensualité avec le nouveau taux et le solde restant
            # Note: Pour les taux variables, on recalcule car c'est un nouveau contrat de prêt
            # Nombre d'années restantes
            annees_restantes = int(amortissement) - annee + 1
            pmt_mensuelle, _ = calcul_mensualite(solde_restant, taux_actuel, annees_restantes)
            print(f"📊 Nouvelle mensualité: {pmt_mensuelle:,.2f} $ (solde: {solde_restant:,.0f} $, {annees_restantes} ans)")
        else:
            # Utiliser la mensualité précédente (initiale ou recalculée)
            if annee == 1:
                pmt_mensuelle = pmt_mensuelle_initiale
            # Sinon, conserver la mensualité précédemment calculée
            # Si pmt_mensuelle n'est pas définie, utiliser la mensualité initiale
            if 'pmt_mensuelle' not in locals():
                pmt_mensuelle = pmt_mensuelle_initiale
        
        # Calcul de la DPA pour l'année
        dpa_annee = 0
        if use_dpa and remaining_building_value > 0 and dpa_rate:
            if annee == 1:
                # Règle de demi-année pour la première année
                dpa_annee = remaining_building_value * (dpa_rate / 100) * 0.5
            else:
                dpa_annee = remaining_building_value * (dpa_rate / 100)
            
            # Limiter la DPA au revenu positif
            max_dpa = max(0, revenue_net)
            dpa_annee = min(dpa_annee, max_dpa)
            
            remaining_building_value -= dpa_annee
        
        # Calcul annuel
        interet_annuel = 0
        capital_annuel = 0
        
        # Calcul mensuel pour l'année avec le taux actuel
        solde_debut_annee = solde_restant
        for mois in range(12):
            if solde_restant <= 0:
                break
                
            interet_mois = solde_restant * (taux_actuel / 12)
            capital_mois = min(pmt_mensuelle - interet_mois, solde_restant)
            
            # S'assurer que le capital n'est pas négatif
            if capital_mois < 0:
                capital_mois = 0
                interet_mois = pmt_mensuelle
            
            interet_annuel += interet_mois
            capital_annuel += capital_mois
            solde_restant -= capital_mois
            
            if solde_restant < 0:
                solde_restant = 0
        
        # Calcul du montant imposable avec DPA
        montant_imposable = revenue_net - interet_annuel - dpa_annee
        
        # Calcul de l'impôt
        if is_incorporated:
            tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
            impot = montant_imposable * tax_rate if montant_imposable > 0 else 0
        else:
            # Pour les particuliers, on calcule l'impôt progressif fédéral et provincial
            impot = calculate_progressive_tax(montant_imposable, tax_province) if montant_imposable > 0 else 0
        
        # Cashflow final = Revenue net - impôt - intérêts - capital remboursé
        cashflow_annuel = revenue_net - impot - interet_annuel - capital_annuel
        cashflow_mensuel = cashflow_annuel / 12
        
        projection_data.append({
            'Année': annee,
            'Taux Intérêt': taux_actuel * 100,  # Afficher en %
            'Revenue Brut': revenus_annee,
            'Dépenses': depenses_annee,
            'Revenue Net': revenue_net,
            'Mensualité': pmt_mensuelle * 12,  # Annualiser pour cohérence
            'Intérêts': interet_annuel,
            'Capital': capital_annuel,
            'DPA': dpa_annee,
            'Montant Imposable': montant_imposable,
            'Impôt': impot,
            'Cashflow annuel': cashflow_annuel,
            'Cashflow mensuel': cashflow_mensuel,
            'Solde prêt': solde_restant
        })
    
    return pd.DataFrame(projection_data)


def create_interest_rate_scenarios(taux_initial, terme_initial=5):
    """
    Crée des scénarios typiques de taux d'intérêt variables
    
    Args:
        taux_initial: Taux d'intérêt initial (en décimal, ex: 0.055 pour 5.5%)
        terme_initial: Terme initial en années (par défaut 5 ans)
    
    Returns:
        dict: Scénarios avec différents profils de taux
    """
    
    scenarios = {
        'taux_fixe': {},  # Pas de changement
        'hausse_graduelle': {
            terme_initial: taux_initial + 0.005,      # +0.5% au renouvellement
            terme_initial + 5: taux_initial + 0.010,  # +1.0% au 2e renouvellement
            terme_initial + 10: taux_initial + 0.015  # +1.5% au 3e renouvellement
        },
        'hausse_majeure': {
            terme_initial: taux_initial + 0.015,      # +1.5% au renouvellement
            terme_initial + 5: taux_initial + 0.025,  # +2.5% au 2e renouvellement
            terme_initial + 10: taux_initial + 0.020  # +2.0% au 3e renouvellement (baisse légère)
        },
        'cycle_economique': {
            terme_initial: taux_initial + 0.010,      # +1.0% (récession)
            terme_initial + 3: taux_initial - 0.005,  # -0.5% (reprise)
            terme_initial + 8: taux_initial + 0.020,  # +2.0% (inflation)
            terme_initial + 13: taux_initial + 0.005  # +0.5% (stabilisation)
        }
    }
    
    return scenarios


def compare_cashflow_scenarios(property_data, loan_type, tax_province, tax_status, montant_finance, taux_interet, amortissement, inflation_rate=None, rent_increase=None, use_dpa=False, dpa_rate=None, building_value=None):
    """
    Compare les projections de cashflow selon différents scénarios de taux d'intérêt
    
    Args:
        property_data: Données de la propriété
        loan_type: Type de prêt
        tax_province: Province pour taxation
        tax_status: Statut fiscal
        montant_finance: Montant financé
        taux_interet: Taux d'intérêt initial
        amortissement: Période d'amortissement
        inflation_rate: Taux d'inflation annuel
        rent_increase: Augmentation annuelle des loyers
        use_dpa: Utiliser la DPA
        dpa_rate: Taux de DPA
        building_value: Valeur du bâtiment pour DPA
    
    Returns:
        dict: Comparaison des scénarios avec métriques clés
    """
    
    # Créer les scénarios de taux
    scenarios_taux = create_interest_rate_scenarios(taux_interet)
    
    results = {}
    
    for scenario_name, scenario_rates in scenarios_taux.items():
        # Calculer la projection pour ce scénario
        projection_df = calculate_cashflow_projection(
            property_data, loan_type, tax_province, tax_status, 
            montant_finance, taux_interet, amortissement, scenario_rates,
            inflation_rate, rent_increase, use_dpa, dpa_rate, building_value
        )
        
        # Calculer les métriques clés
        cashflow_negatif_5ans = calculate_negative_cashflow_total(
            property_data, loan_type, tax_province, tax_status, 5, scenario_rates
        )
        
        cashflow_moyen_10ans = projection_df.head(10)['Cashflow annuel'].mean() if len(projection_df) >= 10 else projection_df['Cashflow annuel'].mean()
        
        # Cashflow cumulé sur 10 ans
        cashflow_cumule_10ans = projection_df.head(10)['Cashflow annuel'].sum() if len(projection_df) >= 10 else projection_df['Cashflow annuel'].sum()
        
        # Année où le cashflow devient positif (si applicable)
        cashflow_positif = projection_df[projection_df['Cashflow annuel'] > 0]
        annee_cashflow_positif = cashflow_positif['Année'].min() if not cashflow_positif.empty else None
        
        results[scenario_name] = {
            'projection_complete': projection_df,
            'cashflow_negatif_5ans': cashflow_negatif_5ans,
            'cashflow_moyen_10ans': cashflow_moyen_10ans,
            'cashflow_cumule_10ans': cashflow_cumule_10ans,
            'annee_cashflow_positif': annee_cashflow_positif,
            'taux_final': projection_df['Taux Intérêt'].iloc[-1] if not projection_df.empty else taux_interet * 100,
            'scenarios_rates': scenario_rates
        }
    
    return results


def calculate_negative_cashflow_total(property_data, loan_type, tax_province, tax_status, years_to_calculate=5, scenarios_taux=None):
    """
    Calcule le total des cashflows négatifs sur les premières années avec support des taux variables
    
    Args:
        property_data: Données de la propriété
        loan_type: Type de prêt (SCHL ou conventionnel)
        tax_province: Province pour le calcul des taxes
        tax_status: Statut fiscal (incorporated ou non)
        years_to_calculate: Nombre d'années à calculer (par défaut 5)
        scenarios_taux: Dict avec les changements de taux par année
    
    Returns:
        float: Total des cashflows négatifs
    """
    try:
        # Récupérer les données de base
        revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
        depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
        revenue_net = revenus_bruts - depenses
        
        # Calculer les paramètres du prêt
        montant_pret, _, pmt_mensuelle_initiale = calculate_loan_amount_from_rdc(property_data, loan_type)
        
        # Calculer le taux d'intérêt et l'amortissement
        if loan_type == "SCHL":
            taux_interet_initial = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
            amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
        else:
            taux_interet_initial = clean_numeric_value(property_data.get('financement_conv_taux_interet', 5.5)) / 100
            amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
        
        # Calculer la prime SCHL si applicable
        prime_schl = 0
        if loan_type == "SCHL":
            prime_schl, _ = calculate_schl_premium(montant_pret, clean_monetary_value(property_data.get('prix_vente', 0)))
        
        montant_finance = montant_pret + prime_schl
        
        is_incorporated = tax_status == "incorporated"
        
        # Calculer le cashflow avec support des taux variables
        cashflow_negatif_total = 0
        solde_restant = montant_finance
        pmt_mensuelle = pmt_mensuelle_initiale
        taux_actuel = taux_interet_initial
        
        for annee in range(1, min(years_to_calculate + 1, int(amortissement) + 1)):
            # Vérifier s'il y a un changement de taux pour cette année
            if scenarios_taux and annee in scenarios_taux:
                taux_actuel = scenarios_taux[annee]
                # Recalculer la mensualité avec le nouveau taux
                annees_restantes = int(amortissement) - annee + 1
                pmt_mensuelle, _ = calcul_mensualite(solde_restant, taux_actuel, annees_restantes)
            
            # Calcul annuel des intérêts et capital
            interet_annuel = 0
            capital_annuel = 0
            
            # Calcul mensuel pour l'année
            for mois in range(12):
                if solde_restant <= 0:
                    break
                    
                interet_mois = solde_restant * (taux_actuel / 12)
                capital_mois = min(pmt_mensuelle - interet_mois, solde_restant)
                
                if capital_mois < 0:
                    capital_mois = 0
                    interet_mois = pmt_mensuelle
                
                interet_annuel += interet_mois
                capital_annuel += capital_mois
                solde_restant -= capital_mois
                
                if solde_restant < 0:
                    solde_restant = 0
            
            # Calcul du cashflow pour l'année
            montant_imposable = revenue_net - interet_annuel
            
            # Calcul de l'impôt
            if is_incorporated:
                tax_rate = get_tax_rate_for_province(tax_province, is_incorporated) / 100
                impot = montant_imposable * tax_rate if montant_imposable > 0 else 0
            else:
                impot = calculate_progressive_tax(montant_imposable, tax_province) if montant_imposable > 0 else 0
            
            # Cashflow annuel
            cashflow_annuel = revenue_net - impot - interet_annuel - capital_annuel
            
            # Si le cashflow est négatif, l'ajouter au total
            if cashflow_annuel < 0:
                cashflow_negatif_total += abs(cashflow_annuel)
        
        return cashflow_negatif_total
    
    except Exception as e:
        print(f"Erreur dans le calcul du cashflow négatif total: {e}")
        return 0


def calculate_bienvenue_tax(prix, property_data=None):
    """
    Calcule la taxe de bienvenue selon les tranches et la région de l'immeuble
    
    Args:
        prix: Prix de vente de l'immeuble
        property_data: Données de l'immeuble contenant latitude et longitude
    
    Returns:
        tuple: (montant_taxe, region_trouvee)
    """
    # Utiliser la fonction améliorée et renvoyer juste la taxe pour compatibilité
    result = calculate_bienvenue_tax_with_details(prix, property_data)
    return result['tax']


def calculate_bienvenue_tax_with_details(prix, property_data=None):
    """
    Calcule la taxe de bienvenue et retourne les détails du calcul
    
    Args:
        prix: Prix de vente de l'immeuble
        property_data: Données de l'immeuble contenant latitude et longitude
    
    Returns:
        dict: {
            'tax': montant de la taxe,
            'region': région trouvée,
            'method': méthode de calcul utilisée,
            'details': détails du calcul par tranche
        }
    """
    result = {
        'tax': 0,
        'region': None,
        'method': 'défaut',
        'details': []
    }
    
    # Tentative de trouver la région à partir des coordonnées de l'immeuble
    if property_data and 'latitude' in property_data and 'longitude' in property_data:
        try:
            # Vérifier que les coordonnées sont valides
            if pd.notna(property_data['latitude']) and pd.notna(property_data['longitude']):
                lat = float(property_data['latitude'])
                lon = float(property_data['longitude'])
                
                # Vérifier que les coordonnées sont dans des plages valides
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    from shapely.geometry import Point
                    
                    # Créer un point à partir des coordonnées (lon, lat)
                    point = Point(lon, lat)
                    
                    # Récupérer toutes les régions du Québec
                    from filter.data_loading import get_db_connection_string
                    engine = create_engine(
                        get_db_connection_string('analysis'),
                        connect_args={"client_encoding": "utf8"}
                    )
                    query = '''
                            SELECT 
                                region_id,
                                region_nom as region_name,
                                ST_AsEWKB(geo_zone) as geom_bin,
                                ST_AsText(geo_zone) as geom_text
                            FROM id."Province_Quebec_Regions_ID"
                        '''
                    regions_df = pd.read_sql(query, engine)
                    
                    # Parcourir chaque région pour vérifier si le point est à l'intérieur
                    for _, row in regions_df.iterrows():
                        try:
                            # Convertir la géométrie WKB en objet shapely
                            from shapely import wkb
                            if pd.notna(row['geom_bin']):
                                geometry = wkb.loads(row['geom_bin'].tobytes())
                                if geometry.contains(point) or geometry.intersects(point):
                                    result['region'] = row['region_name']
                                    print(f"✅ Région trouvée pour la taxe de bienvenue: {result['region']}")
                                    break
                            elif pd.notna(row['geom_text']):
                                from shapely import wkt
                                geometry = wkt.loads(row['geom_text'])
                                if geometry.contains(point) or geometry.intersects(point):
                                    result['region'] = row['region_name']
                                    print(f"✅ Région trouvée pour la taxe de bienvenue: {result['region']}")
                                    break
                        except Exception as e:
                            print(f"Erreur lors de la vérification de la région {row['region_name']}: {e}")
                            continue
                            
                    if not result['region']:
                        print(f"⚠️ Aucune région trouvée pour les coordonnées lat={lat}, lon={lon}")
                        
        except Exception as e:
            print(f"❌ Erreur lors de la détermination de la région: {e}")
    else:
        print("⚠️ Pas de coordonnées disponibles dans property_data")
    
    # Charger les taux de taxe de bienvenue
    try:
        tax_rates_df = load_taxe_bienvenue()
        
        # Si une région a été trouvée, filtrer les taux pour cette région
        if result['region']:
            # Recherche exacte d'abord
            region_rates = tax_rates_df[tax_rates_df['region'] == f"{result['region']} Taxe de Bienvenue"]
            
            # Si pas trouvé, recherche partielle
            if region_rates.empty:
                region_rates = tax_rates_df[tax_rates_df['region'].str.contains(result['region'], case=False, na=False)]
                
            if not region_rates.empty:
                print(f"✅ Taux trouvés pour {result['region']}: {len(region_rates)} tranches")
                result['method'] = 'Taux régionaux trouvés'
            else:
                print(f"⚠️ Aucun taux trouvé pour {result['region']}, utilisation des taux de Montréal")
                region_rates = tax_rates_df[tax_rates_df['region'].str.contains("Montréal", case=False, na=False)]
                result['region'] = f"{result['region']} (taux Montréal)"
                result['method'] = 'Montréal par défaut'
        else:
            # Utiliser les taux par défaut de Montréal si aucune région n'est trouvée
            print("ℹ️ Utilisation des taux de Montréal par défaut")
            region_rates = tax_rates_df[tax_rates_df['region'].str.contains("Montréal", case=False, na=False)]
            result['region'] = "Montréal (défaut)"
            result['method'] = 'Montréal par défaut'
        
        # Si aucun taux n'a été trouvé pour la région, utiliser les taux par défaut
        if region_rates.empty:
            print("⚠️ Aucun taux trouvé dans la BD, utilisation du calcul par défaut")
            result['region'] = "Québec (défaut)"
            result['method'] = 'Calcul standard Québec'
            
            # Définir les seuils pour les tranches standards du Québec
            seuil1 = 58900
            seuil2 = 294600
            seuil3 = 500000
            
            # Calcul par défaut (tranches standards du Québec)
            if prix <= seuil1:
                result['tax'] = prix * 0.005
                result['details'].append(f"0 $ - {prix:,.0f} $ : {prix:,.0f} $ × 0.5% = {result['tax']:,.2f} $")
            elif prix <= seuil2:
                tax1 = seuil1 * 0.005
                tax2 = (prix - seuil1) * 0.01
                result['tax'] = tax1 + tax2
                result['details'].append(f"0 $ - {seuil1:,.0f} $ : {seuil1:,.0f} $ × 0.5% = {tax1:,.2f} $")
                result['details'].append(f"{seuil1:,.0f} $ - {prix:,.0f} $ : {prix - seuil1:,.0f} $ × 1% = {tax2:,.2f} $")
            elif prix <= seuil3:
                tax1 = seuil1 * 0.005
                tax2 = (seuil2 - seuil1) * 0.01
                tax3 = (prix - seuil2) * 0.015
                result['tax'] = tax1 + tax2 + tax3
                result['details'].append(f"0 $ - {seuil1:,.0f} $ : {seuil1:,.0f} $ × 0.5% = {tax1:,.2f} $")
                result['details'].append(f"{seuil1:,.0f} $ - {seuil2:,.0f} $ : {seuil2 - seuil1:,.0f} $ × 1% = {tax2:,.2f} $")
                result['details'].append(f"{seuil2:,.0f} $ - {prix:,.0f} $ : {prix - seuil2:,.0f} $ × 1.5% = {tax3:,.2f} $")
            else:
                tax1 = seuil1 * 0.005
                tax2 = (seuil2 - seuil1) * 0.01
                tax3 = (seuil3 - seuil2) * 0.015
                tax4 = (prix - seuil3) * 0.02
                result['tax'] = tax1 + tax2 + tax3 + tax4
                result['details'].append(f"0 $ - {seuil1:,.0f} $ : {seuil1:,.0f} $ × 0.5% = {tax1:,.2f} $")
                result['details'].append(f"{seuil1:,.0f} $ - {seuil2:,.0f} $ : {seuil2 - seuil1:,.0f} $ × 1% = {tax2:,.2f} $")
                result['details'].append(f"{seuil2:,.0f} $ - {seuil3:,.0f} $ : {seuil3 - seuil2:,.0f} $ × 1.5% = {tax3:,.2f} $")
                result['details'].append(f"{seuil3:,.0f} $ - {prix:,.0f} $ : {prix - seuil3:,.0f} $ × 2% = {tax4:,.2f} $")
        else:
            # Calculer la taxe en fonction des tranches de prix pour la région
            # Trier les tranches par ordre croissant
            region_rates = region_rates.sort_values(by='id')
            
            # Importer la fonction de nettoyage une seule fois
            from functions.clean import clean_monetary_value
            
            # Créer une liste des tranches avec leurs limites et taux
            tranches = []
            for _, rate_row in region_rates.iterrows():
                fourchette = rate_row['fourchette_prix']
                taux_str = rate_row['taux_marginal'].replace('%', '').strip()
                taux = float(taux_str.replace(',', '.')) / 100
                
                # Extraire les limites de la fourchette
                
                if '<' in fourchette:
                    # Format: "< X $" - première tranche
                    max_val = clean_monetary_value(fourchette.replace('<', '').strip())
                    min_val = 0
                elif '>' in fourchette:
                    # Format: "> X $" - dernière tranche
                    min_val = clean_monetary_value(fourchette.replace('>', '').strip())
                    max_val = float('inf')
                else:
                    # Format: "X $ - Y $"
                    parts = fourchette.replace('$', '').split('-')
                    # Utiliser la fonction clean_monetary_value pour gérer correctement les espaces et formats
                    min_val = clean_monetary_value(parts[0].strip())
                    max_val = clean_monetary_value(parts[1].strip())
                
                tranches.append({
                    'min': min_val,
                    'max': max_val,
                    'taux': taux,
                    'fourchette': fourchette
                })
            
            print(f"📊 Calcul avec {len(tranches)} tranches pour {result['region']}")
            
            # Calculer la taxe cumulative
            for i, tranche in enumerate(tranches):
                if prix <= tranche['min']:
                    # Le prix est inférieur à cette tranche
                    break
                
                if i == 0:
                    # Première tranche (0 $ à max)
                    if prix <= tranche['max']:
                        tax_tranche = prix * tranche['taux']
                        result['tax'] = tax_tranche
                        result['details'].append(f"0 $ - {prix:,.0f} $ : {prix:,.0f} $ × {tranche['taux']*100:.1f}% = {tax_tranche:,.2f} $")
                    else:
                        tax_tranche = tranche['max'] * tranche['taux']
                        result['tax'] = tax_tranche
                        result['details'].append(f"0 $ - {tranche['max']:,.0f} $ : {tranche['max']:,.0f} $ × {tranche['taux']*100:.1f}% = {tax_tranche:,.2f} $")
                else:
                    # Tranches suivantes
                    montant_dans_tranche = min(prix, tranche['max']) - tranche['min']
                    if montant_dans_tranche > 0:
                        tax_tranche = montant_dans_tranche * tranche['taux']
                        result['tax'] += tax_tranche
                        if tranche['max'] == float('inf'):
                            result['details'].append(f"{tranche['min']:,.0f} $ - {prix:,.0f} $ : {montant_dans_tranche:,.0f} $ × {tranche['taux']*100:.1f}% = {tax_tranche:,.2f} $")
                        else:
                            fin_tranche = min(prix, tranche['max'])
                            result['details'].append(f"{tranche['min']:,.0f} $ - {fin_tranche:,.0f} $ : {montant_dans_tranche:,.0f} $ × {tranche['taux']*100:.1f}% = {tax_tranche:,.2f} $")
                
                if prix <= tranche['max']:
                    break
                    
    except Exception as e:
        print(f"❌ Erreur lors du calcul de la taxe de bienvenue: {e}")
        result['region'] = "Québec (erreur - défaut)"
        result['method'] = 'Calcul standard suite à erreur'
        
        # Définir les seuils pour les tranches standards du Québec
        seuil1 = 58900
        seuil2 = 294600
        seuil3 = 500000
        
        # Utiliser le calcul par défaut en cas d'erreur (tranches standards)
        if prix <= seuil1:
            result['tax'] = prix * 0.005
        elif prix <= seuil2:
            result['tax'] = seuil1 * 0.005 + (prix - seuil1) * 0.01
        elif prix <= seuil3:
            result['tax'] = seuil1 * 0.005 + (seuil2 - seuil1) * 0.01 + (prix - seuil2) * 0.015
        else:
            result['tax'] = seuil1 * 0.005 + (seuil2 - seuil1) * 0.01 + (seuil3 - seuil2) * 0.015 + (prix - seuil3) * 0.02
    
    print(f"💰 Taxe de bienvenue calculée: {result['tax']:,.2f} $ pour {result['region']}")
    print(f"📍 Prix de vente: {prix:,.0f} $ | Pourcentage: {(result['tax']/prix*100):.3f}%")
    
    return result


def display_bienvenue_tax_calculation(prix, property_data=None):
    """
    Affiche de manière formatée le calcul de la taxe de bienvenue
    
    Args:
        prix: Prix de vente de l'immeuble
        property_data: Données de l'immeuble contenant latitude et longitude
        
    Returns:
        float: Montant de la taxe calculée
    """
    result = calculate_bienvenue_tax_with_details(prix, property_data)
    
    print("\n" + "="*60)
    print("CALCUL DE LA TAXE DE BIENVENUE (DROIT DE MUTATION)")
    print("="*60)
    print(f"📍 Région identifiée : {result['region']}")
    print(f"📊 Méthode de calcul : {result['method']}")
    print(f"💵 Prix de vente    : {prix:,.0f} $")
    print("-"*60)
    print("DÉTAIL DU CALCUL PAR TRANCHE:")
    
    for detail in result['details']:
        print(f"  {detail}")
    
    print("-"*60)
    print(f"💰 TAXE TOTALE      : {result['tax']:,.2f} $")
    print(f"📈 Pourcentage      : {(result['tax']/prix*100):.3f}%")
    print("="*60)
    
    return result['tax']

def calculate_economic_values(property_data, revenue_net_modified=None):
    """
    Calcule les valeurs économiques réelle et de financement

    Args:
        property_data: Données de l'immeuble
        revenue_net_modified: Revenue net modifié (si l'utilisateur a ajusté les revenus/dépenses)
                             Affecte SEULEMENT la valeur réelle (marché)

    Returns:
        dict: Contenant les valeurs économiques et analyses
    """
    # Revenue net original (pour financement) - toujours calculé à partir de revenus_brut - depenses_totales
    # Cela permet de tenir compte des ajustements de revenus et dépenses pour la valeur économique
    revenus_bruts = clean_monetary_value(property_data.get('revenus_brut', 0))
    depenses = clean_monetary_value(property_data.get('depenses_totales', 0))
    revenue_net_original = revenus_bruts - depenses
    
    # Revenue net pour valeur réelle (marché) - peut être modifié par l'utilisateur
    if revenue_net_modified is not None:
        revenue_net_reelle = revenue_net_modified
    else:
        revenue_net_reelle = revenue_net_original

    # TGA réelle (calculée à partir du prix de vente actuel et revenue net modifié)
    # Ceci sert d'INDICATEUR de rendement, pas pour le calcul de valeur économique
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    tga_reelle = (revenue_net_reelle / prix_vente * 100) if prix_vente > 0 else 0

    # TGA de financement (conservateur de la banque)
    # Vérifier d'abord si on a des colonnes spécifiques pour le TGA de financement
    tga_financement_schl = clean_numeric_value(property_data.get('financement_schl_tga', 0))
    tga_financement_conv = clean_numeric_value(property_data.get('financement_conv_tga', 0))

    # Si les TGA de financement ne sont pas dans la BD, utiliser une valeur conservatrice
    if tga_financement_schl == 0:
        tga_financement_schl = 4.5  # Valeur conservatrice par défaut
    if tga_financement_conv == 0:
        tga_financement_conv = 5.0  # Valeur conservatrice par défaut

    # TGA de référence pour la valeur économique réelle (marché)
    # Utiliser un TGA de marché standard - sinon utiliser le TGA ORIGINAL (pas modifié)
    tga_marche_reference = clean_numeric_value(property_data.get('tga_marche_reference', 0))
    if tga_marche_reference == 0:
        # CORRECTION: Utiliser le TGA calculé avec revenue net ORIGINAL pour avoir une référence fixe
        # Cela permet à la valeur économique de refléter correctement l'impact des dépenses ajoutées
        tga_reference_original = (revenue_net_original / prix_vente * 100) if prix_vente > 0 else 0
        tga_marche_reference = tga_reference_original

    # Calculer les valeurs économiques
    # IMPORTANT: La valeur réelle utilise le TGA DE RÉFÉRENCE MARCHÉ avec revenue_net_reelle (modifié)
    # Les valeurs de financement utilisent revenue_net_original (non modifié)
    valeur_economique_reelle = revenue_net_reelle / (tga_marche_reference / 100) if tga_marche_reference > 0 else 0
    valeur_economique_financement_schl = revenue_net_original / (tga_financement_schl / 100) if tga_financement_schl > 0 else 0
    valeur_economique_financement_conv = revenue_net_original / (tga_financement_conv / 100) if tga_financement_conv > 0 else 0

    # Analyse du profit à l'achat (basé sur la différence entre valeur de financement et valeur économique réelle)
    profit_achat_schl = ((valeur_economique_financement_schl - valeur_economique_reelle) / valeur_economique_reelle * 100) if valeur_economique_reelle > 0 else 0
    profit_achat_conv = ((valeur_economique_financement_conv - valeur_economique_reelle) / valeur_economique_reelle * 100) if valeur_economique_reelle > 0 else 0

    return {
        'revenue_net': revenue_net_reelle,  # Pour compatibilité, retourne la valeur utilisée pour calcul réel
        'revenue_net_original': revenue_net_original,  # Nouvelle: valeur originale
        'prix_vente': prix_vente,
        'tga_reelle': tga_reelle,  # TGA indicateur (calculé)
        'tga_marche_reference': tga_marche_reference,  # TGA de référence utilisé pour valeur économique
        'tga_financement_schl': tga_financement_schl,
        'tga_financement_conv': tga_financement_conv,
        'valeur_economique_reelle': valeur_economique_reelle,
        'valeur_economique_financement_schl': valeur_economique_financement_schl,
        'valeur_economique_financement_conv': valeur_economique_financement_conv,
        'profit_achat_schl': profit_achat_schl,
        'profit_achat_conv': profit_achat_conv,
        'fait_profit_schl': profit_achat_schl > 0,
        'fait_profit_conv': profit_achat_conv > 0
    }


def calculate_initial_financing_with_bank_rules(property_data, loan_type, conventional_rate=None):
    """
    Calcule le financement initial en appliquant les règles bancaires :
    - La banque finance sur la plus petite valeur entre :
      * Le prix payé
      * La valeur économique réelle (marché)
      * La valeur économique de financement
    
    Args:
        property_data: Données de l'immeuble
        loan_type: Type de prêt ("SCHL" ou "Conventionnel")
        conventional_rate: Taux conventionnel (optionnel)
        
    Returns:
        dict: Contenant les détails du financement initial
    """
    # Récupérer les données de base
    prix_paye = clean_monetary_value(property_data.get('prix_vente', 0))
    
    # Calculer les valeurs économiques
    economic_values = calculate_economic_values(property_data)
    
    # Récupérer la valeur économique réelle (marché)
    valeur_economique_reelle = economic_values['valeur_economique_reelle']
    
    # Déterminer la valeur économique de financement selon le type de prêt
    if loan_type == "SCHL":
        valeur_economique_financement = economic_values['valeur_economique_financement_schl']
        profit_achat = economic_values['profit_achat_schl']
    else:
        valeur_economique_financement = economic_values['valeur_economique_financement_conv']
        profit_achat = economic_values['profit_achat_conv']
    
    # Règle bancaire : Finance sur la plus petite valeur entre :
    # - Prix payé
    # - Valeur économique réelle (marché)
    # - Valeur économique de financement
    valeur_financement_bancaire = min(prix_paye, valeur_economique_reelle, valeur_economique_financement)
    
    # Calculer le financement basé sur cette valeur
    montant_pret, ratio_pret_valeur, pmt_mensuelle = calculate_loan_amount_from_rdc(
        property_data, loan_type, conventional_rate
    )
    
    # Ajuster le montant si nécessaire selon la règle bancaire
    # Si la valeur de financement bancaire est plus basse que le prix payé
    if valeur_financement_bancaire < prix_paye:
        # La banque limite le financement basé sur la plus petite valeur économique
        ratio_max = 0.95 if loan_type == "SCHL" else 0.80
        montant_pret_ajuste = valeur_financement_bancaire * ratio_max
        montant_pret = min(montant_pret, montant_pret_ajuste)
    
    # Calculer les détails
    mise_de_fonds = prix_paye - montant_pret
    mise_de_fonds_pct = (mise_de_fonds / prix_paye * 100) if prix_paye > 0 else 0
    
    return {
        'prix_paye': prix_paye,
        'valeur_economique_reelle': valeur_economique_reelle,
        'valeur_economique_financement': valeur_economique_financement,
        'valeur_financement_bancaire': valeur_financement_bancaire,
        'montant_pret_initial': montant_pret,
        'mise_de_fonds': mise_de_fonds,
        'mise_de_fonds_pct': mise_de_fonds_pct,
        'profit_achat_equite': valeur_economique_financement - prix_paye,
        'peut_sortir_cash_notaire': False,  # Jamais de cash au notaire selon les règles
        'pmt_mensuelle': pmt_mensuelle,
        'banque_protege_risque': valeur_financement_bancaire < prix_paye
    }


def calculate_refinancing_scenario(property_data, loan_type, years_after_purchase=1, 
                                 appreciation_rate=0.02, stabilisation_improvements=0,
                                 conventional_rate=None):
    """
    Calcule un scénario de refinancement après X années
    
    Args:
        property_data: Données de l'immeuble
        loan_type: Type de prêt initial ("SCHL" ou "Conventionnel")
        years_after_purchase: Nombre d'années après l'achat (défaut: 1)
        appreciation_rate: Taux d'appréciation annuel (défaut: 2%)
        stabilisation_improvements: Améliorations qui augmentent la valeur ($)
        conventional_rate: Taux conventionnel (optionnel)
        
    Returns:
        dict: Contenant les détails du refinancement
    """
    # Obtenir le financement initial
    initial_financing = calculate_initial_financing_with_bank_rules(
        property_data, loan_type, conventional_rate
    )
    
    # Calculer la valeur après appréciation et améliorations
    economic_values = calculate_economic_values(property_data)
    
    if loan_type == "SCHL":
        valeur_economique_initiale = economic_values['valeur_economique_financement_schl']
    else:
        valeur_economique_initiale = economic_values['valeur_economique_financement_conv']
    
    # Valeur après appréciation (compound)
    valeur_apres_appreciation = valeur_economique_initiale * ((1 + appreciation_rate) ** years_after_purchase)
    
    # Ajouter les améliorations
    valeur_refinancement = valeur_apres_appreciation + stabilisation_improvements
    
    # Calculer le solde restant du prêt initial
    montant_pret_initial = initial_financing['montant_pret_initial']
    
    # Calcul simplifié du solde (devrait être plus précis avec tableau d'amortissement)
    if loan_type == "SCHL":
        taux_interet = clean_numeric_value(property_data.get('financement_schl_taux_interet', 5.5)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_schl_amortissement', 25))
    else:
        taux_interet = clean_numeric_value(property_data.get('financement_conv_taux_interet', 6.0)) / 100
        amortissement = clean_numeric_value(property_data.get('financement_conv_amortissement', 25))
    
    # Calcul du solde restant (approximation)
    pmt_mensuelle = initial_financing['pmt_mensuelle']
    months_passed = years_after_purchase * 12
    total_months = amortissement * 12
    
    # Formule du solde restant
    if taux_interet > 0:
        taux_mensuel = taux_interet / 12
        solde_restant = montant_pret_initial * (
            ((1 + taux_mensuel) ** total_months - (1 + taux_mensuel) ** months_passed) /
            ((1 + taux_mensuel) ** total_months - 1)
        )
    else:
        solde_restant = montant_pret_initial - (pmt_mensuelle * months_passed)
    
    # Nouveau financement (75% de la nouvelle valeur)
    ratio_refinancement = 0.75  # Standard pour refinancement
    nouveau_pret_max = valeur_refinancement * ratio_refinancement
    
    # Cash qui sort
    cash_disponible = nouveau_pret_max - solde_restant
    
    # Vérifications
    cash_positif = cash_disponible > 0
    
    return {
        'years_after_purchase': years_after_purchase,
        'valeur_economique_initiale': valeur_economique_initiale,
        'appreciation_rate': appreciation_rate,
        'stabilisation_improvements': stabilisation_improvements,
        'valeur_apres_appreciation': valeur_apres_appreciation,
        'valeur_refinancement': valeur_refinancement,
        'montant_pret_initial': montant_pret_initial,
        'solde_restant': solde_restant,
        'nouveau_pret_max': nouveau_pret_max,
        'ratio_refinancement': ratio_refinancement,
        'cash_disponible': cash_disponible,
        'cash_positif': cash_positif,
        'profit_realise_cash': max(0, cash_disponible),
        'taux_interet_utilise': taux_interet,
        'pmt_mensuelle_initiale': pmt_mensuelle
    }


def calculate_profit_breakdown(property_data, loan_type, conventional_rate=None):
    """
    Analyse complète du profit à l'achat et des opportunités de refinancement
    
    Args:
        property_data: Données de l'immeuble
        loan_type: Type de prêt ("SCHL" ou "Conventionnel")
        conventional_rate: Taux conventionnel (optionnel)
        
    Returns:
        dict: Analyse complète incluant équité instantanée et potentiel de refinancement
    """
    # Calculer les valeurs économiques
    economic_values = calculate_economic_values(property_data)
    
    # Déterminer la valeur économique de financement selon le type de prêt
    if loan_type == "SCHL":
        valeur_economique_financement = economic_values['valeur_economique_financement_schl']
    else:
        valeur_economique_financement = economic_values['valeur_economique_financement_conv']

    # Calculer le profit à l'achat en dollars (comme dans la section "prix à payer")
    prix_vente = clean_monetary_value(property_data.get('prix_vente', 0))
    profit_achat_equite = valeur_economique_financement - prix_vente
    
    # Financement initial
    initial_financing = calculate_initial_financing_with_bank_rules(
        property_data, loan_type, conventional_rate
    )
    
    # Scénarios de refinancement
    scenarios = {}
    
    # Scénario conservateur (1 an, 0% appréciation, just stabilisation)
    scenarios['conservateur'] = calculate_refinancing_scenario(
        property_data, loan_type, 
        years_after_purchase=1, 
        appreciation_rate=0.00, 
        stabilisation_improvements=0,
        conventional_rate=conventional_rate
    )
    
    # Scénario réaliste (1 an, 2% appréciation)
    scenarios['realiste'] = calculate_refinancing_scenario(
        property_data, loan_type, 
        years_after_purchase=1, 
        appreciation_rate=0.02, 
        stabilisation_improvements=0,
        conventional_rate=conventional_rate
    )
    
    # Scénario optimiste (1 an, 3% appréciation + améliorations)
    scenarios['optimiste'] = calculate_refinancing_scenario(
        property_data, loan_type, 
        years_after_purchase=1, 
        appreciation_rate=0.03, 
        stabilisation_improvements=20000,  # 20k$ d'améliorations
        conventional_rate=conventional_rate
    )
    
    return {
        'initial_financing': initial_financing,
        'scenarios_refinancement': scenarios,
        'profit_achat_equite': profit_achat_equite,
        'profit_immediatement_disponible': 0,  # Jamais de cash immédiat
        'profit_potentiel_1_an': {
            'conservateur': scenarios['conservateur']['profit_realise_cash'],
            'realiste': scenarios['realiste']['profit_realise_cash'],
            'optimiste': scenarios['optimiste']['profit_realise_cash']
        }
    }
