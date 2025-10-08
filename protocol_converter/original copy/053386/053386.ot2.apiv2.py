import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/053386/053386.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'Human Islets - Preprocessing',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [m300_mount] = get_values(  # noqa: F821
        "m300_mount")

    # modules
    temp_mod = ctx.load_module('temperature module gen2', 1)
    temp_mod.set_temperature(25)

    # labware
    temp_plate = temp_mod.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       label='sample plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 2)

    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [3, 4, 5, 6, 7, 8, 9, 10, 11]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    # mapping
    trash = ctx.loaded_labwares[12].wells()[0].top()

    wash_buff = reservoir.wells()[0]
    trypsin = reservoir.wells()[1]
    pbs = reservoir.wells()[2]
    meoh = reservoir.wells()[3]

    sample_cols = temp_plate.rows()[0]

    def remove_super(vol):
        for col in sample_cols:
            pick_up()
            m300.aspirate(vol, col)
            m300.dispense(vol, trash)
            m300.drop_tip()

    def pick_up():
        try:
            m300.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause(f"Replace empty tip rack for {m300}")
            m300.reset_tipracks()
            m300.pick_up_tip()

    # protocol
    ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
    remove_super(80)

    ctx.comment('\n---------------ADD TRYPSIN----------------\n\n')
    pick_up()
    for col in sample_cols:
        m300.aspirate(100, trypsin)
        m300.dispense(100, col.top())
    m300.drop_tip()

    temp_mod.set_temperature(37)
    ctx.delay(minutes=7)

    for col in sample_cols:
        pick_up()
        m300.mix(12, 80, col)
        m300.drop_tip()

    temp_mod.set_temperature(25)

    ctx.comment('\n---------------ADD PBS----------------\n\n')
    for col in sample_cols:
        pick_up()
        m300.aspirate(100, pbs)
        m300.dispense(100, col)
        m300.mix(5, 150, col)
        m300.drop_tip()

    ctx.pause("Spin down plate at 400g for 5 minutes.")

    ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
    remove_super(150)

    ctx.comment('\n---------------ADD PBS----------------\n\n')
    for col in sample_cols:
        pick_up()
        m300.aspirate(100, pbs)
        m300.dispense(100, col)
        m300.mix(5, 112, col)
        m300.drop_tip()

    ctx.pause("Spin down plate at 400g for 5 minutes.")

    ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
    remove_super(100)

    ctx.comment('\n---------------ADD MEOH----------------\n\n')
    pick_up()
    for col in sample_cols:
        m300.aspirate(100, meoh)
        m300.dispense(100, col.top())
    m300.drop_tip()

    ctx.pause("""
                Incubate at -20C for 5 minutes.
                Spin down plate at 800g for 5 minutes at 4C.
                """)

    ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
    remove_super(100)

    ctx.comment('\n---------------ADD WASH BUFFER----------------\n\n')
    for col in sample_cols:
        pick_up()
        m300.aspirate(200, wash_buff)
        m300.dispense(200, col)
        m300.mix(3, 180, col)
        m300.drop_tip()

    ctx.pause("""Pellet cells at 800g for 6 minutes.
                 Place back on deck to remove 180ul of super.""")

    ctx.comment('\n---------------REMOVE SUPER----------------\n\n')
    remove_super(180)

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
    filename = f"detailed_action_json/053386.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)