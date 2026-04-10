from fix_core.trees.no_crank import NO_CRANK_TREE, NO_CRANK_HYPOTHESES, NO_CRANK_CONTEXT_PRIORS, NO_CRANK_POST_DIAGNOSIS
from fix_core.trees.crank_no_start import CRANK_NO_START_TREE, CRANK_NO_START_HYPOTHESES, CRANK_NO_START_CONTEXT_PRIORS, CRANK_NO_START_POST_DIAGNOSIS
from fix_core.trees.loss_of_power import LOSS_OF_POWER_TREE, LOSS_OF_POWER_HYPOTHESES, LOSS_OF_POWER_CONTEXT_PRIORS, LOSS_OF_POWER_POST_DIAGNOSIS
from fix_core.trees.rough_idle import ROUGH_IDLE_TREE, ROUGH_IDLE_HYPOTHESES, ROUGH_IDLE_CONTEXT_PRIORS, ROUGH_IDLE_POST_DIAGNOSIS
from fix_core.trees.strange_noise import STRANGE_NOISE_TREE, STRANGE_NOISE_HYPOTHESES, STRANGE_NOISE_CONTEXT_PRIORS, STRANGE_NOISE_POST_DIAGNOSIS
from fix_core.trees.visible_leak import VISIBLE_LEAK_TREE, VISIBLE_LEAK_HYPOTHESES, VISIBLE_LEAK_CONTEXT_PRIORS, VISIBLE_LEAK_POST_DIAGNOSIS
from fix_core.trees.overheating import OVERHEATING_TREE, OVERHEATING_HYPOTHESES, OVERHEATING_CONTEXT_PRIORS, OVERHEATING_POST_DIAGNOSIS
from fix_core.trees.check_engine_light import CHECK_ENGINE_LIGHT_TREE, CHECK_ENGINE_LIGHT_HYPOTHESES, CHECK_ENGINE_LIGHT_CONTEXT_PRIORS, CHECK_ENGINE_LIGHT_POST_DIAGNOSIS

from fix_core.trees.no_crank_motorcycle import NO_CRANK_MOTORCYCLE_TREE, NO_CRANK_MOTORCYCLE_HYPOTHESES, NO_CRANK_MOTORCYCLE_CONTEXT_PRIORS, NO_CRANK_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_motorcycle import CRANK_NO_START_MOTORCYCLE_TREE, CRANK_NO_START_MOTORCYCLE_HYPOTHESES, CRANK_NO_START_MOTORCYCLE_CONTEXT_PRIORS, CRANK_NO_START_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.rough_idle_motorcycle import ROUGH_IDLE_MOTORCYCLE_TREE, ROUGH_IDLE_MOTORCYCLE_HYPOTHESES, ROUGH_IDLE_MOTORCYCLE_CONTEXT_PRIORS, ROUGH_IDLE_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_motorcycle import LOSS_OF_POWER_MOTORCYCLE_TREE, LOSS_OF_POWER_MOTORCYCLE_HYPOTHESES, LOSS_OF_POWER_MOTORCYCLE_CONTEXT_PRIORS, LOSS_OF_POWER_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.strange_noise_motorcycle import STRANGE_NOISE_MOTORCYCLE_TREE, STRANGE_NOISE_MOTORCYCLE_HYPOTHESES, STRANGE_NOISE_MOTORCYCLE_CONTEXT_PRIORS, STRANGE_NOISE_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.visible_leak_motorcycle import VISIBLE_LEAK_MOTORCYCLE_TREE, VISIBLE_LEAK_MOTORCYCLE_HYPOTHESES, VISIBLE_LEAK_MOTORCYCLE_CONTEXT_PRIORS, VISIBLE_LEAK_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.overheating_motorcycle import OVERHEATING_MOTORCYCLE_TREE, OVERHEATING_MOTORCYCLE_HYPOTHESES, OVERHEATING_MOTORCYCLE_CONTEXT_PRIORS, OVERHEATING_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.check_engine_light_motorcycle import CHECK_ENGINE_LIGHT_MOTORCYCLE_TREE, CHECK_ENGINE_LIGHT_MOTORCYCLE_HYPOTHESES, CHECK_ENGINE_LIGHT_MOTORCYCLE_CONTEXT_PRIORS, CHECK_ENGINE_LIGHT_MOTORCYCLE_POST_DIAGNOSIS

from fix_core.trees.no_crank_generator import NO_CRANK_GENERATOR_TREE, NO_CRANK_GENERATOR_HYPOTHESES, NO_CRANK_GENERATOR_CONTEXT_PRIORS, NO_CRANK_GENERATOR_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_generator import CRANK_NO_START_GENERATOR_TREE, CRANK_NO_START_GENERATOR_HYPOTHESES, CRANK_NO_START_GENERATOR_CONTEXT_PRIORS, CRANK_NO_START_GENERATOR_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_generator import LOSS_OF_POWER_GENERATOR_TREE, LOSS_OF_POWER_GENERATOR_HYPOTHESES, LOSS_OF_POWER_GENERATOR_CONTEXT_PRIORS, LOSS_OF_POWER_GENERATOR_POST_DIAGNOSIS
from fix_core.trees.rough_idle_generator import ROUGH_IDLE_GENERATOR_TREE, ROUGH_IDLE_GENERATOR_HYPOTHESES, ROUGH_IDLE_GENERATOR_CONTEXT_PRIORS, ROUGH_IDLE_GENERATOR_POST_DIAGNOSIS
from fix_core.trees.strange_noise_generator import STRANGE_NOISE_GENERATOR_TREE, STRANGE_NOISE_GENERATOR_HYPOTHESES, STRANGE_NOISE_GENERATOR_CONTEXT_PRIORS, STRANGE_NOISE_GENERATOR_POST_DIAGNOSIS
from fix_core.trees.visible_leak_generator import VISIBLE_LEAK_GENERATOR_TREE, VISIBLE_LEAK_GENERATOR_HYPOTHESES, VISIBLE_LEAK_GENERATOR_CONTEXT_PRIORS, VISIBLE_LEAK_GENERATOR_POST_DIAGNOSIS

from fix_core.trees.no_crank_truck import NO_CRANK_TRUCK_TREE, NO_CRANK_TRUCK_HYPOTHESES, NO_CRANK_TRUCK_CONTEXT_PRIORS, NO_CRANK_TRUCK_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_truck import CRANK_NO_START_TRUCK_TREE, CRANK_NO_START_TRUCK_HYPOTHESES, CRANK_NO_START_TRUCK_CONTEXT_PRIORS, CRANK_NO_START_TRUCK_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_truck import LOSS_OF_POWER_TRUCK_TREE, LOSS_OF_POWER_TRUCK_HYPOTHESES, LOSS_OF_POWER_TRUCK_CONTEXT_PRIORS, LOSS_OF_POWER_TRUCK_POST_DIAGNOSIS
from fix_core.trees.rough_idle_truck import ROUGH_IDLE_TRUCK_TREE, ROUGH_IDLE_TRUCK_HYPOTHESES, ROUGH_IDLE_TRUCK_CONTEXT_PRIORS, ROUGH_IDLE_TRUCK_POST_DIAGNOSIS
from fix_core.trees.strange_noise_truck import STRANGE_NOISE_TRUCK_TREE, STRANGE_NOISE_TRUCK_HYPOTHESES, STRANGE_NOISE_TRUCK_CONTEXT_PRIORS, STRANGE_NOISE_TRUCK_POST_DIAGNOSIS
from fix_core.trees.overheating_truck import OVERHEATING_TRUCK_TREE, OVERHEATING_TRUCK_HYPOTHESES, OVERHEATING_TRUCK_CONTEXT_PRIORS, OVERHEATING_TRUCK_POST_DIAGNOSIS
from fix_core.trees.check_engine_light_truck import CHECK_ENGINE_LIGHT_TRUCK_TREE, CHECK_ENGINE_LIGHT_TRUCK_HYPOTHESES, CHECK_ENGINE_LIGHT_TRUCK_CONTEXT_PRIORS, CHECK_ENGINE_LIGHT_TRUCK_POST_DIAGNOSIS

