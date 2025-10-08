import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/17cb2d/17cb2d.ot2.apiv2.py"

from opentrons import types

metadata = {
    'protocolName': 'Plate Filling Master Mix in AB 384 Well Plate',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [piptype, pipmnt, num_plates, p384, mm_vol] = get_values(  # noqa: F821
        'piptype', 'pipmnt', 'num_plates', 'p384', 'mm_vol')

    # load labware and pipettes
    pip_name, tip_name = piptype.split()
    tips = protocol.load_labware(tip_name, '10')
    pip = protocol.load_instrument(pip_name, pipmnt, tip_racks=[tips])
    res = protocol.load_labware('nest_12_reservoir_15ml', '11')
    mm1 = [res['A1']]*5+[res['A2']]*4
    mm2 = [res['A11']]*5+[res['A12']]*4
    num_plates += 1
    plates = [
        protocol.load_labware(p384, s) for s in range(1, num_plates)]

    if pip_name == 'p20_multi_gen2':
        max_vol = mm_vol * 2
    else:
        max_vol = (300//mm_vol) * mm_vol

    # distribute mastermix 1
    protocol.comment('Distributing master mix 1...')
    pip.pick_up_tip()
    for plate, mm in zip(plates, mm1):
        wells = plate.rows()[0]
        # disp_vol = 12
        vol_ctr = 0
        for well in wells:
            if vol_ctr < 1:
                pip.aspirate(max_vol, mm)
                vol_ctr = max_vol
                protocol.max_speeds['X'] = 25
                pip.move_to(mm.top().move(types.Point(x=3.5, y=0, z=-4)))
                pip.move_to(mm.top().move(types.Point(x=-3.5, y=0, z=-2)))
                protocol.max_speeds['X'] = None
            # pip.dispense(disp_vol, well)
            pip.dispense(mm_vol, well)
            vol_ctr -= mm_vol
            # pip.blow_out(well)
            # pip.aspirate(2, well.top())
    pip.drop_tip()

    # distribute mastermix 2
    protocol.comment('Distributing master mix 2...')
    pip.pick_up_tip()
    for plate, mm in zip(plates, mm2):
        wells = plate.rows()[1]
        # disp_vol = 12
        vol_ctr = 0
        for well in wells:
            if vol_ctr < 1:
                pip.aspirate(max_vol, mm)
                vol_ctr = max_vol
                protocol.max_speeds['X'] = 25
                pip.move_to(mm.top().move(types.Point(x=3.5, y=0, z=-4)))
                pip.move_to(mm.top().move(types.Point(x=-3.5, y=0, z=-2)))
                protocol.max_speeds['X'] = None
            # pip.dispense(disp_vol, well)
            pip.dispense(mm_vol, well)
            vol_ctr -= mm_vol
            # pip.blow_out(well)
            # pip.aspirate(2, well.top())
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
    filename = f"detailed_action_json/17cb2d.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)