import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/470d8c/470d8c.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR/qPCR prep',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx):

    [m300_mount, m20_mount] = get_values(  # noqa: F821
        "m300_mount", "m20_mount")

    # Load labware
    tipracks_20ul = [ctx.load_labware('opentrons_96_tiprack_20ul', slot) for
                     slot in [7, 10, 11]]
    tiprack_300ul = [ctx.load_labware('opentrons_96_tiprack_300ul', 4)]
    source_plate = ctx.load_labware('nest_12_reservoir_15ml_icetray', 1,
                                    'Source Plate #1')
    temp_plates = [ctx.load_labware(
                    'thermofast_96well_semiskirted_eppendorf_cooler',
                    slot, f'Template Plate #{i}') for i, slot
                   in enumerate([8, 5, 2], 1)]
    dest_plates = [ctx.load_labware(
                    'thermofast_96well_semiskirted_eppendorf_cooler',
                    slot, f'Destination Plate #{i}') for i, slot
                   in enumerate([9, 6, 3], 1)]

    # Load pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tipracks_20ul)
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tiprack_300ul)

    # Transfer 40 uL of master mix
    m300.pick_up_tip()
    for plate in temp_plates:
        m300.transfer(40, source_plate['A1'], plate.rows()[0], new_tip='never')
    m300.drop_tip()

    # Transfer 10 uL of Template to Destination
    for source, dest in zip(temp_plates, dest_plates):
        m20.transfer(10, source.rows()[0], dest.rows()[0])

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
    filename = f"detailed_action_json/470d8c.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)