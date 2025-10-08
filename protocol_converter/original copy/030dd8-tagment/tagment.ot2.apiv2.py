import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/030dd8-tagment/tagment.ot2.apiv2.py"

from opentrons import protocol_api
from opentrons.types import Point
import math

metadata = {
    'protocolName': '4. Illumina COVIDSeq - Tagment PCR Amplicons',
    'author': 'Opentrons <protocols@opentrons.com>',
    'apiLevel': '2.13'
}

TEST_MODE_TEMP = True
TEST_MODE_DROP = True

num_samples = 96


def run(ctx):

    # tuning parameters
    ctx.max_speeds['X'] = 200
    ctx.max_speeds['Y'] = 200

    # modules
    tempdeck = ctx.load_module('temperature module gen2', '4')
    magdeck = ctx.load_module('magnetic module gen2', '7')
    if not TEST_MODE_TEMP:
        tempdeck.set_temperature(4)
    magdeck.disengage()

    # labware
    tag1_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '2', 'TAG1 plate')
    reagent_plate = tempdeck.load_labware(
        'quantgene_96_aluminumblock_200ul', 'reagent plate')
    cov1_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '1', 'COV1 plate')
    cov2_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '5', 'COV2 plate')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3']]
    tips200 = [
        ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
        for slot in ['9']]

    # load P300M pipette
    m20 = ctx.load_instrument(
        'p20_multi_gen2', 'right', tip_racks=tips20)
    m300 = ctx.load_instrument(
         'p300_multi_gen2', 'left', tip_racks=tips200)

    # reagents and variables
    mm = reagent_plate.rows()[0][6:8]

    vol_mm = 30.0
    vol_amplicon = 10.0
    num_cols = math.ceil(num_samples/8)
    ref_well = tag1_plate.wells()[0]
    if ref_well.width:
        radius = ref_well.width/2
    else:
        radius = ref_well.diameter/2

    def wick(pip, well, side=1):
        pip.move_to(well.bottom().move(Point(x=side*radius*0.7, z=3)))

    def slow_withdraw(pip, well):
        ctx.max_speeds['A'] = 25
        ctx.max_speeds['Z'] = 25
        pip.move_to(well.top())
        del ctx.max_speeds['A']
        del ctx.max_speeds['Z']

    def pick_up(pip, spot=None):
        if spot:
            pip.pick_up_tip(spot)
        else:
            try:
                pip.pick_up_tip()
            except protocol_api.labware.OutOfTipsError:
                ctx.pause("\n\n\n\nReplace 200ul filtertipracks before  resuming.\n\n\n\n")
                pip.reset_tipracks()
                pip.pick_up_tip()

    for i, cov_plate in enumerate([cov1_plate, cov2_plate]):
        for s, d in zip(cov_plate.rows()[0][:num_cols],
                        tag1_plate.rows()[0][:num_cols]):
            pick_up(m20)
            m20.aspirate(vol_amplicon, s.bottom(0.5))
            slow_withdraw(m20, s)
            m20.dispense(m20.current_volume, d.bottom(0.5))
            if i == 0:
                wick(m20, d)
            else:
                slow_withdraw(m20, d)
            if TEST_MODE_DROP:
                m20.return_tip()
            else:
                m20.drop_tip()

    for i, d in enumerate(tag1_plate.rows()[0][:num_cols]):
        mm_source = mm[i//6]
        pick_up(m300)
        m300.aspirate(vol_mm, mm_source.bottom(0.5))
        slow_withdraw(m300, mm_source)
        m300.dispense(vol_mm, d.bottom(2))
        slow_withdraw(m300, d)
        if TEST_MODE_DROP:
            m300.return_tip()
        else:
            m300.drop_tip()

    ctx.comment('\n\n\n\nSeal and shake at 1600 rpm for 1 minute. Place on  the preprogrammed thermal cycler and run the COVIDSeq TAG program.\n\n\n\n')

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
    filename = f"detailed_action_json/030dd8-tagment.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)