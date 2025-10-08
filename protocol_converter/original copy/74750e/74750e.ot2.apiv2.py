import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/74750e/74750e.ot2.apiv2.py"

metadata = {
    'protocolName': 'Standard Serial Dilution',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [num_columns, num_plates] = get_values(  # noqa: F821
        "num_columns", "num_plates")

    if not 1 <= num_columns <= 12:
        raise Exception("Enter a column number between 1-12")
    if not 1 <= num_plates <= 10:
        raise Exception("Enter a plate number between 1-10")

    # custom number of Plates
    custom_plates = [str(i) for i in range(2, num_plates+2)]

    # labware setup
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', '1')
    plates = [ctx.load_labware('corning_96_wellplate_360ul_flat', slot)
              for slot in custom_plates]

    # instrument setup
    p300 = ctx.load_instrument('p300_multi_gen2', 'left', tip_racks=[tiprack])

    # commands
    num_dilutions = num_columns - 1

    for plate in plates:
        p300.pick_up_tip()
        rows = zip(plate.rows()[0][:num_dilutions],
                   plate.rows()[0][1:num_dilutions+1])
        p300.mix(12, 100, plate.rows()[0][0])
        for source, dest in rows:
            p300.transfer(20, source, dest,
                          mix_after=(12, 100), new_tip='never')
        p300.aspirate(20, plate.rows()[0][num_dilutions])
        p300.drop_tip()

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
    filename = f"detailed_action_json/74750e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)