from fix_core.trees.no_crank_boat import NO_CRANK_BOAT_TREE, NO_CRANK_BOAT_HYPOTHESES, NO_CRANK_BOAT_CONTEXT_PRIORS, NO_CRANK_BOAT_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_boat import CRANK_NO_START_BOAT_TREE, CRANK_NO_START_BOAT_HYPOTHESES, CRANK_NO_START_BOAT_CONTEXT_PRIORS, CRANK_NO_START_BOAT_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_boat import LOSS_OF_POWER_BOAT_TREE, LOSS_OF_POWER_BOAT_HYPOTHESES, LOSS_OF_POWER_BOAT_CONTEXT_PRIORS, LOSS_OF_POWER_BOAT_POST_DIAGNOSIS
from fix_core.trees.rough_idle_boat import ROUGH_IDLE_BOAT_TREE, ROUGH_IDLE_BOAT_HYPOTHESES, ROUGH_IDLE_BOAT_CONTEXT_PRIORS, ROUGH_IDLE_BOAT_POST_DIAGNOSIS
from fix_core.trees.strange_noise_boat import STRANGE_NOISE_BOAT_TREE, STRANGE_NOISE_BOAT_HYPOTHESES, STRANGE_NOISE_BOAT_CONTEXT_PRIORS, STRANGE_NOISE_BOAT_POST_DIAGNOSIS
from fix_core.trees.visible_leak_boat import VISIBLE_LEAK_BOAT_TREE, VISIBLE_LEAK_BOAT_HYPOTHESES, VISIBLE_LEAK_BOAT_CONTEXT_PRIORS, VISIBLE_LEAK_BOAT_POST_DIAGNOSIS
from fix_core.trees.overheating_boat import OVERHEATING_BOAT_TREE, OVERHEATING_BOAT_HYPOTHESES, OVERHEATING_BOAT_CONTEXT_PRIORS, OVERHEATING_BOAT_POST_DIAGNOSIS

from fix_core.trees.no_crank_atv import NO_CRANK_ATV_TREE, NO_CRANK_ATV_HYPOTHESES, NO_CRANK_ATV_CONTEXT_PRIORS, NO_CRANK_ATV_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_atv import CRANK_NO_START_ATV_TREE, CRANK_NO_START_ATV_HYPOTHESES, CRANK_NO_START_ATV_CONTEXT_PRIORS, CRANK_NO_START_ATV_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_atv import LOSS_OF_POWER_ATV_TREE, LOSS_OF_POWER_ATV_HYPOTHESES, LOSS_OF_POWER_ATV_CONTEXT_PRIORS, LOSS_OF_POWER_ATV_POST_DIAGNOSIS
from fix_core.trees.rough_idle_atv import ROUGH_IDLE_ATV_TREE, ROUGH_IDLE_ATV_HYPOTHESES, ROUGH_IDLE_ATV_CONTEXT_PRIORS, ROUGH_IDLE_ATV_POST_DIAGNOSIS
from fix_core.trees.strange_noise_atv import STRANGE_NOISE_ATV_TREE, STRANGE_NOISE_ATV_HYPOTHESES, STRANGE_NOISE_ATV_CONTEXT_PRIORS, STRANGE_NOISE_ATV_POST_DIAGNOSIS
from fix_core.trees.visible_leak_atv import VISIBLE_LEAK_ATV_TREE, VISIBLE_LEAK_ATV_HYPOTHESES, VISIBLE_LEAK_ATV_CONTEXT_PRIORS, VISIBLE_LEAK_ATV_POST_DIAGNOSIS
from fix_core.trees.overheating_atv import OVERHEATING_ATV_TREE, OVERHEATING_ATV_HYPOTHESES, OVERHEATING_ATV_CONTEXT_PRIORS, OVERHEATING_ATV_POST_DIAGNOSIS

from fix_core.trees.no_crank_pwc import NO_CRANK_PWC_TREE, NO_CRANK_PWC_HYPOTHESES, NO_CRANK_PWC_CONTEXT_PRIORS, NO_CRANK_PWC_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_pwc import CRANK_NO_START_PWC_TREE, CRANK_NO_START_PWC_HYPOTHESES, CRANK_NO_START_PWC_CONTEXT_PRIORS, CRANK_NO_START_PWC_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_pwc import LOSS_OF_POWER_PWC_TREE, LOSS_OF_POWER_PWC_HYPOTHESES, LOSS_OF_POWER_PWC_CONTEXT_PRIORS, LOSS_OF_POWER_PWC_POST_DIAGNOSIS
from fix_core.trees.strange_noise_pwc import STRANGE_NOISE_PWC_TREE, STRANGE_NOISE_PWC_HYPOTHESES, STRANGE_NOISE_PWC_CONTEXT_PRIORS, STRANGE_NOISE_PWC_POST_DIAGNOSIS
from fix_core.trees.overheating_pwc import OVERHEATING_PWC_TREE, OVERHEATING_PWC_HYPOTHESES, OVERHEATING_PWC_CONTEXT_PRIORS, OVERHEATING_PWC_POST_DIAGNOSIS
from fix_core.trees.visible_leak_pwc import VISIBLE_LEAK_PWC_TREE, VISIBLE_LEAK_PWC_HYPOTHESES, VISIBLE_LEAK_PWC_CONTEXT_PRIORS, VISIBLE_LEAK_PWC_POST_DIAGNOSIS

# Phase 8 — new symptom systems (base / car trees)
from fix_core.trees.brakes import BRAKES_TREE, BRAKES_HYPOTHESES, BRAKES_CONTEXT_PRIORS, BRAKES_POST_DIAGNOSIS
from fix_core.trees.transmission import TRANSMISSION_TREE, TRANSMISSION_HYPOTHESES, TRANSMISSION_CONTEXT_PRIORS, TRANSMISSION_POST_DIAGNOSIS
from fix_core.trees.suspension import SUSPENSION_TREE, SUSPENSION_HYPOTHESES, SUSPENSION_CONTEXT_PRIORS, SUSPENSION_POST_DIAGNOSIS
from fix_core.trees.hvac import HVAC_TREE, HVAC_HYPOTHESES, HVAC_CONTEXT_PRIORS, HVAC_POST_DIAGNOSIS

# Phase 8C — brakes variants
from fix_core.trees.brakes_truck import BRAKES_TRUCK_TREE, BRAKES_TRUCK_HYPOTHESES, BRAKES_TRUCK_CONTEXT_PRIORS, BRAKES_TRUCK_POST_DIAGNOSIS
from fix_core.trees.brakes_motorcycle import BRAKES_MOTORCYCLE_TREE, BRAKES_MOTORCYCLE_HYPOTHESES, BRAKES_MOTORCYCLE_CONTEXT_PRIORS, BRAKES_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.brakes_atv import BRAKES_ATV_TREE, BRAKES_ATV_HYPOTHESES, BRAKES_ATV_CONTEXT_PRIORS, BRAKES_ATV_POST_DIAGNOSIS
from fix_core.trees.brakes_rv import BRAKES_RV_TREE, BRAKES_RV_HYPOTHESES, BRAKES_RV_CONTEXT_PRIORS, BRAKES_RV_POST_DIAGNOSIS

