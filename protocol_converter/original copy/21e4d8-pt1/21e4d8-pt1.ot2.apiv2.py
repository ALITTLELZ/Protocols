import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/21e4d8-pt1/21e4d8-pt1.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Twist Library Prep || Part 1: Fragmentation & Repair',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [p20type, p300type, num, cold, dplate, dna, mm] = get_values(  # noqa: F821
        'p20type', 'p300type', 'num', 'cold', 'dplate', 'dna', 'mm')

    # Variables; these are injected when downloaded from the protocol
    # Library. Listed here for ease of access.
    p20name = p20type  # should be string (ex. 'p20_multi_gen2')
    p300name = p300type  # should be string (ex. 'p300_multi')
    num_samps = num  # should be int, 1-96
    cold_mod = cold  # if using module to keep samples cold
    dest_plate_type = dplate  # should be string (name of labware)
    src_plate_type = dna  # should be string (name of labware)
    mm_labware_type = mm  # should be string (name of labware)

    # Load labware and pipettes
    p20tips = [protocol.load_labware('opentrons_96_tiprack_20ul', '6')]
    p300tips = [protocol.load_labware('opentrons_96_tiprack_300ul', '3')]
    p20 = protocol.load_instrument(p20name, 'left', tip_racks=p20tips)
    p300 = protocol.load_instrument(p300name, 'right', tip_racks=p300tips)

    src_plate = protocol.load_labware(src_plate_type, '1')
    mm_labware = protocol.load_labware(mm_labware_type, '2')

    if cold_mod == 'None':
        dest_plate = protocol.load_labware(dest_plate_type, '7')
    elif cold_mod == 'Thermocycler':
        tc_mod = protocol.load_module('Thermocycler Module')
        dest_plate = tc_mod.load_labware(dest_plate_type)
        tc_mod.open_lid()
        tc_mod.set_block_temperature(4)
    else:
        temp_mod = protocol.load_module(cold_mod, '7')
        dest_plate = temp_mod.load_labware(dest_plate_type)
        temp_mod.set_temperature(4)

    # Create variables based on the number of samples
    num_cols = math.ceil(num_samps/8)
    src_wells = src_plate.wells()[:num_samps]
    src_cols = src_plate.rows()[0][:num_cols]
    dest_wells = dest_plate.wells()[:num_samps]
    dest_cols = dest_plate.rows()[0][:num_cols]
    mm_wells_holder = [[mm_labware[w]]*32 for w in ['A1', 'A2', 'A3']]
    mm_wells = [d for dd in mm_wells_holder for d in dd]

    p20src = src_cols if p20name.split('_')[1] == 'multi' else src_wells
    [p20dest,
     p300dest] = [
        dest_cols if pip.split('_')[1] == 'multi' else dest_wells for pip in [
            p20name,
            p300name]
            ]

    # Transfer 40uL of enzymatic fragmentation master mix to each well
    protocol.comment('Transferring 40uL of Enzymatic Fragmentation Master Mix')
    p300.pick_up_tip()
    for src, dest in zip(mm_wells, p300dest):
        p300.aspirate(40, src)
        p300.dispense(40, dest)
        p300.blow_out()
    p300.drop_tip()

    # Transfer 10uL of sample to each well and mix
    protocol.comment('Transferring 10uL of sample and mixing...')
    for src, dest in zip(p20src, p20dest):
        p20.pick_up_tip()
        p20.aspirate(10, src)
        p20.dispense(10, dest)
        p20.mix(5, 20, dest)
        p20.blow_out()
        p20.drop_tip()

    protocol.comment('Protocol complete.  Please move plate to thermocycler & prepare for step 2.')

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
    filename = f"detailed_action_json/21e4d8-pt1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)