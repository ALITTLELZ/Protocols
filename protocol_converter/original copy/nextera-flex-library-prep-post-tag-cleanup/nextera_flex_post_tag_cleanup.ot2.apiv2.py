import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/nextera-flex-library-prep-post-tag-cleanup/nextera_flex_post_tag_cleanup.ot2.apiv2.py"

import math
from opentrons.types import Point

metadata = {
    'protocolName': 'Nextera DNA Flex NGS Library Prep: Post Tagmentation  Cleanup',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.2'
}


def run(ctx):

    [number_of_samples_to_process, p300_type,
        p300_mount] = get_values(  # noqa: F821
            'number_of_samples_to_process', 'p300_type', 'p300_mount')

    # load labware and modules
    magdeck = ctx.load_module('magdeck', '1')
    mag_plate = magdeck.load_labware(
        'biorad_96_wellplate_200ul_pcr', '1')
    res12 = ctx.load_labware(
        'usascientific_12_reservoir_22ml', '3', 'reagent reservoir')

    twb = [chan.bottom(5) for chan in res12.wells()[:2]]
    liquid_waste = [chan.top() for chan in res12.wells()[10:]]

    # check:
    if number_of_samples_to_process > 96 or number_of_samples_to_process < 1:
        raise Exception('Invalid number of samples to process (must be between  1 and 96).')

    num_cols = math.ceil(number_of_samples_to_process/8)
    num_300_racks = math.ceil((num_cols*6)/12)
    slots300 = [str(slot) for slot in range(5, 5+num_300_racks)]
    tips300 = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot)
        for slot in slots300
    ]

    # pipettes
    pip300 = ctx.load_instrument(p300_type, p300_mount, tip_racks=tips300)
    if p300_type == 'p300_multi':
        samples300 = mag_plate.rows()[0][:num_cols]
    else:
        samples300 = mag_plate.wells()[:number_of_samples_to_process]
    pip300.flow_rate.aspirate = 75
    pip300.flow_rate.dispense = 90

    magdeck.engage(height=18)
    ctx.delay(minutes=3, msg='Incubating beads on magnet for 3 minutes.')

    # remove and discard supernatant
    for s in samples300:
        pip300.pick_up_tip()
        pip300.transfer(65, s.bottom(1), liquid_waste[0], new_tip='never')
        pip300.blow_out()
        pip300.drop_tip()

    # TWB washes 3x
    count = 0
    total_twb = 96*3
    for wash in range(3):
        magdeck.disengage()

        # resuspend beads in TWB
        for i, s in enumerate(samples300):
            ind = (count*len(twb))//total_twb
            count += 1

            side = i % 2 if p300_type == 'multi' else math.floor(i/8) % 2
            angle = 1 if side == 0 else -1
            disp_loc = s.bottom().move(
                Point(x=0.85*(s.diameter/2)*angle, y=0, z=3))
            pip300.pick_up_tip()
            pip300.aspirate(100, twb[ind])
            pip300.move_to(s.center())
            pip300.dispense(100, disp_loc)
            pip300.mix(10, 80, disp_loc)
            pip300.drop_tip()

        magdeck.engage(height=18)

        if wash < 2:
            ctx.delay(
                minutes=3, msg='Incubating beads on magnet for 3 minutes')
            # remove and discard supernatant
            for s in samples300:
                pip300.pick_up_tip()
                pip300.transfer(
                    120, s.bottom(1), liquid_waste[wash], new_tip='never')
                pip300.blow_out()
                pip300.drop_tip()

    ctx.comment('Seal the plate, and keep on the magnetic module. The TWB  remains in the wells to prevent overdrying of the beads')

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
    filename = f"detailed_action_json/nextera-flex-library-prep-post-tag-cleanup.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)