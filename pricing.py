import math

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

# Skrócona baza stawek - skopiowałem przykładowe z Twojego pliku, dodaj resztę w miarę potrzeb
RATES = {
    "WŁASNY SQM BUS": { "postoj": 30, "cap": 1000, "type": 'SQM', "vClass": 'BUS', "exp": {"Amsterdam":373.8,"Barcelona":1106.4,"Berlin":129,"Hannover":226.2,"Londyn":352.8,"Paryż":577.8}, "imp": {"Amsterdam":373.8,"Barcelona":1106.4,"Berlin":129,"Hannover":226.2,"Londyn":352.8,"Paryż":577.8} },
    "WŁASNY SQM SOLO": { "postoj": 150, "cap": 5500, "type": 'SQM', "vClass": 'SOLO', "exp": {"Amsterdam":626.4,"Barcelona":1638.6,"Berlin":202.2,"Hannover":388.2,"Londyn":669.6,"Paryż":948.6}, "imp": {"Amsterdam":626.4,"Barcelona":1638.6,"Berlin":202.2,"Hannover":388.2,"Londyn":669.6,"Paryż":948.6} },
    "WŁASNY SQM FTL": { "postoj": 150, "cap": 10500, "type": 'SQM', "vClass": 'FTL', "exp": {"Amsterdam":874.8,"Barcelona":2156.4,"Berlin":277.2,"Hannover":540, "Londyn":924, "Paryż":1292.4}, "imp": {"Amsterdam":874.8,"Barcelona":2156.4,"Berlin":277.2,"Hannover":540, "Londyn":924, "Paryż":1292.4} },
    "PREMIUM TRANSPORT": { "postoj": 330, "cap": 10500, "type": 'EXT', "vClass": 'FTL', "exp": {"Amsterdam":2300,"Barcelona":4300,"Berlin":1200,"Hannover":1500,"Londyn":5200,"Paryż":2990}, "imp": {"Amsterdam":2300,"Barcelona":4300,"Berlin":1200,"Hannover":1500,"Londyn":5200,"Paryż":2990} },
    "BLM EXPRESS SOLO": { "postoj": 250, "cap": 3500, "type": 'EXT', "vClass": 'SOLO', "exp": {"Amsterdam":1250,"Barcelona":2750,"Berlin":450,"Hannover":750,"Londyn":2250,"Paryż":1700}, "imp": {"Amsterdam":1250,"Barcelona":2750,"Berlin":450,"Hannover":750,"Londyn":1550,"Paryż":1700} },
    "BLM EXPRESS FTL": { "postoj": 400, "cap": 10500, "type": 'EXT', "vClass": 'FTL', "exp": {"Amsterdam":1700,"Barcelona":3950,"Berlin":800,"Hannover":1050,"Londyn":3050,"Paryż":2450}, "imp": {"Amsterdam":1700,"Barcelona":3500,"Berlin":700,"Hannover":900,"Londyn":2800,"Paryż":2200} }
}

def get_all_carrier_rates(city, weight, start_date, end_date, mode="full"):
    if city not in TRANSIT_DAYS:
        return {}

    overlay = max(0, (end_date - start_date).days) if start_date and end_date else 0
    parking_rate = 30
    is_uk = city in ["Londyn", "Liverpool", "Manchester"]
    is_ch = city in ["Bazylea", "Genewa"]
    
    calculated_rates = {}

    for name, c in RATES.items():
        if city not in c["exp"]: 
            continue
        
        num_v = max(1, math.ceil(weight / c["cap"]))
        p_total = c["postoj"] * overlay
        park_total = parking_rate * overlay
        extra = 0
        
        if is_uk:
            extra = (517 if c["vClass"] == 'BUS' else 776) if c["type"] == 'SQM' else 166
        elif is_ch:
            extra = 166

        unit_total = c["exp"][city] + c["imp"][city] + p_total + park_total + extra
        final_cost = unit_total * num_v if mode == "full" else (unit_total / c["cap"]) * weight
        
        calculated_rates[name] = round(final_cost, 2)
    
    return calculated_rates
