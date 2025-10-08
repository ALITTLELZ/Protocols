import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2df9f8-pt4/2df9f8-pt4.ot2.apiv2.py"

"""Protocol."""
metadata = {
    'protocolName': 'Pooling Deep Well Plates by Column',  # noqa: E501
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):
    """Protocol."""

    [num_plates, num_col, p300_mount] = get_values(  # noqa: F821
        'num_plates', "num_col", "p300_mount")

    num_plates = int(num_plates)
    num_col = int(num_col)

    # load labware
    tiprack = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in ['1', '2', '3', '4', '5']]
    plates = [ctx.load_labware(
        'nest_96_wellplate_2ml_deep', slot)
        for slot in ['6', '7', '8', '9', '10']][:num_plates]
    pooled_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '11')

    # load instrument
    m300 = ctx.load_instrument('p300_multi_gen2', p300_mount,
                               tip_racks=tiprack)

    # protocol
    for plate in plates:
        for col, dest in zip(plate.rows()[0][:num_col],
                             pooled_plate.rows()[0]):
            m300.pick_up_tip()
            m300.aspirate(100, col)
            m300.dispense(100, dest)
            m300.blow_out()
            m300.touch_tip()
            m300.drop_tip()

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
    filename = f"detailed_action_json/2df9f8-pt4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)