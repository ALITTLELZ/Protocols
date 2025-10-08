import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0fa015/0fa015.ot2.apiv2.py"

from opentrons import types

metadata = {
    'protocolName': 'Plate Filling QE in NEST Plate',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [piptype, pipmnt, num_plates] = get_values(  # noqa: F821
        'piptype', 'pipmnt', 'num_plates')

    # load labware and pipettes
    pip_name, tip_name = piptype.split()
    tips = protocol.load_labware(tip_name, '10')
    pip = protocol.load_instrument(pip_name, pipmnt, tip_racks=[tips])
    res = protocol.load_labware('nest_12_reservoir_15ml', '11')
    mm1 = [res['A1']]*5+[res['A2']]*4
    num_plates += 1
    plates = [
        protocol.load_labware(
            'nest_96_wellplate_100ul_pcr_full_skirt',
            s) for s in range(1, num_plates)]

    # max_vol = 15 if pip_name == 'p20_multi_gen2' else 180

    # distribute 10ul of QE
    pip.pick_up_tip()
    for plate, mm, r in zip(plates, mm1, range(1, 10)):
        wells = plate.rows()[0]
        disp_vol = 12
        protocol.comment(f'Distributing 10ul to plate {r}...')
        for well in wells:
            pip.aspirate(10, mm)
            protocol.max_speeds['X'] = 25
            pip.move_to(mm.top().move(types.Point(x=3.5, y=0, z=-4)))
            pip.move_to(mm.top().move(types.Point(x=-3.5, y=0, z=-2)))
            protocol.max_speeds['X'] = None
            pip.dispense(disp_vol, well)
            pip.blow_out(well)
            pip.aspirate(2, well.top())
    pip.drop_tip()

    protocol.comment('Protocol complete.')

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
    filename = f"detailed_action_json/0fa015.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)