# Phase 8C — transmission variants
from fix_core.trees.transmission_truck import TRANSMISSION_TRUCK_TREE, TRANSMISSION_TRUCK_HYPOTHESES, TRANSMISSION_TRUCK_CONTEXT_PRIORS, TRANSMISSION_TRUCK_POST_DIAGNOSIS
from fix_core.trees.transmission_motorcycle import TRANSMISSION_MOTORCYCLE_TREE, TRANSMISSION_MOTORCYCLE_HYPOTHESES, TRANSMISSION_MOTORCYCLE_CONTEXT_PRIORS, TRANSMISSION_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.transmission_atv import TRANSMISSION_ATV_TREE, TRANSMISSION_ATV_HYPOTHESES, TRANSMISSION_ATV_CONTEXT_PRIORS, TRANSMISSION_ATV_POST_DIAGNOSIS
from fix_core.trees.transmission_boat import TRANSMISSION_BOAT_TREE, TRANSMISSION_BOAT_HYPOTHESES, TRANSMISSION_BOAT_CONTEXT_PRIORS, TRANSMISSION_BOAT_POST_DIAGNOSIS
from fix_core.trees.transmission_rv import TRANSMISSION_RV_TREE, TRANSMISSION_RV_HYPOTHESES, TRANSMISSION_RV_CONTEXT_PRIORS, TRANSMISSION_RV_POST_DIAGNOSIS

# Phase 8C — suspension variants
from fix_core.trees.suspension_truck import SUSPENSION_TRUCK_TREE, SUSPENSION_TRUCK_HYPOTHESES, SUSPENSION_TRUCK_CONTEXT_PRIORS, SUSPENSION_TRUCK_POST_DIAGNOSIS
from fix_core.trees.suspension_motorcycle import SUSPENSION_MOTORCYCLE_TREE, SUSPENSION_MOTORCYCLE_HYPOTHESES, SUSPENSION_MOTORCYCLE_CONTEXT_PRIORS, SUSPENSION_MOTORCYCLE_POST_DIAGNOSIS
from fix_core.trees.suspension_atv import SUSPENSION_ATV_TREE, SUSPENSION_ATV_HYPOTHESES, SUSPENSION_ATV_CONTEXT_PRIORS, SUSPENSION_ATV_POST_DIAGNOSIS
from fix_core.trees.suspension_rv import SUSPENSION_RV_TREE, SUSPENSION_RV_HYPOTHESES, SUSPENSION_RV_CONTEXT_PRIORS, SUSPENSION_RV_POST_DIAGNOSIS

# Phase 8C — HVAC variants
from fix_core.trees.hvac_truck import HVAC_TRUCK_TREE, HVAC_TRUCK_HYPOTHESES, HVAC_TRUCK_CONTEXT_PRIORS, HVAC_TRUCK_POST_DIAGNOSIS
from fix_core.trees.hvac_rv import HVAC_RV_TREE, HVAC_RV_HYPOTHESES, HVAC_RV_CONTEXT_PRIORS, HVAC_RV_POST_DIAGNOSIS

# Phase 8D — RV variants for existing symptoms
from fix_core.trees.no_crank_rv import NO_CRANK_RV_TREE, NO_CRANK_RV_HYPOTHESES, NO_CRANK_RV_CONTEXT_PRIORS, NO_CRANK_RV_POST_DIAGNOSIS
from fix_core.trees.crank_no_start_rv import CRANK_NO_START_RV_TREE, CRANK_NO_START_RV_HYPOTHESES, CRANK_NO_START_RV_CONTEXT_PRIORS, CRANK_NO_START_RV_POST_DIAGNOSIS
from fix_core.trees.visible_leak_rv import VISIBLE_LEAK_RV_TREE, VISIBLE_LEAK_RV_HYPOTHESES, VISIBLE_LEAK_RV_CONTEXT_PRIORS, VISIBLE_LEAK_RV_POST_DIAGNOSIS
from fix_core.trees.overheating_rv import OVERHEATING_RV_TREE, OVERHEATING_RV_HYPOTHESES, OVERHEATING_RV_CONTEXT_PRIORS, OVERHEATING_RV_POST_DIAGNOSIS

# Phase 11 — Heavy Equipment (construction, field machinery, operator workflows)
from fix_core.trees.no_start_heavy_equipment import NO_START_HEAVY_EQUIPMENT_TREE, NO_START_HEAVY_EQUIPMENT_HYPOTHESES, NO_START_HEAVY_EQUIPMENT_CONTEXT_PRIORS, NO_START_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.hydraulic_loss_heavy_equipment import HYDRAULIC_LOSS_HEAVY_EQUIPMENT_TREE, HYDRAULIC_LOSS_HEAVY_EQUIPMENT_HYPOTHESES, HYDRAULIC_LOSS_HEAVY_EQUIPMENT_CONTEXT_PRIORS, HYDRAULIC_LOSS_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.loss_of_power_heavy_equipment import LOSS_OF_POWER_HEAVY_EQUIPMENT_TREE, LOSS_OF_POWER_HEAVY_EQUIPMENT_HYPOTHESES, LOSS_OF_POWER_HEAVY_EQUIPMENT_CONTEXT_PRIORS, LOSS_OF_POWER_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.overheating_heavy_equipment import OVERHEATING_HEAVY_EQUIPMENT_TREE, OVERHEATING_HEAVY_EQUIPMENT_HYPOTHESES, OVERHEATING_HEAVY_EQUIPMENT_CONTEXT_PRIORS, OVERHEATING_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.electrical_fault_heavy_equipment import ELECTRICAL_FAULT_HEAVY_EQUIPMENT_TREE, ELECTRICAL_FAULT_HEAVY_EQUIPMENT_HYPOTHESES, ELECTRICAL_FAULT_HEAVY_EQUIPMENT_CONTEXT_PRIORS, ELECTRICAL_FAULT_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.track_or_drive_issue_heavy_equipment import TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_TREE, TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_HYPOTHESES, TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_CONTEXT_PRIORS, TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.abnormal_noise_heavy_equipment import ABNORMAL_NOISE_HEAVY_EQUIPMENT_TREE, ABNORMAL_NOISE_HEAVY_EQUIPMENT_HYPOTHESES, ABNORMAL_NOISE_HEAVY_EQUIPMENT_CONTEXT_PRIORS, ABNORMAL_NOISE_HEAVY_EQUIPMENT_POST_DIAGNOSIS
# Phase 12 — Additional Heavy Equipment Trees
from fix_core.trees.coolant_leak_heavy_equipment import COOLANT_LEAK_HEAVY_EQUIPMENT_TREE, COOLANT_LEAK_HEAVY_EQUIPMENT_HYPOTHESES, COOLANT_LEAK_HEAVY_EQUIPMENT_CONTEXT_PRIORS, COOLANT_LEAK_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.implement_failure_heavy_equipment import IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_TREE, IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_HYPOTHESES, IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_CONTEXT_PRIORS, IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.cab_electrical_heavy_equipment import CAB_ELECTRICAL_HEAVY_EQUIPMENT_TREE, CAB_ELECTRICAL_HEAVY_EQUIPMENT_HYPOTHESES, CAB_ELECTRICAL_HEAVY_EQUIPMENT_CONTEXT_PRIORS, CAB_ELECTRICAL_HEAVY_EQUIPMENT_POST_DIAGNOSIS
from fix_core.trees.fuel_contamination_heavy_equipment import FUEL_CONTAMINATION_HEAVY_EQUIPMENT_TREE, FUEL_CONTAMINATION_HEAVY_EQUIPMENT_HYPOTHESES, FUEL_CONTAMINATION_HEAVY_EQUIPMENT_CONTEXT_PRIORS, FUEL_CONTAMINATION_HEAVY_EQUIPMENT_POST_DIAGNOSIS

