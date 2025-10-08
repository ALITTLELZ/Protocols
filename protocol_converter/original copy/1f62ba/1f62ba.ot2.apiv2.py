import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1f62ba/1f62ba.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'PCR Prep with Strip Tubes',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):

    [
     _num_col,
     _m20_mount
    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "_num_col",
        "_m20_mount")

    # VARIABLES
    num_col = _num_col
    m20_mount = _m20_mount

    if not 1 <= num_col <= 12:
        raise Exception("Enter a column number 1-12")

    # LABWARE
    water = ctx.load_labware('nest_12_reservoir_15ml', '3')
    kappa_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '1')
    dna_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '2')
    primer_num_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '4')
    primer_let_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '5')
    final_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '6')

    # TIPRACKS
    tipracks = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                for slot in ['7', '8', '9', '10']]

    # INSTRUMENTS
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tipracks)

    # protocol
    cols = final_plate.rows()[0][:num_col]
    ctx.comment('\n\nMOVING WATER TO PLATE\n')
    m20.pick_up_tip()
    m20.distribute(3, water.wells()[0], [col for col in cols], new_tip='never')
    m20.drop_tip()

    ctx.comment('\n\nMOVING KAPPA ENZYME TO PLATE\n')
    m20.pick_up_tip()
    for kappa, col in zip(kappa_plate.rows()[0], cols):
        m20.aspirate(10, kappa)
        m20.dispense(10, col)
        m20.blow_out()
    m20.drop_tip()

    ctx.comment('\n\nMOVING PRIMER NUMBER TO PLATE\n')
    for primer_num, col in zip(primer_num_plate.rows()[0], cols):
        m20.pick_up_tip()
        m20.aspirate(1, primer_num)
        m20.dispense(1, col)
        m20.drop_tip()

    ctx.comment('\n\nMOVING PRIMER LETTER TO PLATE\n')
    for primer_let, col in zip(primer_let_plate.rows()[0], cols):
        m20.pick_up_tip()
        m20.aspirate(1, primer_let)
        m20.dispense(1, col)
        m20.drop_tip()

    ctx.comment('\n\nMOVING DNA TO PLATE\n')
    for dna, col in zip(dna_plate.rows()[0], cols):
        m20.pick_up_tip()
        m20.aspirate(5, dna)
        m20.dispense(5, col)
        m20.drop_tip()

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
    filename = f"detailed_action_json/1f62ba.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)