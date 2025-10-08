import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2df9f8-pt3/2df9f8-pt3.ot2.apiv2.py"

"""Protocol."""
metadata = {
    'protocolName': 'Plate Filling Heat Inactivated Covid Samples for PCR - Part 3',  # noqa: E501
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):
    """Protocol."""

    [num_plates] = get_values(  # noqa: F821
        'num_plates')

    # load labware
    reservoirs = [ctx.load_labware('nest_1_reservoir_195ml', slot)
                  for slot in ['1', '2']]
    tiprack = [ctx.load_labware('opentrons_96_tiprack_300ul', '3')]
    plates = [ctx.load_labware(
        'nest_96_wellplate_2ml_deep', slot)
        for slot in ['4', '5', '6', '7', '8', '9', '10', '11']][:num_plates]

    # load instrument
    p300L = ctx.load_instrument('p300_multi_gen2', "left",
                                tip_racks=tiprack)
    p300R = ctx.load_instrument('p300_multi_gen2', "right",
                                tip_racks=tiprack)

    cols_L = [col for plate in plates for col in plate.rows()[0][::2]]
    cols_R = [col for plate in plates for col in plate.rows()[0][1::2]]
    res_wells = [well for res in reservoirs for well in res.wells()]

    # protocol
    p300L.pick_up_tip()
    p300R.pick_up_tip()
    for i, (s, left, right) in enumerate(zip(res_wells*12,
                                             cols_L,
                                             cols_R)):
        for _ in range(2):
            p300L.aspirate(300, s)
            p300R.aspirate(300, s)
            p300L.dispense(300, left)
            p300L.blow_out()
            p300R.dispense(300, right)
            p300R.blow_out()
        ctx.comment('\n\n')
    p300L.drop_tip()
    p300R.drop_tip()

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
    filename = f"detailed_action_json/2df9f8-pt3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)