# Phase 15C — HE Subtype Trees (tractor, excavator, loader, skid_steer)
from fix_core.trees.no_start_tractor import NO_START_TRACTOR_TREE, NO_START_TRACTOR_HYPOTHESES, NO_START_TRACTOR_CONTEXT_PRIORS, NO_START_TRACTOR_POST_DIAGNOSIS
from fix_core.trees.hydraulic_loss_tractor import HYDRAULIC_LOSS_TRACTOR_TREE, HYDRAULIC_LOSS_TRACTOR_HYPOTHESES, HYDRAULIC_LOSS_TRACTOR_CONTEXT_PRIORS, HYDRAULIC_LOSS_TRACTOR_POST_DIAGNOSIS
from fix_core.trees.no_start_excavator import NO_START_EXCAVATOR_TREE, NO_START_EXCAVATOR_HYPOTHESES, NO_START_EXCAVATOR_CONTEXT_PRIORS, NO_START_EXCAVATOR_POST_DIAGNOSIS
from fix_core.trees.hydraulic_loss_excavator import HYDRAULIC_LOSS_EXCAVATOR_TREE, HYDRAULIC_LOSS_EXCAVATOR_HYPOTHESES, HYDRAULIC_LOSS_EXCAVATOR_CONTEXT_PRIORS, HYDRAULIC_LOSS_EXCAVATOR_POST_DIAGNOSIS
from fix_core.trees.no_start_loader import NO_START_LOADER_TREE, NO_START_LOADER_HYPOTHESES, NO_START_LOADER_CONTEXT_PRIORS, NO_START_LOADER_POST_DIAGNOSIS
from fix_core.trees.hydraulic_loss_loader import HYDRAULIC_LOSS_LOADER_TREE, HYDRAULIC_LOSS_LOADER_HYPOTHESES, HYDRAULIC_LOSS_LOADER_CONTEXT_PRIORS, HYDRAULIC_LOSS_LOADER_POST_DIAGNOSIS
from fix_core.trees.no_start_skid_steer import NO_START_SKID_STEER_TREE, NO_START_SKID_STEER_HYPOTHESES, NO_START_SKID_STEER_CONTEXT_PRIORS, NO_START_SKID_STEER_POST_DIAGNOSIS
from fix_core.trees.hydraulic_loss_skid_steer import HYDRAULIC_LOSS_SKID_STEER_TREE, HYDRAULIC_LOSS_SKID_STEER_HYPOTHESES, HYDRAULIC_LOSS_SKID_STEER_CONTEXT_PRIORS, HYDRAULIC_LOSS_SKID_STEER_POST_DIAGNOSIS

TREES: dict[str, dict] = {
    # Base (car) trees
    "no_crank": NO_CRANK_TREE,
    "crank_no_start": CRANK_NO_START_TREE,
    "loss_of_power": LOSS_OF_POWER_TREE,
    "rough_idle": ROUGH_IDLE_TREE,
    "strange_noise": STRANGE_NOISE_TREE,
    "visible_leak": VISIBLE_LEAK_TREE,
    "overheating": OVERHEATING_TREE,
    "check_engine_light": CHECK_ENGINE_LIGHT_TREE,
    # Motorcycle variants
    "no_crank_motorcycle": NO_CRANK_MOTORCYCLE_TREE,
    "crank_no_start_motorcycle": CRANK_NO_START_MOTORCYCLE_TREE,
    "rough_idle_motorcycle": ROUGH_IDLE_MOTORCYCLE_TREE,
    "loss_of_power_motorcycle": LOSS_OF_POWER_MOTORCYCLE_TREE,
    "strange_noise_motorcycle": STRANGE_NOISE_MOTORCYCLE_TREE,
    "visible_leak_motorcycle": VISIBLE_LEAK_MOTORCYCLE_TREE,
    "overheating_motorcycle": OVERHEATING_MOTORCYCLE_TREE,
    "check_engine_light_motorcycle": CHECK_ENGINE_LIGHT_MOTORCYCLE_TREE,
    # Generator variants
    "no_crank_generator": NO_CRANK_GENERATOR_TREE,
    "crank_no_start_generator": CRANK_NO_START_GENERATOR_TREE,
    "loss_of_power_generator": LOSS_OF_POWER_GENERATOR_TREE,
    "rough_idle_generator": ROUGH_IDLE_GENERATOR_TREE,
    "strange_noise_generator": STRANGE_NOISE_GENERATOR_TREE,
    "visible_leak_generator": VISIBLE_LEAK_GENERATOR_TREE,
    # Truck/diesel variants
    "no_crank_truck": NO_CRANK_TRUCK_TREE,
    "crank_no_start_truck": CRANK_NO_START_TRUCK_TREE,
    "loss_of_power_truck": LOSS_OF_POWER_TRUCK_TREE,
    "rough_idle_truck": ROUGH_IDLE_TRUCK_TREE,
    "strange_noise_truck": STRANGE_NOISE_TRUCK_TREE,
    "overheating_truck": OVERHEATING_TRUCK_TREE,
    "check_engine_light_truck": CHECK_ENGINE_LIGHT_TRUCK_TREE,
    # Boat/marine variants
    "no_crank_boat": NO_CRANK_BOAT_TREE,
    "crank_no_start_boat": CRANK_NO_START_BOAT_TREE,
    "loss_of_power_boat": LOSS_OF_POWER_BOAT_TREE,
    "rough_idle_boat": ROUGH_IDLE_BOAT_TREE,
    "strange_noise_boat": STRANGE_NOISE_BOAT_TREE,
    "visible_leak_boat": VISIBLE_LEAK_BOAT_TREE,
    "overheating_boat": OVERHEATING_BOAT_TREE,
    # ATV/UTV variants
    "no_crank_atv": NO_CRANK_ATV_TREE,
    "crank_no_start_atv": CRANK_NO_START_ATV_TREE,
    "loss_of_power_atv": LOSS_OF_POWER_ATV_TREE,
    "rough_idle_atv": ROUGH_IDLE_ATV_TREE,
    "strange_noise_atv": STRANGE_NOISE_ATV_TREE,
    "visible_leak_atv": VISIBLE_LEAK_ATV_TREE,
    "overheating_atv": OVERHEATING_ATV_TREE,
    # PWC (personal watercraft) variants
    "no_crank_pwc": NO_CRANK_PWC_TREE,
    "crank_no_start_pwc": CRANK_NO_START_PWC_TREE,
    "loss_of_power_pwc": LOSS_OF_POWER_PWC_TREE,
    "strange_noise_pwc": STRANGE_NOISE_PWC_TREE,
    "overheating_pwc": OVERHEATING_PWC_TREE,
    "visible_leak_pwc": VISIBLE_LEAK_PWC_TREE,
    # Phase 8 — new symptom systems (base / car trees)
    "brakes": BRAKES_TREE,
    "transmission": TRANSMISSION_TREE,
    "suspension": SUSPENSION_TREE,
    "hvac": HVAC_TREE,
    # Phase 8C — brakes variants
    "brakes_truck": BRAKES_TRUCK_TREE,
    "brakes_motorcycle": BRAKES_MOTORCYCLE_TREE,
    "brakes_atv": BRAKES_ATV_TREE,
    "brakes_rv": BRAKES_RV_TREE,
    # Phase 8C — transmission variants
    "transmission_truck": TRANSMISSION_TRUCK_TREE,
    "transmission_motorcycle": TRANSMISSION_MOTORCYCLE_TREE,
    "transmission_atv": TRANSMISSION_ATV_TREE,
    "transmission_boat": TRANSMISSION_BOAT_TREE,
    "transmission_rv": TRANSMISSION_RV_TREE,
    # Phase 8C — suspension variants
    "suspension_truck": SUSPENSION_TRUCK_TREE,
    "suspension_motorcycle": SUSPENSION_MOTORCYCLE_TREE,
    "suspension_atv": SUSPENSION_ATV_TREE,
    "suspension_rv": SUSPENSION_RV_TREE,
    # Phase 8C — HVAC variants
    "hvac_truck": HVAC_TRUCK_TREE,
    "hvac_rv": HVAC_RV_TREE,
    # Phase 8D — RV variants for existing symptoms
    "no_crank_rv": NO_CRANK_RV_TREE,
    "crank_no_start_rv": CRANK_NO_START_RV_TREE,
    "visible_leak_rv": VISIBLE_LEAK_RV_TREE,
    "overheating_rv": OVERHEATING_RV_TREE,
    # Phase 11 — Heavy Equipment
    "no_start_heavy_equipment": NO_START_HEAVY_EQUIPMENT_TREE,
    "hydraulic_loss_heavy_equipment": HYDRAULIC_LOSS_HEAVY_EQUIPMENT_TREE,
    "loss_of_power_heavy_equipment": LOSS_OF_POWER_HEAVY_EQUIPMENT_TREE,
    "overheating_heavy_equipment": OVERHEATING_HEAVY_EQUIPMENT_TREE,
    "electrical_fault_heavy_equipment": ELECTRICAL_FAULT_HEAVY_EQUIPMENT_TREE,
    "track_or_drive_issue_heavy_equipment": TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_TREE,
    "abnormal_noise_heavy_equipment": ABNORMAL_NOISE_HEAVY_EQUIPMENT_TREE,
    # Phase 12 — Additional Heavy Equipment Trees
    "coolant_leak_heavy_equipment": COOLANT_LEAK_HEAVY_EQUIPMENT_TREE,
    "implement_failure_heavy_equipment": IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_TREE,
    "cab_electrical_heavy_equipment": CAB_ELECTRICAL_HEAVY_EQUIPMENT_TREE,
    "fuel_contamination_heavy_equipment": FUEL_CONTAMINATION_HEAVY_EQUIPMENT_TREE,
    # Phase 15C — HE Subtype Trees
    "no_start_tractor": NO_START_TRACTOR_TREE,
    "hydraulic_loss_tractor": HYDRAULIC_LOSS_TRACTOR_TREE,
    "no_start_excavator": NO_START_EXCAVATOR_TREE,
    "hydraulic_loss_excavator": HYDRAULIC_LOSS_EXCAVATOR_TREE,
    "no_start_loader": NO_START_LOADER_TREE,
    "hydraulic_loss_loader": HYDRAULIC_LOSS_LOADER_TREE,
    "no_start_skid_steer": NO_START_SKID_STEER_TREE,
    "hydraulic_loss_skid_steer": HYDRAULIC_LOSS_SKID_STEER_TREE,
}

