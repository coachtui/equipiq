"""
Cranks but won't start diagnostic tree — boat / marine variant.

Engine rotates when key is held to start, but won't fire and run.
Key marine-specific causes: water in fuel (ethanol absorption + condensation
in boat tanks), unprimed fuel primer bulb on outboards, and carburetor
varnish from storage with ethanol fuel.
"""

CRANK_NO_START_BOAT_HYPOTHESES: dict[str, dict] = {
    "water_in_fuel": {
        "label": "Water in fuel — ethanol-blend fuel absorbed condensation from the tank",
        "prior": 0.28,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel/water separator filter (inline, e.g., Racor)", "notes": "Look for cloudy fuel or visible water layer in the filter bowl. Replace if contaminated."},
            {"name": "Non-ethanol marine gasoline", "notes": "Ethanol-blend fuels (E10/E15) absorb water readily in marine environments and can phase-separate. Use ethanol-free marine fuel when available."},
            {"name": "Isopropyl alcohol fuel additive", "notes": "In small amounts, helps blend absorbed water back into the fuel if contamination is minor"},
        ],
    },
    "primer_bulb_not_primed": {
        "label": "Fuel primer bulb not primed — no fuel at the engine (outboard only)",
        "prior": 0.20,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Fuel primer bulb (outboard style)", "notes": "Squeeze the bulb firmly until it becomes hard — this indicates fuel has reached the carburetor or VST. If the bulb doesn't firm up, there may be a cracked bulb or fuel line issue."},
        ],
    },
    "varnished_carb": {
        "label": "Varnished carburetor from storage with ethanol fuel — jets clogged",
        "prior": 0.18,
        "diy_difficulty": "moderate",
        "parts": [
            {"name": "Marine carburetor cleaner spray", "notes": "Spray carb cleaner into the throat while cranking as a test — if it fires briefly, fuel delivery is the issue"},
            {"name": "Carburetor rebuild kit (marine)", "notes": "Marine carb rebuild kits include all jets, gaskets, and float needle"},
        ],
    },
    "spark_plug_fouled": {
        "label": "Fouled spark plugs — water contamination, oil fouling, or worn electrodes",
        "prior": 0.14,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine spark plugs (correct heat range per engine)", "notes": "Marine engines often run NGK or Champion plugs — confirm spec with owner's manual. Inspect for wet fouling (water/fuel) or carbon fouling."},
        ],
    },
    "choke_or_efi_prime": {
        "label": "Choke not applied on cold start (carbureted) or EFI not primed",
        "prior": 0.10,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "(No parts needed)", "notes": "Carbureted outboards: engage choke fully for cold starts. EFI engines: cycle key ON→OFF 3 times before cranking to prime the fuel rail."},
        ],
    },
    "fuel_line_cracked": {
        "label": "Cracked or kinked fuel line — no fuel reaching engine",
        "prior": 0.06,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Marine fuel line hose (USCG A1 or A2 rated)", "notes": "Only use USCG-approved marine fuel line — automotive hose is not rated for marine immersion. Inspect the full run from tank to engine."},
        ],
    },
    "emergency_stop_engaged": {
        "label": "Emergency stop or additional safety switch engaged / stuck",
        "prior": 0.04,
        "diy_difficulty": "easy",
        "parts": [
            {"name": "Kill switch / safety stop switch", "notes": "Some boats have multiple safety stops. Check all kill switches and verify the lanyard contact is making connection."},
        ],
    },
}

