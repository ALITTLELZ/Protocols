import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0bd707/0bd707.ot2.apiv2.py"

metadata = {
    'protocolName': 'Media Aliquotting',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}


def run(protocol):
    [num_plates, transfer_vol, p1000_mount] = get_values(  # noqa: F821
        'num_plates', 'transfer_vol', 'p1000_mount')

    # labware
    source = [protocol.load_labware(
                'nest_1_reservoir_195ml', s,
                'liquid reservoir').wells()[0] for s in ['11', '10']]

    tuberacks = [protocol.load_labware(
                    'custom_24_tuberack_2000ul',
                    slot, 'custom tuberack') for slot in [
                        2, 3, 5, 6, 7, 8, 9]][:num_plates]
    tiprack = [
        protocol.load_labware(
            'opentrons_96_tiprack_1000ul',
            slot, '1000µl tiprack') for slot in [1, 4]]

    # pipette
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', p1000_mount, tip_racks=tiprack)

    if transfer_vol > 1000 or transfer_vol < 100:
        raise Exception(
            'The Transfer Volume must be within P1000 range (100-1000).')

    if num_plates < 1 or num_plates > 7:
        raise Exception('The Number of Plates must be between 1 and 7.')

    # perform transfers from source 1
    for tubes in tuberacks[:3]:
        for t in tubes.wells():
            p1000.pick_up_tip()
            for _ in range(2):
                p1000.transfer(
                    transfer_vol, source[0], t, air_gap=50, new_tip='never')
            p1000.air_gap(50)
            p1000.drop_tip()

    # perform transfers from source 2
    for tubes in tuberacks[3:]:
        for t in tubes.wells():
            p1000.pick_up_tip()
            for _ in range(2):
                p1000.transfer(
                    transfer_vol, source[1], t, air_gap=50, new_tip='never')
            p1000.air_gap(50)
            p1000.drop_tip()

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
    filename = f"detailed_action_json/0bd707.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)