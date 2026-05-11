import math
import pandas as pd
from core import fetch_data

# Słownik czasu tranzytu
TRANSIT_DAYS = {
    "Amsterdam": {"BUS": 1, "FTL": 2}, "Barcelona": {"BUS": 2, "FTL": 4}, "Bazylea": {"BUS": 1, "FTL": 2},
    "Berlin": {"BUS": 1, "FTL": 1}, "Bruksela": {"BUS": 1, "FTL": 2}, "Budapeszt": {"BUS": 1, "FTL": 2},
    "Cannes / Nicea": {"BUS": 2, "FTL": 3}, "Frankfurt nad Menem": {"BUS": 1, "FTL": 2}, "Gdańsk": {"BUS": 1, "FTL": 1},
    "Genewa": {"BUS": 2, "FTL": 2}, "Hamburg": {"BUS": 1, "FTL": 1}, "Hannover": {"BUS": 1, "FTL": 1},
    "Kielce": {"BUS": 1, "FTL": 1}, "Kolonia / Dusseldorf": {"BUS": 1, "FTL": 2}, "Kopenhaga": {"BUS": 1, "FTL": 2},
    "Lipsk": {"BUS": 1, "FTL": 1}, "Liverpool": {"BUS": 2, "FTL": 3}, "Lizbona": {"BUS": 3, "FTL": 5},
    "Londyn": {"BUS": 2, "FTL": 3}, "Lyon": {"BUS": 2, "FTL": 3}, "Madryt": {"BUS": 3, "FTL": 4},
    "Manchester": {"BUS": 2, "FTL": 3}, "Mediolan": {"BUS": 2, "FTL": 2}, "Monachium": {"BUS": 1, "FTL": 2},
    "Norymberga": {"BUS": 1, "FTL": 1}, "Paryż": {"BUS": 1, "FTL": 2}, "Praga": {"BUS": 1, "FTL": 1},
    "Rzym": {"BUS": 2, "FTL": 4}, "Sewilla": {"BUS": 3, "FTL": 5}, "Sofia": {"BUS": 2, "FTL": 3},
    "Sztokholm": {"BUS": 2, "FTL": 3}, "Tuluza": {"BUS": 2, "FTL": 4}, "Warszawa": {"BUS": 1, "FTL": 1}, "Wiedeń": {"BUS": 1, "FTL": 2}
}

def get_all_carrier_rates(city, weight, start_date, end_date, typ_zlecenia="Pełny event"):
    df_cennik = fetch_data("Cennik")
    
    if df_cennik.empty or city not in TRANSIT_DAYS:
        return {}

    df_city = df_cennik[df_cennik['Miasto'] == city]
    
    if df_city.empty:
        return {}

    overlay = max(0, (end_date - start_date).days) if start_date and end_date else 0
    parking_rate = 30
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    is_ch = city in ["Bazylea", "Genewa"]
    
    calculated_rates = {}

    for _, row in df_city.iterrows():
        name = row['Przewoźnik']
        cap = float(row['Ładowność'])
        v_class = row['Klasa']
        v_type = row['Typ']
        
        # Wyliczanie pełnych aut na podstawie wagi
        num_v = max(1, math.ceil(weight / cap)) if cap > 0 else 1
        
        extra = 0
        if is_uk:
            if v_type == 'SQM':
                extra = 517 if v_class == 'BUS' else 776
            else:
                extra = 166
        elif is_ch:
            extra = 166

        if typ_zlecenia == "Pełny event":
            # PEŁNY EVENT: Kółko (Export + Import) + Postoje + Dodatki
            p_total = float(row['Postój']) * overlay
            park_total = parking_rate * overlay
            unit_total = float(row['Export']) + float(row['Import']) + p_total + park_total + extra
        else:
            # TYLKO DOSTAWA: Tylko w 1 stronę (Export) + Dodatki
            unit_total = float(row['Export']) + extra

        # Zawsze mnożymy przez pełne auta (1, 2, 3...) - brak ułamków!
        final_cost = unit_total * num_v

        calculated_rates[name] = {
            "cost": round(final_cost, 2),
            "postoj": float(row['Postój'])
        }
    
    return calculated_rates
