import math
from datetime import date

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

# Skrócona baza stawek (dla przykładu - wklej tu pełne dane z pliku HTML dla wszystkich przewoźników)
RATES = {
    "WŁASNY SQM BUS": { 
        "postoj": 30, "cap": 1000, "type": 'SQM', "vClass": 'BUS', "dniowki": {}, 
        "exp": {"Amsterdam":373.8, "Barcelona":1106.4, "Berlin":129, "Hannover":226.2, "Londyn":352.8},
        "imp": {"Amsterdam":373.8, "Barcelona":1106.4, "Berlin":129, "Hannover":226.2, "Londyn":352.8}
    },
    "WŁASNY SQM FTL": { 
        "postoj": 150, "cap": 10500, "type": 'SQM', "vClass": 'FTL', 
        "dniowki": {"Amsterdam":680, "Barcelona":1360, "Berlin":340, "Hannover":340, "Londyn":1020},
        "exp": {"Amsterdam":874.8, "Barcelona":2156.4, "Berlin":277.2, "Hannover":540, "Londyn":924},
        "imp": {"Amsterdam":874.8, "Barcelona":2156.4, "Berlin":277.2, "Hannover":540, "Londyn":924}
    }
    # Uzupełnij o resztę słownika RATES z JavaScript...
}

def calculate_vantage_price(city, weight, start_date, end_date, mode="full"):
    """
    Kalkuluje zestawienie opcji transportowych na podstawie podanych kryteriów.
    Zwraca posortowaną listę słowników z wycenami.
    """
    if city not in TRANSIT_DAYS:
        return []

    # Obliczanie dni postoju (overlay)
    overlay = 0
    if start_date and end_date:
        overlay = max(0, (end_date - start_date).days)
    
    parking_daily_rate = 30
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    is_ch = city in ["Bazylea", "Genewa"]
    
    results = []

    for carrier_name, c in RATES.items():
        if city not in c.get("exp", {}):
            continue

        num_vehicles = math.ceil(weight / c["cap"]) if c["cap"] > 0 else 1
        num_vehicles = max(1, num_vehicles)

        exp_cost = c["exp"][city]
        imp_cost = c["imp"][city]
        dniowka = c.get("dniowki", {}).get(city, 0)
        p_total = c["postoj"] * overlay
        parking_total = parking_daily_rate * overlay

        extra_cost = 0
        
        # Logika dodatków celnych / promowych
        if is_uk:
            if c["type"] == 'SQM':
                extra_cost = (332 + 166 + 19) if c["vClass"] == 'BUS' else (522 + 166 + 19 + 69)
            else:
                extra_cost = 166
        elif is_ch:
            extra_cost = 166

        total_for_one = exp_cost + imp_cost + dniowka + p_total + extra_cost + parking_total
        
        if mode == "full":
            final_cost = total_for_one * num_vehicles
        else: # proporcjonalny (doładunek)
            final_cost = (total_for_one / c["cap"]) * weight

        results.append({
            "carrier": carrier_name,
            "cost": final_cost,
            "vClass": c["vClass"],
            "count": num_vehicles
        })

    # Sortowanie od najtańszego
    results.sort(key=lambda x: x["cost"])
    return results
