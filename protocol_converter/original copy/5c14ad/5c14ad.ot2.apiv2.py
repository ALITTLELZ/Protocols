import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5c14ad/5c14ad.ot2.apiv2.py"

metadata = {
    'protocolName': 'Lysis Pre-Fill (Salmonella/Listeria)',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(protocol):
    [lysis, pip_type, pip_mnt, no_plates, tip_no] = get_values(  # noqa: F821
        'lysis', 'pip_type', 'pip_mnt', 'no_plates', 'tip_no')

    # load labware
    tips = protocol.load_labware('generic_96_tiprack_200ul', '1', 'Tips')
    res = protocol.load_labware('nest_1_reservoir_195ml', '2', 'Reservoir')
    p300 = protocol.load_instrument(pip_type, pip_mnt)

    plates = []
    plate_start = 3
    for i in range(no_plates):
        plates.append(
            protocol.load_labware(
                'custom_96_tubeholder_500ul',
                str(plate_start),
                'Plate '+str(i+1)
                )
            )
        plate_start += 1

    # create wells/columns for pipette type
    for x in range(len(plates)):
        if pip_type == 'p300_single':
            plates[x] = plates[x].wells()
        else:
            plates[x] = plates[x].rows()[0]

    # pick up tip
    tip_spot = 'A'+str(tip_no)
    p300.pick_up_tip(tips[tip_spot])

    # transfer according to lysis
    vol = int(lysis)

    pip_vol = 0

    for plate in plates:
        for w in plate:
            if pip_vol == 0:
                p300.aspirate(vol, res['A1'])
                pip_vol += vol
            p300.dispense(vol/2, w)
            pip_vol -= vol/2

    p300.drop_tip()

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
    filename = f"detailed_action_json/5c14ad.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)