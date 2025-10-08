import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/5f37a2/5fe7a2.ot2.apiv2.py"

metadata = {
    'protocolName': 'Nucleic Acid Purification',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}


def run(protocol):

    # load labware and pipettes
    tips = [protocol.load_labware(
        'opentrons_96_tiprack_300ul', str(s)) for s in range(1, 8)]

    dwp500 = protocol.load_labware(
        'eppendorf_96_deepwellplate_500ul', '9', 'Eppendorf DWP 500ul')

    corning = protocol.load_labware('corning_96_wellplate_360ul_flat', '8')

    magdeck = protocol.load_module('magdeck', '10')
    magplate = magdeck.load_labware(
        'eppendorf_96_deepwellplate_2000ul', 'Eppendorf DWP 2000ul')
    maght = 14.94

    res = protocol.load_labware('usascientific_12_reservoir_22ml', '11')

    # p50 = protocol.load_instrument('p50_single', 'right', tip_racks=tips)
    p300 = protocol.load_instrument('p300_multi', 'left', tip_racks=tips)

    # transfers
    def ctx_trans(vol1, src, dest, vol2, reps):
        p300.pick_up_tip()
        p300.transfer(vol1, src, dest, new_tip='never')
        if vol2 > 0:
            p300.mix(reps, vol2, dest)
        p300.blow_out(dest.top())
        p300.drop_tip()

    ctx_trans(90, res['A1'], dwp500['A1'], 70, 10)

    ctx_trans(120, res['A2'], dwp500['A1'], 150, 5)

    protocol.comment('Pausing operation for 2 minutes.')
    protocol.delay(minutes=2)

    ctx_trans(120, res['A3'], dwp500['A1'], 250, 5)

    ctx_trans(30, res['A4'], dwp500['A1'], 50, 5)

    magdeck.engage(height=maght)

    protocol.comment('Pausing operation for 10 minutes.')
    protocol.delay(minutes=10)

    ctx_trans(250, dwp500['A1'], magplate['A1'], 0, 0)

    # ctx_trans(50, res['A5'], magplate['A1'], 200, 5)
    p300.pick_up_tip()
    p300.transfer(50, res['A5'], magplate['A1'], new_tip='never')
    p300.mix(5, 200, magplate['A1'])
    p300.blow_out(magplate['A1'].top())

    protocol.comment('Pausing operation for 10 minutes.')
    protocol.delay(minutes=10)

    p300.aspirate(250, magplate['A1'])
    p300.drop_tip()

    ctx_trans(100, res['A6'], magplate['A1'], 75, 5)

    protocol.pause('Pausing. Make sure a Corning 360ul plate is in slot 8  before resuming. When ready, click RESUME.')

    ctx_trans(100, res['A7'], magplate['A1'], 70, 5)

    protocol.comment('Pausing operation for 10 minutes.')
    protocol.delay(minutes=10)

    ctx_trans(100, magplate['A1'], corning['A1'], 0, 0)

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
    filename = f"detailed_action_json/5f37a2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)