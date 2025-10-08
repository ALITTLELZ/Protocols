import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5c24e2/5c24e2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Plate Filling Sample in AB 384 Well Plate',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [pip_type, pipmnt, s_vol, sec_plate, p384] = get_values(  # noqa: F821
        'pip_type', 'pipmnt', 's_vol', 'sec_plate', 'p384')

    # load labware and pipettes
    tips = [
        protocol.load_labware(
            pip_type.split()[1], s) for s in range(1, 11, 3)]
    pip = protocol.load_instrument(pip_type.split()[0], pipmnt, tip_racks=tips)
    dnaPlates = [
        protocol.load_labware(
            'nest_96_wellplate_100ul_pcr_full_skirt',
            s) for s in range(2, 12, 3)]

    mmPlates = [
        protocol.load_labware(p384, s) for s in ['3', '6']]
    plate1 = [mmPlates[0][ltr+str(i)] for i in range(1, 13) for ltr in 'AB']
    plate2 = [mmPlates[0][ltr+str(i)] for i in range(13, 25) for ltr in 'AB']
    plate3 = [mmPlates[1][ltr+str(i)] for i in range(1, 13) for ltr in 'AB']
    plate4 = [mmPlates[1][ltr+str(i)] for i in range(13, 25) for ltr in 'AB']

    asp_vol = s_vol * 2

    for s_plate, d_plate in zip(dnaPlates[:2], [plate1, plate2]):
        dest1 = d_plate[::2]
        dest2 = d_plate[1::2]
        for src, d1, d2 in zip(s_plate.rows()[0], dest1, dest2):
            pip.pick_up_tip()
            pip.aspirate(asp_vol, src)
            pip.dispense(s_vol, d1)
            pip.dispense(s_vol, d2)
            pip.drop_tip()

    if sec_plate == 'yes':
        for s_plate, d_plate in zip(dnaPlates[2:], [plate3, plate4]):
            dest1 = d_plate[::2]
            dest2 = d_plate[1::2]
            for src, d1, d2 in zip(s_plate.rows()[0], dest1, dest2):
                pip.pick_up_tip()
                pip.aspirate(asp_vol, src)
                pip.dispense(s_vol, d1)
                pip.dispense(s_vol, d2)
                pip.drop_tip()

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
    filename = f"detailed_action_json/5c24e2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)