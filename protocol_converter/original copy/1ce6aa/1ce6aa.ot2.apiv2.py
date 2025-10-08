import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1ce6aa/1ce6aa.ot2.apiv2.py"

metadata = {
    'protocolName': 'Transfer to BHI',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(protocol):
    [pip_mnt, samp_no] = get_values(  # noqa: F821
        'pip_mnt', 'samp_no')

    # load labware
    tips = protocol.load_labware('generic_96_tiprack_20ul', '1')
    src = protocol.load_labware('custom_96_tubeholder_500ul', '2')
    dest = protocol.load_labware('custom_96_tubeholder_500ul', '3')
    pip = protocol.load_instrument('p300_multi', pip_mnt, tip_racks=[tips])

    row_no = samp_no//8
    rows_samp = row_no if samp_no % 8 == 0 else row_no + 1

    src_rows = src.rows()[0][:rows_samp]
    dest_rows = dest.rows()[0][:rows_samp]

    for s, d in zip(src_rows, dest_rows):
        pip.transfer(10, s.top(-5), d.bottom(20), air_gap=2)

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
    filename = f"detailed_action_json/1ce6aa.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)