HYPOTHESES: dict[str, dict] = {
    # Base (car) trees
    "no_crank": NO_CRANK_HYPOTHESES,
    "crank_no_start": CRANK_NO_START_HYPOTHESES,
    "loss_of_power": LOSS_OF_POWER_HYPOTHESES,
    "rough_idle": ROUGH_IDLE_HYPOTHESES,
    "strange_noise": STRANGE_NOISE_HYPOTHESES,
    "visible_leak": VISIBLE_LEAK_HYPOTHESES,
    "overheating": OVERHEATING_HYPOTHESES,
    "check_engine_light": CHECK_ENGINE_LIGHT_HYPOTHESES,
    # Motorcycle variants
    "no_crank_motorcycle": NO_CRANK_MOTORCYCLE_HYPOTHESES,
    "crank_no_start_motorcycle": CRANK_NO_START_MOTORCYCLE_HYPOTHESES,
    "rough_idle_motorcycle": ROUGH_IDLE_MOTORCYCLE_HYPOTHESES,
    "loss_of_power_motorcycle": LOSS_OF_POWER_MOTORCYCLE_HYPOTHESES,
    "strange_noise_motorcycle": STRANGE_NOISE_MOTORCYCLE_HYPOTHESES,
    "visible_leak_motorcycle": VISIBLE_LEAK_MOTORCYCLE_HYPOTHESES,
    "overheating_motorcycle": OVERHEATING_MOTORCYCLE_HYPOTHESES,
    "check_engine_light_motorcycle": CHECK_ENGINE_LIGHT_MOTORCYCLE_HYPOTHESES,
    # Generator variants
    "no_crank_generator": NO_CRANK_GENERATOR_HYPOTHESES,
    "crank_no_start_generator": CRANK_NO_START_GENERATOR_HYPOTHESES,
    "loss_of_power_generator": LOSS_OF_POWER_GENERATOR_HYPOTHESES,
    "rough_idle_generator": ROUGH_IDLE_GENERATOR_HYPOTHESES,
    "strange_noise_generator": STRANGE_NOISE_GENERATOR_HYPOTHESES,
    "visible_leak_generator": VISIBLE_LEAK_GENERATOR_HYPOTHESES,
    # Truck/diesel variants
    "no_crank_truck": NO_CRANK_TRUCK_HYPOTHESES,
    "crank_no_start_truck": CRANK_NO_START_TRUCK_HYPOTHESES,
    "loss_of_power_truck": LOSS_OF_POWER_TRUCK_HYPOTHESES,
    "rough_idle_truck": ROUGH_IDLE_TRUCK_HYPOTHESES,
    "strange_noise_truck": STRANGE_NOISE_TRUCK_HYPOTHESES,
    "overheating_truck": OVERHEATING_TRUCK_HYPOTHESES,
    "check_engine_light_truck": CHECK_ENGINE_LIGHT_TRUCK_HYPOTHESES,
    # Boat/marine variants
    "no_crank_boat": NO_CRANK_BOAT_HYPOTHESES,
    "crank_no_start_boat": CRANK_NO_START_BOAT_HYPOTHESES,
    "loss_of_power_boat": LOSS_OF_POWER_BOAT_HYPOTHESES,
    "rough_idle_boat": ROUGH_IDLE_BOAT_HYPOTHESES,
    "strange_noise_boat": STRANGE_NOISE_BOAT_HYPOTHESES,
    "visible_leak_boat": VISIBLE_LEAK_BOAT_HYPOTHESES,
    "overheating_boat": OVERHEATING_BOAT_HYPOTHESES,
    # ATV/UTV variants
    "no_crank_atv": NO_CRANK_ATV_HYPOTHESES,
    "crank_no_start_atv": CRANK_NO_START_ATV_HYPOTHESES,
    "loss_of_power_atv": LOSS_OF_POWER_ATV_HYPOTHESES,
    "rough_idle_atv": ROUGH_IDLE_ATV_HYPOTHESES,
    "strange_noise_atv": STRANGE_NOISE_ATV_HYPOTHESES,
    "visible_leak_atv": VISIBLE_LEAK_ATV_HYPOTHESES,
    "overheating_atv": OVERHEATING_ATV_HYPOTHESES,
    # PWC (personal watercraft) variants
    "no_crank_pwc": NO_CRANK_PWC_HYPOTHESES,
    "crank_no_start_pwc": CRANK_NO_START_PWC_HYPOTHESES,
    "loss_of_power_pwc": LOSS_OF_POWER_PWC_HYPOTHESES,
    "strange_noise_pwc": STRANGE_NOISE_PWC_HYPOTHESES,
    "overheating_pwc": OVERHEATING_PWC_HYPOTHESES,
    "visible_leak_pwc": VISIBLE_LEAK_PWC_HYPOTHESES,
    # Phase 8 — new symptom systems (base / car trees)
    "brakes": BRAKES_HYPOTHESES,
    "transmission": TRANSMISSION_HYPOTHESES,
    "suspension": SUSPENSION_HYPOTHESES,
    "hvac": HVAC_HYPOTHESES,
    # Phase 8C — brakes variants
    "brakes_truck": BRAKES_TRUCK_HYPOTHESES,
    "brakes_motorcycle": BRAKES_MOTORCYCLE_HYPOTHESES,
    "brakes_atv": BRAKES_ATV_HYPOTHESES,
    "brakes_rv": BRAKES_RV_HYPOTHESES,
    # Phase 8C — transmission variants
    "transmission_truck": TRANSMISSION_TRUCK_HYPOTHESES,
    "transmission_motorcycle": TRANSMISSION_MOTORCYCLE_HYPOTHESES,
    "transmission_atv": TRANSMISSION_ATV_HYPOTHESES,
    "transmission_boat": TRANSMISSION_BOAT_HYPOTHESES,
    "transmission_rv": TRANSMISSION_RV_HYPOTHESES,
    # Phase 8C — suspension variants
    "suspension_truck": SUSPENSION_TRUCK_HYPOTHESES,
    "suspension_motorcycle": SUSPENSION_MOTORCYCLE_HYPOTHESES,
    "suspension_atv": SUSPENSION_ATV_HYPOTHESES,
    "suspension_rv": SUSPENSION_RV_HYPOTHESES,
    # Phase 8C — HVAC variants
    "hvac_truck": HVAC_TRUCK_HYPOTHESES,
    "hvac_rv": HVAC_RV_HYPOTHESES,
    # Phase 8D — RV variants for existing symptoms
    "no_crank_rv": NO_CRANK_RV_HYPOTHESES,
    "crank_no_start_rv": CRANK_NO_START_RV_HYPOTHESES,
    "visible_leak_rv": VISIBLE_LEAK_RV_HYPOTHESES,
    "overheating_rv": OVERHEATING_RV_HYPOTHESES,
    # Phase 11 — Heavy Equipment
    "no_start_heavy_equipment": NO_START_HEAVY_EQUIPMENT_HYPOTHESES,
    "hydraulic_loss_heavy_equipment": HYDRAULIC_LOSS_HEAVY_EQUIPMENT_HYPOTHESES,
    "loss_of_power_heavy_equipment": LOSS_OF_POWER_HEAVY_EQUIPMENT_HYPOTHESES,
    "overheating_heavy_equipment": OVERHEATING_HEAVY_EQUIPMENT_HYPOTHESES,
    "electrical_fault_heavy_equipment": ELECTRICAL_FAULT_HEAVY_EQUIPMENT_HYPOTHESES,
    "track_or_drive_issue_heavy_equipment": TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_HYPOTHESES,
    "abnormal_noise_heavy_equipment": ABNORMAL_NOISE_HEAVY_EQUIPMENT_HYPOTHESES,
    # Phase 12 — Additional Heavy Equipment Trees
    "coolant_leak_heavy_equipment": COOLANT_LEAK_HEAVY_EQUIPMENT_HYPOTHESES,
    "implement_failure_heavy_equipment": IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_HYPOTHESES,
    "cab_electrical_heavy_equipment": CAB_ELECTRICAL_HEAVY_EQUIPMENT_HYPOTHESES,
    "fuel_contamination_heavy_equipment": FUEL_CONTAMINATION_HEAVY_EQUIPMENT_HYPOTHESES,
    # Phase 15C — HE Subtype Trees
    "no_start_tractor": NO_START_TRACTOR_HYPOTHESES,
    "hydraulic_loss_tractor": HYDRAULIC_LOSS_TRACTOR_HYPOTHESES,
    "no_start_excavator": NO_START_EXCAVATOR_HYPOTHESES,
    "hydraulic_loss_excavator": HYDRAULIC_LOSS_EXCAVATOR_HYPOTHESES,
    "no_start_loader": NO_START_LOADER_HYPOTHESES,
    "hydraulic_loss_loader": HYDRAULIC_LOSS_LOADER_HYPOTHESES,
    "no_start_skid_steer": NO_START_SKID_STEER_HYPOTHESES,
    "hydraulic_loss_skid_steer": HYDRAULIC_LOSS_SKID_STEER_HYPOTHESES,
}


