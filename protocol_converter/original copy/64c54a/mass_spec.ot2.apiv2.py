import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/64c54a/mass_spec.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Mass Spec Sample Prep',
    'author': 'Nick <ndiehl@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.12'
}


def run(ctx):

    num_samples, p1000_mount = get_values(  # noqa: F821
        'num_samples', 'p1000_mount')

    # labware
    source_rack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '1',
        'source tubes')
    dest_rack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '2',
        'destination tubes')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '4')
    tipracks1000 = [
        ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
        for slot in ['3', '5', '6', '7', '8', '9', '10', '11'][
            :math.ceil(num_samples*2/96)]]

    # pipettes
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tipracks1000)

    # define wells and volumes
    num_tubes_per_replacement = len(source_rack.wells())
    num_replacements = math.ceil(num_samples/num_tubes_per_replacement)
    source_sets, dest_sets = [
        [rack.wells()[:num_samples % num_tubes_per_replacement]
         if r == num_replacements - 1
         else rack.wells()
         for r in range(num_replacements)]
        for rack in [source_rack, dest_rack]
    ]

    mobile_phase_a = reservoir.rows()[0][0]

    vol_supernatant = 900.0
    vol_reconstitution = 100.0

    # transfer precipitate
    p1000.flow_rate.aspirate /= 5
    for i, (source_set, dest_set) in enumerate(zip(source_sets, dest_sets)):
        samples_per_set = len(source_set)
        sample_start = (i+1)*num_tubes_per_replacement+1
        sample_end = (i+1)*num_tubes_per_replacement+samples_per_set
        for s, d in zip(source_set, dest_set):
            p1000.transfer(vol_supernatant, s.bottom(3), d)
        if i < num_replacements - 1:
            msg = f'Place next set of samples {sample_start}-{sample_end} in  slot 1 and fresh 1.5ml tubes in slot 2.'
        else:
            msg = 'Dry the samples to with a N2 dryer or SpeedVac with no  temp. Place samples 1-24 on slot 1 when complete.'
        ctx.pause(msg)

    # reconstitute in mobile phase A
    p1000.flow_rate.aspirate *= 5
    for i, source_set in enumerate(source_sets):
        samples_per_set = len(source_set)
        sample_start = (i+1)*num_tubes_per_replacement+1
        sample_end = (i+1)*num_tubes_per_replacement+samples_per_set
        for s in source_set:
            p1000.transfer(vol_reconstitution, mobile_phase_a, s.bottom(3),
                           mix_after=(5, 100))
        if i < num_replacements - 1:
            msg = f'Place next set of samples {sample_start}-{sample_end} in  slot 1 and fresh 1.5ml tubes in slot 2.'
            ctx.pause(msg)

    from opentrons.protocol_api.labware import Well, Labware
    import re
    import json
    all_vars = locals()

    # Wells that have been processed 
    processed_wells = set()
    liquid_locations = {}

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, list) and len(var_value) > 0 and isinstance(var_value[0], Well):
            for i, well in enumerate(var_value):
                processed_wells.add(well)   
                display_name = well.display_name
                well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
                slot_match = re.search(r" on (\d+)$", display_name)
                slot_number = slot_match.group(1) if slot_match else "unknown"
                name_with_index = f"{var_name}[{i}]"
                liquid_locations[name_with_index] = {
                    "well": well_position,
                    "slot": slot_number
                }

    for var_name, var_value in all_vars.items():
        if isinstance(var_value, Well):
            if var_value in processed_wells:
                continue
            
            display_name = var_value.display_name
            well_position = display_name.split(" of ")[0] if " of " in display_name else "unknown"
            slot_match = re.search(r" on (\d+)$", display_name)
            slot_number = slot_match.group(1) if slot_match else "unknown"
            liquid_locations[var_name] = {
                "well": well_position,
                "slot": slot_number
            }
    filename = f"detailed_action_json/64c54a.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)