import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2d7126/pin_pickup.ot2.apiv2.py"

metadata = {
    'protocolName': '8-Pin Pickup',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [num_cols, m300_type, m300_mount] = get_values(  # noqa: F821
        'num_cols', 'm300_type', 'm300_mount')

    # check
    if not 1 <= num_cols <= 12:
        raise Exception('Invalid number of columns (must be 1-12).')

    # labware
    plate1, plate2 = [
        ctx.load_labware('corning_96_wellplate_360ul_flat', slot,
                         'plate ' + str(i+1))
        for i, slot in enumerate(['1', '2'])]
    pinrack = [ctx.load_labware('opentrons_96_tiprack_300ul', '5',
                                'custom pin adapter')]

    # pipette
    m300 = ctx.load_instrument(m300_type, m300_mount, tip_racks=pinrack)
    m300.pick_up_tip()
    m300.aspirate(1, plate1.rows()[0][0].top(1))
    m300.dispense(1)
    m300.aspirate(1, plate2.rows()[0][0].top(1))
    m300.dispense(1)

    for col1, col2 in zip(plate1.rows()[0], plate2.rows()[0]):
        # plate 1
        m300.default_speed = 40
        for _ in range(3):
            m300.move_to(col1.top(1))
            m300.move_to(col1.bottom(-0.5))
        m300.default_speed = 400

        # plate 2
        m300.default_speed = 40
        m300.move_to(col2.top(1))
        m300.move_to(col2.bottom(-0.5))
        ctx.delay(seconds=3)
        m300.default_speed = 400

    m300.default_speed = 40
    m300.return_tip()

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
    filename = f"detailed_action_json/2d7126.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)