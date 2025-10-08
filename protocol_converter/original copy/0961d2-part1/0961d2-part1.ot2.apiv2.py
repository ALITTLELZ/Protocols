import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0961d2-part1/0961d2-part1.ot2.apiv2.py"

metadata = {
    'protocolName': 'plexWell LP384 Part 1',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
    }


def run(protocol):
    [p10_mnt] = get_values(  # noqa: F821
        'p10_mnt')

    # create pipettes and labware
    tips10 = [protocol.load_labware('opentrons_96_filtertiprack_10ul', str(s))
              for s in range(1, 11, 3)]
    pip10 = protocol.load_instrument('p10_multi', p10_mnt, tip_racks=tips10)
    [src1, src2, dst1, dst2] = [
        protocol.load_labware('biorad_96_wellplate_200ul_pcr', s, t)
        for s, t in zip(
            ['2', '5', '3', '6'],
            ['Source 1', 'Source 2', 'Destination 1', 'Destination 2'])]

    res = protocol.load_labware('nest_12_reservoir_15ml', '9')
    buff = res.wells()[0]

    src_plates = src1.rows()[0] + src2.rows()[0]
    dest_plates = dst1.rows()[0] + dst2.rows()[0]

    pip10.flow_rate.aspirate = 3
    pip10.flow_rate.dispense = 6

    # part 1 - add DNA to SBP96 plates
    for src, dest in zip(src_plates, dest_plates):
        pip10.pick_up_tip()
        pip10.transfer(6, src, dest, new_tip='never')
        pip10.mix(5, 6, dest)
        pip10.blow_out(dest.top())
        pip10.drop_tip()

    # part 2 - add Coding buffer
    for dest in dest_plates:
        pip10.pick_up_tip()
        pip10.transfer(5, buff, dest, new_tip='never')
        pip10.mix(10, 5, dest)
        pip10.blow_out(dest.top())
        pip10.drop_tip()

    protocol.comment('Part 1 now complete. Seal plates in slots 3 and 6,  pulse-spin, and run on thermal cycler.')

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
    filename = f"detailed_action_json/0961d2-part1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)