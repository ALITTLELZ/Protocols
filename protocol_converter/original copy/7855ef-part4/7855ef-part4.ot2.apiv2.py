import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7855ef-part4/7855ef-part4.ot2.apiv2.py"

import math
from opentrons.types import Point

metadata = {
    'protocolName': 'Agriseq Library Prep Part 4 - Pooling',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(protocol):
    [num_samp, p20_mount, tip_disp] = get_values(  # noqa: F821
        "num_samp", "p20_mount", "tip_disp")

    if not 1 <= num_samp <= 384:
        raise Exception("Enter a sample number between 1-384")
    tip_counter = 0
    dropped_tip = 0

    num_col = math.ceil(num_samp/8)
    num_plates = math.ceil(num_col/12)

    # load labware
    pool_plate = protocol.load_labware(
        'customendura_96_wellplate_200ul', '1', label='Pool Plate')
    reaction_plate = protocol.load_labware(
        'microamp_384_wellplate_100ul', '5', label='Reaction Plate')
    tiprack20 = [
        protocol.load_labware(
            'opentrons_96_filtertiprack_20ul',
            str(slot)) for slot in [7, 8, 9, 10][:num_plates]]

    tiprack200 = [
        protocol.load_labware('opentrons_96_filtertiprack_200ul', '11')
        ]

    # load instruments
    m20 = protocol.load_instrument(
        'p20_multi_gen2', p20_mount, tip_racks=tiprack20)
    p300_mount = 'right' if p20_mount == 'left' else 'left'
    m300 = protocol.load_instrument(
        'p300_multi_gen2', p300_mount, tip_racks=tiprack200)

    tips = [well for tipbox in tiprack20 for well in tipbox.rows()[0]]

    def pick_up_20():
        nonlocal tip_counter
        m20.pick_up_tip()
        tip_counter += 1

    def trash_tip():
        nonlocal tip_counter
        nonlocal dropped_tip
        if tip_counter < 13:
            m20.drop_tip()
        else:
            m20.drop_tip(tips[dropped_tip])
            dropped_tip += 1

    def touchtip(pip, well):
        knock_loc = well.top(z=-1).move(
                    Point(x=-(well.diameter/2.25)))
        knock_loc2 = well.top(z=-1).move(
                    Point(x=(well.diameter/2.25)))
        pip.move_to(knock_loc)
        pip.move_to(knock_loc2)

    protocol.comment(
        f'This protocol is for {num_samp} samples.  Please prepare reagents accordingly'
    )

    # pool each row of plates
    airgap = 2
    reaction_plate_cols = [col for j in range(2) for i in range(2)
                           for col in reaction_plate.rows()[i][j::2]][:num_col]
    for i, well in enumerate(reaction_plate_cols):
        dest = pool_plate.rows()[0][i//12]
        pick_up_20()
        m20.aspirate(5, well)
        touchtip(m20, well)
        m20.air_gap(airgap)
        m20.dispense(airgap, dest.top())
        m20.dispense(5, dest)
        m20.blow_out()
        touchtip(m20, dest)
        m20.return_tip() if tip_disp else trash_tip()
        protocol.comment('\n')

    airgap = 5
    final_dest = pool_plate['A12']
    mix = False
    for well in (pool_plate.rows()[0][:num_plates]):
        m300.pick_up_tip()
        m300.mix(3, 50, well)
        m300.aspirate(45, well)
        touchtip(m300, well)
        m300.air_gap(airgap)
        m300.dispense(airgap, final_dest.top(-2))
        m300.dispense(45, final_dest)
        if mix:
            m300.mix(3, 80, final_dest)
        m300.blow_out()
        touchtip(m300, final_dest)
        m300.drop_tip()
        mix = True

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
    filename = f"detailed_action_json/7855ef-part4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)