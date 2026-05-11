import math
import pandas as pd
from core import fetch_data

# Statyczny słownik czasów tranzytu (można też przenieść do Sheets w przyszłości)
TRANSIT_DAYS = {
    "Amsterdam": {"BUS": 1, "FTL": 2}, "Barcelona": {"BUS": 2, "FTL": 4}, "Berlin": {"BUS": 1, "FTL": 1},
    "Hannover": {"BUS": 1, "FTL": 1}, "Londyn": {"BUS": 2, "FTL": 3}, "Paryż": {"BUS": 1, "FTL": 2}
    # ... uzupełnij pozostałe miasta ...
}

def get_all_carrier_rates(city, weight, start_date, end_date, mode="full"):
    """Pobiera stawki z Google Sheets i oblicza koszty na żywo."""
    
    # 1. Pobranie danych z nowej zakładki 'Cennik'
    df_cennik = fetch_data("Cennik")
    
    if df_cennik.empty or city not in TRANSIT_DAYS:
        return {}

    # 2. Filtrowanie cennika pod konkretne miasto
    df_city = df_cennik[df_cennik['Miasto'] == city]
    
    if df_city.empty:
        return {}

    overlay = max(0, (end_date - start_date).days) if start_date and end_date else 0
    parking_rate = 30
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    is_ch = city in ["Bazylea", "Genewa"]
    
    calculated_rates = {}

    # 3. Iteracja po przewoźnikach dostępnych dla tego miasta
    for _, row in df_city.iterrows():
        name = row['Przewoźnik']
        cap = float(row['Ładowność'])
        v_class = row['Klasa']
        v_type = row['Typ']
        
        num_v = max(1, math.ceil(weight / cap)) if cap > 0 else 1
        p_total = float(row['Postój']) * overlay
        park_total = parking_rate * overlay
        
        # Dodatki (Promy / Cło)
        extra = 0
        if is_uk:
            if v_type == 'SQM':
                extra = 517 if v_class == 'BUS' else 776
            else:
                extra = 166
        elif is_ch:
            extra = 166

        # Sumowanie kosztu jednostkowego (Kółko + Postoje + Opłaty)
        unit_total = float(row['Export']) + float(row['Import']) + p_total + park_total + extra
        
        # Finalna wycena (Dedyk vs Doładunek)
        if mode == "full":
            final_cost = unit_total * num_v
        else:
            final_cost = (unit_total / cap) * weight
            
        calculated_rates[name] = round(final_cost, 2)
    
    return calculated_rates
