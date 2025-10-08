import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/4471ba/4471ba.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Plate Filling (Flipped)',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [mnt, vol, cols] = get_values(  # noqa: F821
        'mnt', 'vol', 'cols')

    # load labware and pipettes
    p300 = protocol.load_instrument('p300_multi_gen2', mount=mnt)
    tips = protocol.load_labware('opentrons_300ul_tiprack_flipped', '4')
    res = protocol.load_labware('beckmancoulter_8_reservoir_19000ul', '10')

    plate1, plate2 = [
        protocol.load_labware(
            'simport_96_wellplate_flipped', s) for s in ['8', '2']
            ]

    # Create variable lists based on number of columns
    reagent = res.wells()[:cols]
    tip_list = [[tips[j+'1'], tips[j+'5']] for j in 'ABCDEFGH'][:cols]
    well_list = [
        [plate1[j+'1'], plate2[j+'1'],
         plate1[j+'5'], plate2[j+'5']] for j in 'ABCDEFGH'][:cols]

    for re, tip, wells in zip(reagent, tip_list, well_list):
        p300.pick_up_tip(tip[0])
        for well in wells[:2]:
            p300.aspirate(vol, re)
            p300.dispense(vol, well)
        p300.drop_tip()
        p300.pick_up_tip(tip[1])
        for well in wells[2:]:
            p300.aspirate(vol, re)
            p300.dispense(vol, well)
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
    filename = f"detailed_action_json/4471ba.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)