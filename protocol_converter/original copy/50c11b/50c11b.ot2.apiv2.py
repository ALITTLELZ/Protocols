import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/50c11b/50c11b.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Custom PCR Setup',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(protocol):
    [protoType, p1num, p2num, p3num, p4num, mnt20] = get_values(  # noqa: F821
     'protoType', 'p1num', 'p2num', 'p3num', 'p4num', 'mnt20')

    # load labware
    tips20 = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul', s) for s in [8, 11, 10, 7]]
    tipLocs = [r for rack in tips20 for r in rack.rows()[0]]

    m20 = protocol.load_instrument(
        'p20_multi_gen2', mnt20, tip_racks=tips20)

    plates = [
        protocol.load_labware(
            'kingfisher_96_deepwell_plate_2ml',
            s, f'Sample Plate {idx+1}') for idx, s in enumerate(
                [4, 5, 6, 3])]

    finalPlate = protocol.load_labware(
        'appliedbiosystems_384_wellplate_40ul', '1', 'Destination Plate')

    # Create and update variables
    sampNums = [p1num, p2num, p3num, p4num]
    for idx, num in enumerate(sampNums):
        if not 0 <= num <= 96:
            raise Exception(f'Number of Samples for Plate {idx+1} is: {num}.  Please select a valid value between 1 and 96.')

    sampCols = [math.ceil(n/8) for n in sampNums]

    destWells = [finalPlate.rows()[r][w:w+n] for r, w, n in zip(
        [0, 0, 1, 1], [0, 12, 0, 12], sampCols)]

    tVol, mVol = [float(n) for n in protoType.split(' ')]

    # Begin protocol; Transfer tVol and mix with mVol
    returnTips = False
    rtv = 0
    for plate, col, dest in zip(plates, sampCols, destWells):
        protocol.comment(f'\nTransferring Samples from {plate}\n')

        for s, d in zip(plate.rows()[0][:col], dest):
            m20.pick_up_tip()
            m20.mix(3, tVol, s)
            m20.aspirate(tVol, s)
            m20.dispense(tVol, d)
            m20.mix(5, mVol, d)
            m20.blow_out()
            if returnTips:
                m20.drop_tip(tipLocs[rtv])
                rtv += 1
            else:
                m20.drop_tip()

        returnTips = True

    protocol.comment('\nProtocol Complete!')

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
    filename = f"detailed_action_json/50c11b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)