CONTEXT_PRIORS: dict[str, dict] = {
    # Base (car) trees
    "no_crank": NO_CRANK_CONTEXT_PRIORS,
    "crank_no_start": CRANK_NO_START_CONTEXT_PRIORS,
    "loss_of_power": LOSS_OF_POWER_CONTEXT_PRIORS,
    "rough_idle": ROUGH_IDLE_CONTEXT_PRIORS,
    "strange_noise": STRANGE_NOISE_CONTEXT_PRIORS,
    "visible_leak": VISIBLE_LEAK_CONTEXT_PRIORS,
    "overheating": OVERHEATING_CONTEXT_PRIORS,
    "check_engine_light": CHECK_ENGINE_LIGHT_CONTEXT_PRIORS,
    # Motorcycle variants
    "no_crank_motorcycle": NO_CRANK_MOTORCYCLE_CONTEXT_PRIORS,
    "crank_no_start_motorcycle": CRANK_NO_START_MOTORCYCLE_CONTEXT_PRIORS,
    "rough_idle_motorcycle": ROUGH_IDLE_MOTORCYCLE_CONTEXT_PRIORS,
    "loss_of_power_motorcycle": LOSS_OF_POWER_MOTORCYCLE_CONTEXT_PRIORS,
    "strange_noise_motorcycle": STRANGE_NOISE_MOTORCYCLE_CONTEXT_PRIORS,
    "visible_leak_motorcycle": VISIBLE_LEAK_MOTORCYCLE_CONTEXT_PRIORS,
    "overheating_motorcycle": OVERHEATING_MOTORCYCLE_CONTEXT_PRIORS,
    "check_engine_light_motorcycle": CHECK_ENGINE_LIGHT_MOTORCYCLE_CONTEXT_PRIORS,
    # Generator variants
    "no_crank_generator": NO_CRANK_GENERATOR_CONTEXT_PRIORS,
    "crank_no_start_generator": CRANK_NO_START_GENERATOR_CONTEXT_PRIORS,
    "loss_of_power_generator": LOSS_OF_POWER_GENERATOR_CONTEXT_PRIORS,
    "rough_idle_generator": ROUGH_IDLE_GENERATOR_CONTEXT_PRIORS,
    "strange_noise_generator": STRANGE_NOISE_GENERATOR_CONTEXT_PRIORS,
    "visible_leak_generator": VISIBLE_LEAK_GENERATOR_CONTEXT_PRIORS,
    # Truck/diesel variants
    "no_crank_truck": NO_CRANK_TRUCK_CONTEXT_PRIORS,
    "crank_no_start_truck": CRANK_NO_START_TRUCK_CONTEXT_PRIORS,
    "loss_of_power_truck": LOSS_OF_POWER_TRUCK_CONTEXT_PRIORS,
    "rough_idle_truck": ROUGH_IDLE_TRUCK_CONTEXT_PRIORS,
    "strange_noise_truck": STRANGE_NOISE_TRUCK_CONTEXT_PRIORS,
    "overheating_truck": OVERHEATING_TRUCK_CONTEXT_PRIORS,
    "check_engine_light_truck": CHECK_ENGINE_LIGHT_TRUCK_CONTEXT_PRIORS,
    # Boat/marine variants
    "no_crank_boat": NO_CRANK_BOAT_CONTEXT_PRIORS,
    "crank_no_start_boat": CRANK_NO_START_BOAT_CONTEXT_PRIORS,
    "loss_of_power_boat": LOSS_OF_POWER_BOAT_CONTEXT_PRIORS,
    "rough_idle_boat": ROUGH_IDLE_BOAT_CONTEXT_PRIORS,
    "strange_noise_boat": STRANGE_NOISE_BOAT_CONTEXT_PRIORS,
    "visible_leak_boat": VISIBLE_LEAK_BOAT_CONTEXT_PRIORS,
    "overheating_boat": OVERHEATING_BOAT_CONTEXT_PRIORS,
    # ATV/UTV variants
    "no_crank_atv": NO_CRANK_ATV_CONTEXT_PRIORS,
    "crank_no_start_atv": CRANK_NO_START_ATV_CONTEXT_PRIORS,
    "loss_of_power_atv": LOSS_OF_POWER_ATV_CONTEXT_PRIORS,
    "rough_idle_atv": ROUGH_IDLE_ATV_CONTEXT_PRIORS,
    "strange_noise_atv": STRANGE_NOISE_ATV_CONTEXT_PRIORS,
    "visible_leak_atv": VISIBLE_LEAK_ATV_CONTEXT_PRIORS,
    "overheating_atv": OVERHEATING_ATV_CONTEXT_PRIORS,
    # PWC (personal watercraft) variants
    "no_crank_pwc": NO_CRANK_PWC_CONTEXT_PRIORS,
    "crank_no_start_pwc": CRANK_NO_START_PWC_CONTEXT_PRIORS,
    "loss_of_power_pwc": LOSS_OF_POWER_PWC_CONTEXT_PRIORS,
    "strange_noise_pwc": STRANGE_NOISE_PWC_CONTEXT_PRIORS,
    "overheating_pwc": OVERHEATING_PWC_CONTEXT_PRIORS,
    "visible_leak_pwc": VISIBLE_LEAK_PWC_CONTEXT_PRIORS,
    # Phase 8 — new symptom systems (base / car trees)
    "brakes": BRAKES_CONTEXT_PRIORS,
    "transmission": TRANSMISSION_CONTEXT_PRIORS,
    "suspension": SUSPENSION_CONTEXT_PRIORS,
    "hvac": HVAC_CONTEXT_PRIORS,
    # Phase 8C — brakes variants
    "brakes_truck": BRAKES_TRUCK_CONTEXT_PRIORS,
    "brakes_motorcycle": BRAKES_MOTORCYCLE_CONTEXT_PRIORS,
    "brakes_atv": BRAKES_ATV_CONTEXT_PRIORS,
    "brakes_rv": BRAKES_RV_CONTEXT_PRIORS,
    # Phase 8C — transmission variants
    "transmission_truck": TRANSMISSION_TRUCK_CONTEXT_PRIORS,
    "transmission_motorcycle": TRANSMISSION_MOTORCYCLE_CONTEXT_PRIORS,
    "transmission_atv": TRANSMISSION_ATV_CONTEXT_PRIORS,
    "transmission_boat": TRANSMISSION_BOAT_CONTEXT_PRIORS,
    "transmission_rv": TRANSMISSION_RV_CONTEXT_PRIORS,
    # Phase 8C — suspension variants
    "suspension_truck": SUSPENSION_TRUCK_CONTEXT_PRIORS,
    "suspension_motorcycle": SUSPENSION_MOTORCYCLE_CONTEXT_PRIORS,
    "suspension_atv": SUSPENSION_ATV_CONTEXT_PRIORS,
    "suspension_rv": SUSPENSION_RV_CONTEXT_PRIORS,
    # Phase 8C — HVAC variants
    "hvac_truck": HVAC_TRUCK_CONTEXT_PRIORS,
    "hvac_rv": HVAC_RV_CONTEXT_PRIORS,
    # Phase 8D — RV variants for existing symptoms
    "no_crank_rv": NO_CRANK_RV_CONTEXT_PRIORS,
    "crank_no_start_rv": CRANK_NO_START_RV_CONTEXT_PRIORS,
    "visible_leak_rv": VISIBLE_LEAK_RV_CONTEXT_PRIORS,
    "overheating_rv": OVERHEATING_RV_CONTEXT_PRIORS,
    # Phase 11 — Heavy Equipment
    "no_start_heavy_equipment": NO_START_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "hydraulic_loss_heavy_equipment": HYDRAULIC_LOSS_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "loss_of_power_heavy_equipment": LOSS_OF_POWER_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "overheating_heavy_equipment": OVERHEATING_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "electrical_fault_heavy_equipment": ELECTRICAL_FAULT_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "track_or_drive_issue_heavy_equipment": TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "abnormal_noise_heavy_equipment": ABNORMAL_NOISE_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    # Phase 12 — Additional Heavy Equipment Trees
    "coolant_leak_heavy_equipment": COOLANT_LEAK_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "implement_failure_heavy_equipment": IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "cab_electrical_heavy_equipment": CAB_ELECTRICAL_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    "fuel_contamination_heavy_equipment": FUEL_CONTAMINATION_HEAVY_EQUIPMENT_CONTEXT_PRIORS,
    # Phase 15C — HE Subtype Trees
    "no_start_tractor": NO_START_TRACTOR_CONTEXT_PRIORS,
    "hydraulic_loss_tractor": HYDRAULIC_LOSS_TRACTOR_CONTEXT_PRIORS,
    "no_start_excavator": NO_START_EXCAVATOR_CONTEXT_PRIORS,
    "hydraulic_loss_excavator": HYDRAULIC_LOSS_EXCAVATOR_CONTEXT_PRIORS,
    "no_start_loader": NO_START_LOADER_CONTEXT_PRIORS,
    "hydraulic_loss_loader": HYDRAULIC_LOSS_LOADER_CONTEXT_PRIORS,
    "no_start_skid_steer": NO_START_SKID_STEER_CONTEXT_PRIORS,
    "hydraulic_loss_skid_steer": HYDRAULIC_LOSS_SKID_STEER_CONTEXT_PRIORS,
}


