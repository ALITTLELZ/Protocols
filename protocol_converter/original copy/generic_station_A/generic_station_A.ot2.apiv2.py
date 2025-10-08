import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/generic_station_A/generic_station_A.ot2.apiv2.py"

metadata = {
    'protocolName': 'Generic Sample Plating Protocol (Station A)',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.5'
}


def run(protocol):
    [num_samples, samp_vol, plate_type,
     tube_type, pip_type] = get_values(  # noqa: F821
        'num_samples', 'samp_vol', 'plate_type',
        'tube_type', 'pip_type')

    # load labware and pipettes
    pip_name, tip_name = pip_type.split()
    tips = [protocol.load_labware(tip_name, '3')]
    pipette = protocol.load_instrument(pip_name, 'right', tip_racks=tips)

    dest_plate = protocol.load_labware(plate_type, '2')

    t_slots = ['1', '4', '7', '10', '5', '8', '11']
    src_tubes = [protocol.load_labware(tube_type, s) for s in t_slots]

    # define source/dest wells
    if num_samples > 96:
        raise Exception('The number of samples should be 1-96.')

    dest_wells = dest_plate.wells()[:num_samples]
    src_wells = [t for tube in src_tubes for t in tube.wells()][:num_samples]
    air_vol = round(samp_vol*0.1)

    for src, dest in zip(src_wells, dest_wells):
        pipette.pick_up_tip()
        pipette.transfer(samp_vol, src, dest, new_tip='never', air_gap=air_vol)
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
    filename = f"detailed_action_json/generic_station_A.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)