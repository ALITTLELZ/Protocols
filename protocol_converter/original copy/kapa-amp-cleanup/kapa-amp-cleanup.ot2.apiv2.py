import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/kapa-amp-cleanup/kapa-amp-cleanup.ot2.apiv2.py"

metadata = {
    'protocolName': 'Kapa Bead Clean Up',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_col, bead_dry_time, m300_mount] = get_values(  # noqa: F821
        "num_col", "bead_dry_time", "m300_mount")

    # num_col = 2
    # bead_dry_time = 3
    # m300_mount = 'left'

    # labware
    # mag_mod = ctx.load_module('magnetic module gen2', 1)
    mag_stand = ctx.load_labware('genericmagnet_96_wellplate_1500ul', 1)
    mag_plate = ctx.load_labware('generic_96_wellplate_1500ul', 4)
    # mag_plate = mag_mod.load_labware('nest_wellplate_100ul_pcr_full_skirt')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 3)
    elute_plate = ctx.load_labware('agilent_96_wellplate_270ul', 2)
    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [7, 8]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    # mapping
    beads = reservoir['A1']
    ethanol = reservoir['A2']
    eb = reservoir['A3']
    trash = reservoir['A12'].top()

    sample_cols = mag_plate.rows()[0][:num_col]
    sample_cols_stand = mag_stand.rows()[0][:num_col]

    def slow_tip_withdrawal(pipette, well_location, to_center=False):
        if pipette.mount == 'right':
            axis = 'A'
        else:
            axis = 'Z'
        ctx.max_speeds[axis] = 10
        if to_center is False:
            pipette.move_to(well_location.top())
        else:
            pipette.move_to(well_location.center())
        ctx.max_speeds[axis] = None

    # protocol
    m300.pick_up_tip()
    m300.mix(20, 200, beads)
    ctx.comment('\n---------------ADDING BEADS TO PLATE----------------\n\n')
    for col in sample_cols:
        if not m300.has_tip:
            m300.pick_up_tip()
        m300.aspirate(90, beads)
        slow_tip_withdrawal(m300, col)
        m300.dispense(90, col)
        m300.mix(10, 110, col)
        m300.drop_tip()

    ctx.delay(minutes=5)

    ctx.pause('Move plate to magnetic stand, then select resume')

    ctx.delay(minutes=3)

    ctx.comment('\n---------------REMOVING SUPER----------------\n\n')
    for col in sample_cols_stand:
        m300.pick_up_tip()
        m300.aspirate(140, col, rate=0.1)
        m300.aspirate(20, col.bottom(z=0.6), rate=0.1)
        m300.dispense(160, trash)
        m300.drop_tip()

    ctx.comment('\n---------------TWO ETHANOL WASHES----------------\n\n')
    for _ in range(2):

        m300.pick_up_tip()
        for col in sample_cols_stand:
            m300.aspirate(200, ethanol)
            slow_tip_withdrawal(m300, ethanol)
            m300.dispense(200, col.top())
            ctx.delay(seconds=2)
            m300.blow_out()

        ctx.delay(seconds=30)

        for col in sample_cols_stand:
            if not m300.has_tip:
                m300.pick_up_tip()
            m300.aspirate(180, col, rate=0.1)
            m300.aspirate(20, col.bottom(z=0.6), rate=0.1)
            m300.dispense(200, trash)
            ctx.delay(seconds=2)
            m300.blow_out()
            m300.drop_tip()

    ctx.delay(minutes=bead_dry_time)

    ctx.pause('Move magplate to slot 4, then select resume')

    ctx.comment('\n---------------Resuspend----------------\n\n')
    for col in sample_cols:
        m300.pick_up_tip()
        m300.aspirate(23, eb)
        m300.dispense(23, col)
        m300.mix(15, 19, col.bottom(z=0.7))
        m300.drop_tip()

    ctx.pause('Move plate to magnetic stand, then select resume')
    ctx.delay(minutes=3)

    ctx.comment('\n---------------Transfer Elute----------------\n\n')
    for s, d in zip(sample_cols, elute_plate.rows()[0]):
        m300.pick_up_tip()
        m300.aspirate(20, s.bottom(z=0.7), rate=0.1)
        m300.dispense(20, d)
        m300.blow_out(d.top())
        m300.touch_tip()
        m300.drop_tip()

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
    filename = f"detailed_action_json/kapa-amp-cleanup.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)