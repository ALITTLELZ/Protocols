import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/030dd8-amplify/amplify.ot2.apiv2.py"

from opentrons import protocol_api
from opentrons.types import Point
import math

metadata = {
    'protocolName': '3. Illumina COVIDSeq - Amplify cDNA',
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
    cdna_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '2', 'cDNA plate')
    reagent_plate = tempdeck.load_labware(
        'quantgene_96_aluminumblock_200ul', 'reagent plate')
    cov1_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '1', 'COV1 plate')
    cov2_plate = ctx.load_labware('agilentwithnonskirted_96_wellplate_200ul',
                                  '5', 'COV2 plate')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['3', '6']]

    # load P300M pipette
    m20 = ctx.load_instrument(
        'p20_multi_gen2', 'right', tip_racks=tips20)

    # reagents and variables
    mm1 = reagent_plate.rows()[0][2:4]
    mm2 = reagent_plate.rows()[0][4:6]

    vol_mm = 20.0
    vol_cdna = 5.0
    num_cols = math.ceil(num_samples/8)
    ref_well = cdna_plate.wells()[0]
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

    for mm, cov_plate in zip([mm1, mm2], [cov1_plate, cov2_plate]):
        pick_up(m20)
        for i, d in enumerate(cov_plate.rows()[0][:num_cols]):
            mm_source = mm[i//6]
            m20.aspirate(vol_mm, mm_source.bottom(0.5))
            slow_withdraw(m20, mm_source)
            m20.dispense(vol_mm, d.bottom(0.5))
            wick(m20, d)

        for s, d in zip(cdna_plate.rows()[0][:num_cols],
                        cov_plate.rows()[0][:num_cols]):
            if not m20.has_tip:
                pick_up(m20)
            m20.aspirate(vol_cdna, s.bottom(0.5))
            slow_withdraw(m20, s)
            m20.dispense(vol_cdna, d.bottom(2))
            slow_withdraw(m20, d)
            if TEST_MODE_DROP:
                m20.return_tip()
            else:
                m20.drop_tip()

    ctx.comment('\n\n\n\nProtocol complete.\nSeal and shake at 1600 rpm for 1  minute. Centrifuge at 1000 x g for 1 minute. Place in the preprogrammed \
thermal cycler and run the COVIDSeq PCR program.\n\n\n\n')

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
    filename = f"detailed_action_json/030dd8-amplify.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)