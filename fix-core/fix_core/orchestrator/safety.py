"""
Safety Interruption Layer — mandatory override for dangerous conditions.

Scans user input and observation text for patterns indicating immediate physical danger.
When a critical alert fires, the session flow is interrupted and the alert is returned
to the frontend BEFORE any diagnostic response.  The user must acknowledge before
continuing.

Alert levels:
  critical — stop immediately, do not operate the vehicle
  warning  — proceed with caution, address soon
"""
from __future__ import annotations

import re

# SafetyAlert is the Pydantic model from fix_core.models.safety.
# No dataclass duplicate — this is the single canonical representation.
from fix_core.models.safety import SafetyAlert  # noqa: F401  (re-exported)


# ── Pattern definitions ──────────────────────────────────────────────────────
# Each entry: (compiled_regex, level, message, recommended_action)
_PATTERNS: list[tuple[re.Pattern, str, str, str]] = [
    # Critical: fuel / fire hazards
    (
        re.compile(
            r"(fuel|gas|gasoline|petrol)\s*(is\s+)?(leak(ing)?|smell(ing)?|spill(ing)?|drip(ping)?|puddle|vapor)",
            re.IGNORECASE,
        ),
        "critical",
        "Fuel leak or vapor detected.",
        (
            "Turn off the engine immediately. Do not restart it. "
            "Do not smoke or use any ignition source near the vehicle. "
            "Move away and call for roadside assistance."
        ),
    ),
    (
        re.compile(
            r"(smell(s)?|smelling|smells like)\s+(gas|gasoline|fuel|petrol|burning fuel)",
            re.IGNORECASE,
        ),
        "critical",
        "Fuel odor detected.",
        (
            "Stop the vehicle immediately in a safe location. "
            "Turn off the engine. Do not restart. "
            "Exit the vehicle and keep bystanders away. Call for assistance."
        ),
    ),
    (
        re.compile(r"(fire|flames?|burning)\s*(is\s+|are\s+)?(coming|from|under|in|on)", re.IGNORECASE),
        "critical",
        "Fire or flames reported.",
        (
            "Evacuate the vehicle immediately. Move at least 100 feet away. "
            "Call emergency services (911) immediately. Do not re-enter the vehicle."
        ),
    ),
    (
        re.compile(r"(on fire|caught fire|engine fire|car fire|truck fire)", re.IGNORECASE),
        "critical",
        "Vehicle fire reported.",
        "Evacuate immediately. Call 911. Do not re-enter.",
    ),
    # Critical: electrical fire / smoke from wiring
    (
        re.compile(
            r"(smoke|burning smell).{0,40}(wir(ing|e)|electrical|fuse|circuit|harness)",
            re.IGNORECASE,
        ),
        "critical",
        "Electrical smoke or burning wiring detected.",
        (
            "Turn off the ignition and disconnect the battery if safe to do so. "
            "Do not restart. Have the vehicle towed — do not drive it."
        ),
    ),
    (
        re.compile(
            r"(wir(ing|e)|electrical|fuse|circuit).{0,40}(smoke|burning|melting|sparking)",
            re.IGNORECASE,
        ),
        "critical",
        "Electrical burning or sparking detected.",
        (
            "Turn off the ignition immediately. Disconnect the battery if safe. "
            "Do not restart — have the vehicle towed."
        ),
    ),
    # Critical: severe overheating with steam
    (
        re.compile(
            r"(steam|smoke).{0,30}(overheat|hood|radiator|engine)|"
            r"(overheat|radiator|hood).{0,30}(steam|smoke)",
            re.IGNORECASE,
        ),
        "critical",
        "Severe overheating with steam or smoke detected.",
        (
            "Stop driving immediately. Pull over safely and turn off the engine. "
            "Do NOT open the radiator cap — scalding coolant can cause severe burns. "
            "Allow the engine to cool for at least 30 minutes before inspecting."
        ),
    ),
    # Critical: brake failure
    (
        re.compile(
            r"(brake(s)?|braking).{0,30}(fail(ed|ing|ure)?|no brakes|not working|gone|lost)",
            re.IGNORECASE,
        ),
        "critical",
        "Brake failure or total loss of braking reported.",
        (
            "Do not drive the vehicle. If you are currently driving: downshift to slow down, "
            "use the parking/emergency brake gently, and safely bring the vehicle to a stop. "
            "Have the vehicle towed — do not drive until brakes are inspected and repaired."
        ),
    ),
    # Warning: overheating without steam
    (
        re.compile(
            r"(overheat(ing)?|temperature.{0,20}(high|warning|light|gauge|red)|"
            r"(temp|coolant).{0,20}(high|warning|hot|boiling|light))",
            re.IGNORECASE,
        ),
        "warning",
        "Engine overheating detected.",
        (
            "Pull over when safe and let the engine cool. "
            "Check coolant level only when the engine is cold. "
            "Continuing to drive while overheating can cause severe engine damage."
        ),
    ),
    # Warning: brake noise while driving
    (
        re.compile(
            r"(brake(s)?|braking).{0,40}(grind(ing)?|metal.{0,10}metal|screeching|no pad)",
            re.IGNORECASE,
        ),
        "warning",
        "Severe brake wear or grinding detected.",
        (
            "Avoid hard braking. Have the brakes inspected immediately — "
            "metal-on-metal grinding means pads are fully worn and rotors may be damaged."
        ),
    ),
    # Warning: steering loss
    (
        re.compile(
            r"(steering|wheel).{0,30}(no control|can't steer|lost control|lock(ed|ing) up)",
            re.IGNORECASE,
        ),
        "warning",
        "Steering control issue detected.",
        (
            "Reduce speed carefully. Do not drive at highway speeds until this is diagnosed. "
            "Have the steering system inspected immediately."
        ),
    ),

    # ── Heavy equipment safety patterns (Phase 11) ───────────────────────────

    # Critical: high-pressure hydraulic line rupture / injection risk
    (
        re.compile(
            r"(hydraulic).{0,40}(burst(ing)?|rupt(ure|ured)|blow(n|ing)|"
            r"spray(ing)?|high.pressure.{0,20}leak|injection|pinhole)",
            re.IGNORECASE,
        ),
        "critical",
        "High-pressure hydraulic line failure detected.",
        (
            "STOP the machine immediately and lower all implements to the ground. "
            "Do NOT touch the suspected leak with bare hands — hydraulic fluid at 3000+ PSI "
            "can penetrate skin without a visible wound (hydraulic injection injury). "
            "Use cardboard or paper to locate the spray, then seek medical attention "
            "AND call a qualified technician. Do not restart the machine."
        ),
    ),
    # Critical: uncontrolled machine movement
    (
        re.compile(
            r"(machine|equipment|excavator|dozer|loader|crane|skid.steer).{0,40}"
            r"(moving|moved|rolling|drifting|creeping).{0,30}"
            r"(on its own|by itself|uncontrolled|won.t stop|can.t stop)",
            re.IGNORECASE,
        ),
        "critical",
        "Uncontrolled machine movement detected.",
        (
            "Set the parking brake immediately. Lower all implements fully to the ground. "
            "Do not attempt to drive the machine. Chock the tracks or wheels with blocks "
            "to prevent further movement. Keep all personnel clear of the machine's path. "
            "Do not operate until the brake and drive system are inspected."
        ),
    ),
    (
        re.compile(
            r"(brake(s)?|park(ing)?.brake).{0,40}"
            r"(fail(ed|ing|ure)?|not.holding|won.t.hold|released.by.itself|no.brakes)",
            re.IGNORECASE,
        ),
        "critical",
        "Equipment brake failure or brake not holding.",
        (
            "Do not move the machine. Apply any available secondary or emergency brake. "
            "Lower all implements fully to the ground. "
            "Chock the tracks or wheels immediately with blocks or ground engagement. "
            "Keep all personnel away from the machine's downhill side. "
            "Do not attempt operation until brakes are repaired and tested."
        ),
    ),
    # Critical: fuel leak near hot diesel engine
    (
        re.compile(
            r"(diesel|fuel).{0,30}(leak(ing)?|drip(ping)?|spray(ing)?|smell(ing)?).{0,40}"
            r"(hot|engine|exhaust|turbo|manifold)",
            re.IGNORECASE,
        ),
        "critical",
        "Fuel leak near hot engine or exhaust detected.",
        (
            "Shut down the engine immediately. Do not restart. "
            "Diesel fuel on a hot exhaust manifold or turbocharger can ignite. "
            "Move all personnel at least 50 feet away. "
            "Have a fire extinguisher ready and call for assistance before attempting any repair."
        ),
    ),
    # Critical: electrical arc or short on heavy equipment
    (
        re.compile(
            r"(arc(ing)?|spark(ing)?|short.circuit|melting.wire|burning.wire|"
            r"smoke.from.wiring|electrical.fire).{0,40}"
            r"(battery|harness|wiring|electrical|fuse|relay|controller|panel)",
            re.IGNORECASE,
        ),
        "critical",
        "Electrical arc, short circuit, or burning wiring on equipment.",
        (
            "Shut down the machine. Disconnect the battery main switch or pull the main "
            "battery disconnect (if equipped and safely accessible). "
            "Do not restart. Arc faults and wiring fires can spread rapidly in machine "
            "compartments. Have a Class C fire extinguisher available. "
            "Do not attempt repair until the machine is de-energized and cooled."
        ),
    ),
    # Critical: overheating under sustained load — severe
    (
        re.compile(
            r"(machine|engine|equipment).{0,30}(shut(ting)?.down|shut.off|"
            r"protection.mode|derat(e|ing)).{0,30}(overheat|temperature|heat|hot)",
            re.IGNORECASE,
        ),
        "critical",
        "Equipment shut down due to overtemperature.",
        (
            "Allow the engine to cool before inspecting. "
            "Do NOT open the radiator cap — the cooling system is pressurized and the coolant "
            "may be near boiling. Wait at least 30 minutes. "
            "Check that all cooler screens are clear of debris before restarting. "
            "Check coolant level only when cold. Do not operate until the cause is identified."
        ),
    ),
    # Warning: hydraulic fluid low — possible leak
    (
        re.compile(
            r"(hydraulic.fluid|hyd.fluid|hydraulic.oil).{0,30}(low|empty|below.min|level.drop)",
            re.IGNORECASE,
        ),
        "warning",
        "Low hydraulic fluid level detected.",
        (
            "Stop using hydraulic functions until the fluid level is restored. "
            "Running a hydraulic system low on fluid can cause pump cavitation and rapid pump failure. "
            "Before adding fluid, inspect for leaks — low fluid usually indicates a loss somewhere."
        ),
    ),
    # Warning: machine tipping / stability risk
    (
        re.compile(
            r"(tip(ping)?|tip.over|tip.forward|fall(ing)?.over|unstable|stability).{0,30}"
            r"(machine|excavator|crane|loader|lift|boom|load)",
            re.IGNORECASE,
        ),
        "warning",
        "Machine stability or tipping risk detected.",
        (
            "Lower the boom and implements to the lowest safe position immediately. "
            "Do not make any sudden movements. Move slowly to level ground if possible. "
            "Do not operate on slopes or near edges with a raised load until stability is confirmed. "
            "Know your machine's rated capacity and center-of-gravity limits."
        ),
    ),
]


def evaluate_safety(
    texts: list[str],
    existing_safety_flags: list[dict] | None = None,
) -> list[SafetyAlert]:
    """
    Scan one or more text strings for dangerous patterns and return any alerts.

    Args:
        texts:                 List of strings to scan (description, user message, observations).
        existing_safety_flags: Previously fired safety alerts (to avoid duplicates).

    Returns:
        List of new SafetyAlert objects (not including previously raised ones).
    """
    already_raised: set[str] = set()
    if existing_safety_flags:
        already_raised = {f.get("message", "") for f in existing_safety_flags}

    alerts: list[SafetyAlert] = []
    combined = " ".join(texts)

    for pattern, level, message, action in _PATTERNS:
        if message in already_raised:
            continue
        if pattern.search(combined):
            alerts.append(SafetyAlert(level=level, message=message, recommended_action=action))
            already_raised.add(message)

    # Sort: critical first, then warning
    alerts.sort(key=lambda a: 0 if a.level == "critical" else 1)
    return alerts


def has_critical_alert(safety_flags: list[dict]) -> bool:
    """Return True if any stored safety flag is at critical level."""
    return any(f.get("level") == "critical" for f in safety_flags)