POST_DIAGNOSIS: dict[str, list[str]] = {
    # Base (car) trees
    "no_crank": NO_CRANK_POST_DIAGNOSIS,
    "crank_no_start": CRANK_NO_START_POST_DIAGNOSIS,
    "loss_of_power": LOSS_OF_POWER_POST_DIAGNOSIS,
    "rough_idle": ROUGH_IDLE_POST_DIAGNOSIS,
    "strange_noise": STRANGE_NOISE_POST_DIAGNOSIS,
    "visible_leak": VISIBLE_LEAK_POST_DIAGNOSIS,
    "overheating": OVERHEATING_POST_DIAGNOSIS,
    "check_engine_light": CHECK_ENGINE_LIGHT_POST_DIAGNOSIS,
    # Motorcycle variants
    "no_crank_motorcycle": NO_CRANK_MOTORCYCLE_POST_DIAGNOSIS,
    "crank_no_start_motorcycle": CRANK_NO_START_MOTORCYCLE_POST_DIAGNOSIS,
    "rough_idle_motorcycle": ROUGH_IDLE_MOTORCYCLE_POST_DIAGNOSIS,
    "loss_of_power_motorcycle": LOSS_OF_POWER_MOTORCYCLE_POST_DIAGNOSIS,
    "strange_noise_motorcycle": STRANGE_NOISE_MOTORCYCLE_POST_DIAGNOSIS,
    "visible_leak_motorcycle": VISIBLE_LEAK_MOTORCYCLE_POST_DIAGNOSIS,
    "overheating_motorcycle": OVERHEATING_MOTORCYCLE_POST_DIAGNOSIS,
    "check_engine_light_motorcycle": CHECK_ENGINE_LIGHT_MOTORCYCLE_POST_DIAGNOSIS,
    # Generator variants
    "no_crank_generator": NO_CRANK_GENERATOR_POST_DIAGNOSIS,
    "crank_no_start_generator": CRANK_NO_START_GENERATOR_POST_DIAGNOSIS,
    "loss_of_power_generator": LOSS_OF_POWER_GENERATOR_POST_DIAGNOSIS,
    "rough_idle_generator": ROUGH_IDLE_GENERATOR_POST_DIAGNOSIS,
    "strange_noise_generator": STRANGE_NOISE_GENERATOR_POST_DIAGNOSIS,
    "visible_leak_generator": VISIBLE_LEAK_GENERATOR_POST_DIAGNOSIS,
    # Truck/diesel variants
    "no_crank_truck": NO_CRANK_TRUCK_POST_DIAGNOSIS,
    "crank_no_start_truck": CRANK_NO_START_TRUCK_POST_DIAGNOSIS,
    "loss_of_power_truck": LOSS_OF_POWER_TRUCK_POST_DIAGNOSIS,
    "rough_idle_truck": ROUGH_IDLE_TRUCK_POST_DIAGNOSIS,
    "strange_noise_truck": STRANGE_NOISE_TRUCK_POST_DIAGNOSIS,
    "overheating_truck": OVERHEATING_TRUCK_POST_DIAGNOSIS,
    "check_engine_light_truck": CHECK_ENGINE_LIGHT_TRUCK_POST_DIAGNOSIS,
    # Boat/marine variants
    "no_crank_boat": NO_CRANK_BOAT_POST_DIAGNOSIS,
    "crank_no_start_boat": CRANK_NO_START_BOAT_POST_DIAGNOSIS,
    "loss_of_power_boat": LOSS_OF_POWER_BOAT_POST_DIAGNOSIS,
    "rough_idle_boat": ROUGH_IDLE_BOAT_POST_DIAGNOSIS,
    "strange_noise_boat": STRANGE_NOISE_BOAT_POST_DIAGNOSIS,
    "visible_leak_boat": VISIBLE_LEAK_BOAT_POST_DIAGNOSIS,
    "overheating_boat": OVERHEATING_BOAT_POST_DIAGNOSIS,
    # ATV/UTV variants
    "no_crank_atv": NO_CRANK_ATV_POST_DIAGNOSIS,
    "crank_no_start_atv": CRANK_NO_START_ATV_POST_DIAGNOSIS,
    "loss_of_power_atv": LOSS_OF_POWER_ATV_POST_DIAGNOSIS,
    "rough_idle_atv": ROUGH_IDLE_ATV_POST_DIAGNOSIS,
    "strange_noise_atv": STRANGE_NOISE_ATV_POST_DIAGNOSIS,
    "visible_leak_atv": VISIBLE_LEAK_ATV_POST_DIAGNOSIS,
    "overheating_atv": OVERHEATING_ATV_POST_DIAGNOSIS,
    # PWC (personal watercraft) variants
    "no_crank_pwc": NO_CRANK_PWC_POST_DIAGNOSIS,
    "crank_no_start_pwc": CRANK_NO_START_PWC_POST_DIAGNOSIS,
    "loss_of_power_pwc": LOSS_OF_POWER_PWC_POST_DIAGNOSIS,
    "strange_noise_pwc": STRANGE_NOISE_PWC_POST_DIAGNOSIS,
    "overheating_pwc": OVERHEATING_PWC_POST_DIAGNOSIS,
    "visible_leak_pwc": VISIBLE_LEAK_PWC_POST_DIAGNOSIS,
    # Phase 8 — new symptom systems (base / car trees)
    "brakes": BRAKES_POST_DIAGNOSIS,
    "transmission": TRANSMISSION_POST_DIAGNOSIS,
    "suspension": SUSPENSION_POST_DIAGNOSIS,
    "hvac": HVAC_POST_DIAGNOSIS,
    # Phase 8C — brakes variants
    "brakes_truck": BRAKES_TRUCK_POST_DIAGNOSIS,
    "brakes_motorcycle": BRAKES_MOTORCYCLE_POST_DIAGNOSIS,
    "brakes_atv": BRAKES_ATV_POST_DIAGNOSIS,
    "brakes_rv": BRAKES_RV_POST_DIAGNOSIS,
    # Phase 8C — transmission variants
    "transmission_truck": TRANSMISSION_TRUCK_POST_DIAGNOSIS,
    "transmission_motorcycle": TRANSMISSION_MOTORCYCLE_POST_DIAGNOSIS,
    "transmission_atv": TRANSMISSION_ATV_POST_DIAGNOSIS,
    "transmission_boat": TRANSMISSION_BOAT_POST_DIAGNOSIS,
    "transmission_rv": TRANSMISSION_RV_POST_DIAGNOSIS,
    # Phase 8C — suspension variants
    "suspension_truck": SUSPENSION_TRUCK_POST_DIAGNOSIS,
    "suspension_motorcycle": SUSPENSION_MOTORCYCLE_POST_DIAGNOSIS,
    "suspension_atv": SUSPENSION_ATV_POST_DIAGNOSIS,
    "suspension_rv": SUSPENSION_RV_POST_DIAGNOSIS,
    # Phase 8C — HVAC variants
    "hvac_truck": HVAC_TRUCK_POST_DIAGNOSIS,
    "hvac_rv": HVAC_RV_POST_DIAGNOSIS,
    # Phase 8D — RV variants for existing symptoms
    "no_crank_rv": NO_CRANK_RV_POST_DIAGNOSIS,
    "crank_no_start_rv": CRANK_NO_START_RV_POST_DIAGNOSIS,
    "visible_leak_rv": VISIBLE_LEAK_RV_POST_DIAGNOSIS,
    "overheating_rv": OVERHEATING_RV_POST_DIAGNOSIS,
    # Phase 11 — Heavy Equipment
    "no_start_heavy_equipment": NO_START_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "hydraulic_loss_heavy_equipment": HYDRAULIC_LOSS_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "loss_of_power_heavy_equipment": LOSS_OF_POWER_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "overheating_heavy_equipment": OVERHEATING_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "electrical_fault_heavy_equipment": ELECTRICAL_FAULT_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "track_or_drive_issue_heavy_equipment": TRACK_OR_DRIVE_ISSUE_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "abnormal_noise_heavy_equipment": ABNORMAL_NOISE_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    # Phase 12 — Additional Heavy Equipment Trees
    "coolant_leak_heavy_equipment": COOLANT_LEAK_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "implement_failure_heavy_equipment": IMPLEMENT_FAILURE_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "cab_electrical_heavy_equipment": CAB_ELECTRICAL_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    "fuel_contamination_heavy_equipment": FUEL_CONTAMINATION_HEAVY_EQUIPMENT_POST_DIAGNOSIS,
    # Phase 15C — HE Subtype Trees
    "no_start_tractor": NO_START_TRACTOR_POST_DIAGNOSIS,
    "hydraulic_loss_tractor": HYDRAULIC_LOSS_TRACTOR_POST_DIAGNOSIS,
    "no_start_excavator": NO_START_EXCAVATOR_POST_DIAGNOSIS,
    "hydraulic_loss_excavator": HYDRAULIC_LOSS_EXCAVATOR_POST_DIAGNOSIS,
    "no_start_loader": NO_START_LOADER_POST_DIAGNOSIS,
    "hydraulic_loss_loader": HYDRAULIC_LOSS_LOADER_POST_DIAGNOSIS,
    "no_start_skid_steer": NO_START_SKID_STEER_POST_DIAGNOSIS,
    "hydraulic_loss_skid_steer": HYDRAULIC_LOSS_SKID_STEER_POST_DIAGNOSIS,
}


_HE_SUBTYPES = {"tractor", "excavator", "loader", "skid_steer"}


def resolve_tree_key(symptom_category: str, vehicle_type: str) -> str:
    """Return the best tree key for (symptom_category, vehicle_type).
    For HE subtypes, falls back to heavy_equipment before the base (car) tree.
    Falls back to base symptom_category if no vehicle-specific variant exists."""
    candidate = f"{symptom_category}_{vehicle_type}"
    if candidate in TREES:
        return candidate
    if vehicle_type in _HE_SUBTYPES:
        he_candidate = f"{symptom_category}_heavy_equipment"
        if he_candidate in TREES:
            return he_candidate
    return symptom_category