CRANK_NO_START_BOAT_TREE: dict[str, dict] = {
    "start": {
        "question": "Is this an outboard motor or an inboard/sterndrive engine?",
        "options": [
            {
                "match": "outboard",
                "label": "Outboard motor",
                "deltas": {
                    "primer_bulb_not_primed": +0.20,
                    "varnished_carb": +0.05,
                    "water_in_fuel": +0.05,
                },
                "eliminate": [],
                "next_node": "storage_history",
            },
            {
                "match": "inboard_sterndrive",
                "label": "Inboard or sterndrive (engine inside the hull)",
                "deltas": {
                    "primer_bulb_not_primed": -0.20,
                    "water_in_fuel": +0.05,
                    "varnished_carb": +0.05,
                },
                "eliminate": ["primer_bulb_not_primed"],
                "next_node": "storage_history",
            },
        ],
    },

    "storage_history": {
        "question": "Has the boat been in storage, or was ethanol-blend fuel left in the tank over winter?",
        "options": [
            {
                "match": "yes_stored",
                "label": "Yes — stored, especially with ethanol fuel in tank",
                "deltas": {
                    "water_in_fuel": +0.25,
                    "varnished_carb": +0.25,
                    "spark_plug_fouled": +0.10,
                },
                "eliminate": [],
                "next_node": "primer_bulb",
            },
            {
                "match": "running_recently",
                "label": "Was running fine recently — sudden failure",
                "deltas": {
                    "water_in_fuel": +0.10,
                    "primer_bulb_not_primed": +0.10,
                    "varnished_carb": -0.10,
                    "choke_or_efi_prime": +0.05,
                },
                "eliminate": [],
                "next_node": "primer_bulb",
            },
        ],
    },

    "primer_bulb": {
        "question": "For outboards: have you squeezed the primer bulb until it's firm? For inboards: is there fuel visible in the filter bowl?",
        "options": [
            {
                "match": "bulb_soft_not_primed",
                "label": "Outboard: bulb is still soft after squeezing — not priming up",
                "deltas": {
                    "primer_bulb_not_primed": +0.40,
                    "fuel_line_cracked": +0.20,
                    "water_in_fuel": -0.05,
                },
                "eliminate": [],
                "next_node": "fuel_filter_check",
            },
            {
                "match": "bulb_firm_primed",
                "label": "Outboard: bulb firms up normally. Or inboard: fuel is present at filter",
                "deltas": {
                    "primer_bulb_not_primed": -0.20,
                    "water_in_fuel": +0.10,
                    "varnished_carb": +0.10,
                    "spark_plug_fouled": +0.05,
                },
                "eliminate": [],
                "next_node": "fuel_filter_check",
            },
            {
                "match": "not_applicable",
                "label": "Not applicable (EFI / no primer bulb)",
                "deltas": {
                    "primer_bulb_not_primed": -0.20,
                    "choke_or_efi_prime": +0.10,
                },
                "eliminate": ["primer_bulb_not_primed"],
                "next_node": "fuel_filter_check",
            },
        ],
    },

    "fuel_filter_check": {
        "question": "Check the fuel/water separator filter bowl. Is the fuel clear, or is it cloudy, milky, or have a water layer at the bottom?",
        "options": [
            {
                "match": "cloudy_or_water",
                "label": "Cloudy, milky, or visible water layer",
                "deltas": {
                    "water_in_fuel": +0.40,
                    "varnished_carb": -0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "fuel_clear",
                "label": "Fuel looks clear and clean",
                "deltas": {
                    "water_in_fuel": -0.20,
                    "varnished_carb": +0.10,
                    "spark_plug_fouled": +0.10,
                    "choke_or_efi_prime": +0.05,
                },
                "eliminate": [],
                "next_node": None,
            },
            {
                "match": "no_separator",
                "label": "No fuel/water separator installed",
                "deltas": {
                    "water_in_fuel": +0.10,
                },
                "eliminate": [],
                "next_node": None,
            },
        ],
    },
}

CRANK_NO_START_BOAT_CONTEXT_PRIORS: dict = {
    "climate": {
        "cold": {"choke_or_efi_prime": +0.10, "spark_plug_fouled": +0.06},
    },
    "saltwater_use": {
        "yes": {"spark_plug_fouled": +0.06, "fuel_line_cracked": +0.06},
    },
    "storage_time": {
        "weeks": {"varnished_carb": +0.08, "water_in_fuel": +0.06},
        "months": {"varnished_carb": +0.15, "water_in_fuel": +0.10, "spark_plug_fouled": +0.06},
        "season": {"varnished_carb": +0.18, "water_in_fuel": +0.12, "spark_plug_fouled": +0.08},
    },
    "first_start_of_season": {
        "yes": {"varnished_carb": +0.12, "water_in_fuel": +0.08, "primer_bulb_not_primed": +0.08, "emergency_stop_engaged": +0.06},
    },
}

CRANK_NO_START_BOAT_POST_DIAGNOSIS: list[str] = [
    "After starting, let the engine warm up fully in the water and confirm the tell-tale (pee hole) is flowing normally — starting issues sometimes mask a cooling problem.",
    "Replace the primer bulb at the same time as any fuel system service — UV and ethanol degrade them annually.",
]
