import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/053386-pt3/053386-pt3.ot2.apiv2.py"

from opentrons import protocol_api

metadata = {
    'protocolName': 'Human Islets - RT Barcoding',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [m20_mount, m300_mount] = get_values(  # noqa: F821
        "m20_mount", "m300_mount")

    # modules
    temp_mod = ctx.load_module('temperature module gen2', 1)
    temp_mod.set_temperature(25)

    # labware
    samp_plate = temp_mod.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       1)

    barcode_plate = ctx.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       2,
                                       label='barcode plate')

    pcr_strip_plate = ctx.load_labware(
                                       'opentrons_96_aluminumblock_generic_pcr_strip_200ul',  # noqa: E501
                                       3,
                                       label='reagent plate')

    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 4)

    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [5, 6, 7, 8, 9]]

    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
              for slot in [10, 11]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tips20)

    # mapping
    trash = ctx.loaded_labwares[12].wells()[0].top()

    wash_buff = reservoir.wells()[0]
    smart_seq_3 = pcr_strip_plate.wells()[0]
    pool_res_well = reservoir.wells()[-2]

    samp_cols = samp_plate.rows()[0]
    barcode_cols = barcode_plate.rows()[0]

    def remove_super(vol):
        for col in samp_cols:
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
    ctx.comment('\n---------------ADD BARCODE----------------\n\n')
    for s, d in zip(barcode_cols, samp_cols):
        m20.pick_up_tip()
        m20.aspirate(1, s)
        m20.dispense(1, d)
        m20.mix(3, 1, d)
        m20.drop_tip()

    temp_mod.set_temperature(72)
    ctx.delay(minutes=10)
    temp_mod.set_temperature(4)

    ctx.comment('\n---------------ADD MIX----------------\n\n')

    for col in samp_cols:
        m20.pick_up_tip()
        m20.aspirate(2, smart_seq_3)
        m20.dispense(2, col)
        m20.mix(3, 3, d)
        m20.drop_tip()

    ctx.pause(""""
                  Run thermocycler profile and place sample plate back
                  on temperature module.
                  """)

    ctx.comment('\n---------------ADD WASH BUFFER----------------\n\n')
    m300.pick_up_tip()
    for col in samp_cols:
        m300.aspirate(60, wash_buff)
        m300.dispense(60, col.top())
    m300.drop_tip()

    ctx.comment('\n---------------ADD SMART SEQ3----------------\n\n')

    for _ in range(3):
        m300.pick_up_tip()
        m300.aspirate(100, smart_seq_3)
        m300.dispense(100, samp_plate.rows()[0][0])
        m300.mix(5, 120, samp_plate.rows()[0][0])
        m300.aspirate(150, samp_plate.rows()[0][0])
        m300.dispense(50, pool_res_well)
        m300.dispense(100, samp_plate.rows()[0][1])
        for col in range(1, 11):
            m300.mix(5, 120, samp_plate.rows()[0][col])
            m300.aspirate(150, samp_plate.rows()[0][col])
            m300.dispense(50, pool_res_well)
            m300.dispense(100, samp_plate.rows()[0][col+1])
        m300.mix(5, 120, samp_plate.rows()[0][-1])
        m300.aspirate(150, samp_plate.rows()[0][-1])  # move entire col 12
        m300.dispense(150, pool_res_well)
        m300.drop_tip()
        ctx.comment('\n')

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
    filename = f"detailed_action_json/053386-pt3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)