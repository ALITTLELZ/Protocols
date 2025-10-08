import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/060c4f/060c4f.ot2.apiv2.py"

metadata = {
    'protocolName': '96-well to 384-well transfer',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.4'
}


def run(protocol):
    [plate_cols, pip_mount] = get_values(  # noqa: F821
        'plate_cols', 'pip_mount')

    # load labware and pipettes
    tips300 = [protocol.load_labware('opentrons_96_tiprack_300ul', '2')]

    m300 = protocol.load_instrument(
        'p300_multi', pip_mount, tip_racks=tips300)

    tempdeck = protocol.load_module('tempdeck', '4')

    tempplate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul')

    destplate = protocol.load_labware('greinerbioone_384_wellplate_100ul', '1')

    tempdeck.set_temperature(4)

    # transfer 30ul from source column to 3 corresponding columns

    src_cols = tempplate.rows()[0][:8]

    dest_cols = []
    for i in range(8):
        num1 = i*3+1
        num2 = i*3+4
        x = [destplate[plate_cols+str(i)] for i in range(num1, num2)]
        dest_cols.append(x)

    for src, dest in zip(src_cols, dest_cols):
        m300.pick_up_tip()
        m300.aspirate(90, src)
        for d in dest:
            m300.dispense(30, d)
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
    filename = f"detailed_action_json/060c4f.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)