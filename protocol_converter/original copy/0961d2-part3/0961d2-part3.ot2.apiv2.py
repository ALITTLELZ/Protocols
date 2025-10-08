import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0961d2-part3/0961d2-part3.ot2.apiv2.py"

metadata = {
    'protocolName': 'plexWell LP384 Part 3',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
    }


def run(protocol):
    [p10_mnt, num_pl] = get_values(  # noqa: F821
        'p10_mnt', 'num_pl')

    # check for correct number of plates
    if num_pl > 4 or num_pl < 1:
        raise Exception('The number of plates must be between 1 and 4.')

    # create pipettes and tips
    tips10 = [protocol.load_labware('opentrons_96_filtertiprack_10ul', str(s))
              for s in range(1, (3*num_pl-1), 3)]
    pip10 = protocol.load_instrument('p10_multi', p10_mnt, tip_racks=tips10)
    src_plates = [
        protocol.load_labware('biorad_96_wellplate_200ul_pcr', str(s), t)
        for s, t in zip(
            range(2, 3*num_pl, 3),
            ['Plate 1', 'Plate 2', 'Plate 3', 'Plate 4'])]

    dest_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', '3', 'Destination Plate')

    pip10.flow_rate.aspirate = 3
    pip10.flow_rate.dispense = 6
    i = 0

    for plate in src_plates:
        for row in plate.rows()[0]:
            dest = dest_plate.rows()[0][i//6]
            pip10.pick_up_tip()
            for _ in range(2):
                pip10.transfer(9, row, dest, new_tip='never')
                pip10.mix(2, 8, dest)
                pip10.blow_out(dest.top())
            pip10.drop_tip()
            i += 1

    protocol.comment('If bubbles are present, please centrifuge to remove  bubbles before proceeding to Part 4.')

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
    filename = f"detailed_action_json/0961d2-part3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)