import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0e525c/0e525c.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'droplet digital PCR Prep',
    'author': 'Parrish Payne <parrish.payne@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [m300_mount, m20_mount] = get_values(  # noqa: F821
        'm300_mount', 'm20_mount')

    # labware
    tips200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in [1]]
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
              for slot in [4, 7]]
    dest_plate_1 = ctx.load_labware(
        'biorad_96_wellplate_200ul_pcr', 3, 'Prep Plate')
    # custom labware Biorad semi-skirted 96-well plate held in a ELISA plate
    dest_plate_2 = ctx.load_labware(
        'biorad_96_wellplate_200ul_pcr', 6, 'Final Plate')
    # custom labware Biorad semi-skirted 96-well plate held in a ELISA plate
    source_plate = ctx.load_labware(
        'biorad_96_wellplate_200ul_pcr', 5, 'Reagent Plate')
    # custom labware Biorad semi-skirted 96-well plate held in a ELISA plate

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tips200)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tips20)

    # reagents
    dpbs = source_plate.rows()[0][:8]   # col. 1-8
    article = source_plate.rows()[0][8]  # col. 9
    mas_mix = source_plate.rows()[0][10]  # col. 11
    water = source_plate.rows()[0][11]  # col. 12
    dpbs_destinations = dest_plate_1.rows()[0][:8]  # col. 1-8

    # Helper Functions
    def pick_up(pip):
        """Function that can be used instead of .pick_up_tip() that will pause
        robot when robot runs out of tips, prompting user to replace tips
        before resuming"""
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            ctx.pause("Replace the tips")
            pip.reset_tipracks()
            pip.pick_up_tip()

    def slow_withdraw(pip, well, delay_seconds=1.0):
        pip.default_speed /= 16
        if delay_seconds > 0:
            ctx.delay(seconds=delay_seconds)
        pip.move_to(well.top())
        pip.default_speed *= 16

    # step 1
    for i, d in zip(dpbs, dpbs_destinations):
        pick_up(m300)
        m300.aspirate(180, i.bottom(1.0))
        m300.dispense(180, d.bottom(2))
        m300.drop_tip()

    # step 2
    pick_up(m300)
    m300.aspirate(160, source_plate.rows()[0][7].bottom(1))
    m300.dispense(160, dest_plate_1.rows()[0][7].bottom(2))
    m300.drop_tip()

    # step 3 & 4
    pick_up(m20)
    m20.aspirate(20, article.bottom(1.0))
    slow_withdraw(m20, article)
    m20.dispense(20, dest_plate_1.rows()[0][0].bottom(2.0))
    m20.mix(20, 20)
    slow_withdraw(m20, dest_plate_1.rows()[0][0])
    m20.drop_tip()

    # step 5 serial dilution
    for s, d in zip(dest_plate_1.rows()[0][:6], dest_plate_1.rows()[0][1:7]):
        pick_up(m20)
        m20.aspirate(20, s.bottom(1.0))
        m20.dispense(20, d.bottom(2.0))
        m20.mix(20, 20)
        slow_withdraw(m20, d)
        m20.drop_tip()

    # step 6 & 7
    pick_up(m300)
    m300.aspirate(40, dest_plate_1.rows()[0][5])  # col 6
    slow_withdraw(m300, dest_plate_1.rows()[0][5])
    m300.dispense(40, dest_plate_1.rows()[0][7])  # col 8
    m300.mix(20, 180)
    slow_withdraw(m300, dest_plate_1.rows()[0][7])
    m300.drop_tip()

    # step 8 transfer 20 uL of mas_mix into col 1-5 of dest plate 2
    pick_up(m20)
    for d in dest_plate_2.rows()[0][:5]:
        m20.aspirate(20, mas_mix)
        slow_withdraw(m20, mas_mix)
        m20.dispense(20, d.bottom(2))
        slow_withdraw(m20, d)
    m20.drop_tip()

    # step 9, 10, 11
    for s, d in zip(dest_plate_1.rows()[0][5:8], dest_plate_2.rows()[0][:3]):
        pick_up(m20)
        m20.aspirate(5, s)
        m20.dispense(5, d)
        slow_withdraw(m20, d)
        m20.drop_tip()

    # step 12
    for d in dest_plate_2.rows()[0][3:5]:
        pick_up(m20)
        m20.aspirate(5, water)
        m20.dispense(5, d.bottom(2))
        slow_withdraw(m20, d)
        m20.drop_tip()

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
    filename = f"detailed_action_json/0e525c.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)