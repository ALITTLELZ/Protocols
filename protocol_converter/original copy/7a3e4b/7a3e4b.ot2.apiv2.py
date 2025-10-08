import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7a3e4b/7a3e4b.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cherrypicking with Source and Destination',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
    }


def run(protocol):
    [volumes_csv, pip_model, pip_mount, sp_type,
     dp_type, tip_reuse] = get_values(  # noqa: F821
     'volumes_csv', 'pip_model', 'pip_mount', 'sp_type', 'dp_type',
     'tip_reuse')

    # create pipette and tip rack
    pip_max = pip_model.split('_')[0][1:]

    pip_max = '300' if pip_max == '50' else pip_max
    tip_name = 'opentrons_96_tiprack_'+pip_max+'ul'

    tiprack_slots = ['1', '4', '7', '10']
    tips = [protocol.load_labware(tip_name, slot)
            for slot in tiprack_slots]

    pipette = protocol.load_instrument(
        pip_model, pip_mount, tip_racks=tips)

    source_plate = protocol.load_labware(sp_type, '2', 'Source Labware')

    dest_plate = protocol.load_labware(dp_type, '3', 'Destination Labware')

    data = [row.split(',') for row in volumes_csv.strip().splitlines() if row]

    if tip_reuse == 'never':
        pipette.pick_up_tip()
    for src_well, vol, dest_well in data[1:]:
        vol = float(vol)
        dest_well = dest_well.strip()
        pipette.transfer(
            vol,
            source_plate[src_well],
            dest_plate[dest_well],
            new_tip=tip_reuse
        )
    if tip_reuse == 'never':
        pipette.drop_tip()

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
    filename = f"detailed_action_json/7a3e4b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)