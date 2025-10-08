import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/05f673/05f673.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'Cell Normalization',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(protocol: protocol_api.ProtocolContext):
    [p1000mnt, transfer_csv, labwareType, prefill] = get_values(  # noqa: F821
        'p1000mnt', 'transfer_csv', 'labwareType', 'prefill')

    # load labware
    reservoir = protocol.load_labware('agilent_1_reservoir_290ml', '4')
    buffer = reservoir['A1']

    source = [protocol.load_labware(labwareType, slot)
              for slot in ['1', '2', '3', '5']]
    outputs = [protocol.load_labware(labwareType, slot)
               for slot in ['6', '8', '9', '11']]

    tipracks1000 = [protocol.load_labware('opentrons_96_tiprack_1000ul', '7')]
    if prefill:
        if labwareType == 'corning_96_wellplate_360ul_flat':
            tipracks300 = [
                protocol.load_labware('opentrons_96_tiprack_300ul', '10')]
            mnt300 = 'left' if p1000mnt == 'right' else 'right'
            m300 = protocol.load_instrument(
                'p300_multi_gen2', mnt300, tip_racks=tipracks300)
        else:
            raise Exception('The prefill volume cannot be selected  with 24-well plate option.')

    # load pipette
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', p1000mnt, tip_racks=tipracks1000)

    def tip_pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            protocol.set_rail_lights(False)
            protocol.pause("Replace the tips")
            pip.reset_tipracks()
            protocol.set_rail_lights(True)
            pip.pick_up_tip()

    # process csv
    csv_data = [
        el.split(',') for el in transfer_csv.strip().splitlines() if el][1:]

    # optional prefill (should be caught by exception above if not working)
    if prefill:
        tip_pick_up(m300)
        dest96plate = [well for plate in outputs for well in plate.rows()[0]]
        for well in dest96plate:
            m300.transfer(prefill, buffer, well, new_tip='never')
        m300.drop_tip()

    # transfer buffer - chunk volumes to 1000
    protocol.set_rail_lights(True)
    max_vol = 1000
    lst_of_lsts = []
    chunks = []
    tmp = 0
    for line in csv_data:
        destPlate = int(line[2]) - 1
        destWell = line[3]
        volBuff = int(line[4])
        x = [destPlate, destWell, volBuff]
        if tmp + volBuff <= max_vol:
            chunks.append(x)
            tmp += volBuff
        else:
            if chunks:
                lst_of_lsts.append(chunks)
            chunks = [x]
            tmp = volBuff

    lst_of_lsts.append(chunks)

    tip_pick_up(p1000)

    for lst in lst_of_lsts:
        totalVol = 0
        for el in lst:
            totalVol += el[2]
        p1000.aspirate(totalVol, buffer)
        for el in lst:
            p1000.dispense(el[2], outputs[el[0]][el[1]])

    p1000.drop_tip()

    # transfer samples
    for line in csv_data:
        srcPlate = int(line[0]) - 1
        srcWell = line[1]
        destPlate = int(line[2]) - 1
        destWell = line[3]
        volSamp = int(line[5])

        tip_pick_up(p1000)
        p1000.mix(3, 1000, source[srcPlate][srcWell], rate=2.0)
        p1000.aspirate(volSamp, source[srcPlate][srcWell])
        p1000.dispense(volSamp, outputs[destPlate][destWell])
        p1000.drop_tip()

    protocol.set_rail_lights(False)

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
    filename = f"detailed_action_json/05f673.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)