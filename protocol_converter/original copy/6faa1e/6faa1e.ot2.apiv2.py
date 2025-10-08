import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6faa1e/6faa1e.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR/qPCR prep (Master Mix Transfer)',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [m20_mount] = get_values(  # noqa: F821
        "m20_mount")

    # Load labware
    tiprack = ctx.load_labware('opentrons_96_tiprack_20ul', 10)
    source_plate_1 = ctx.load_labware('nest_12_reservoir_15ml_icetray', 11,
                                      'Source Plate #1')

    for slot in range(1, 9):
        if int(slot) not in ctx.loaded_labwares:
            ctx.load_labware('thermofast_96well_semiskirted_eppendorf_cooler',
                             slot, f'Destination Plate #{slot}')

    # Load pipette
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=[tiprack])

    # Setup source and destinations
    mm_1 = source_plate_1['A1']
    mm_2 = source_plate_1['A2']

    sample_set_1 = [ctx.loaded_labwares[i].rows()[0] for i in range(1, 5)]
    sample_set_2 = [ctx.loaded_labwares[i].rows()[0] for i in range(5, 9)]

    m20.pick_up_tip()
    for source, dest in zip([mm_1, mm_2], [sample_set_1, sample_set_2]):
        m20.transfer(16, source, dest, new_tip='never')
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
    filename = f"detailed_action_json/6faa1e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)