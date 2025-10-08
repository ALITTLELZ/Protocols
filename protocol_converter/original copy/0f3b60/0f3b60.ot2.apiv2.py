import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0f3b60/0f3b60.ot2.apiv2.py"

metadata = {
    'protocolName': 'NEBNext® ARTIC SARS-CoV-2 Library Prep - Bead Cleanup',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [m20_mount, m300_mount] = get_values(  # noqa: F821
        "m20_mount", "m300_mount")

    m300_mount = "left"
    m20_mount = "right"

    # load labware
    mag_mod = ctx.load_module('magnetic module gen2', 3)
    mag_mod.disengage()
    mag_plate = mag_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    pcr_plate = ctx.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 2)
    reag_plate = ctx.load_labware('nest_96_wellplate_2ml_deep', 1)

    tipracks200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
                   for slot in [7, 8, 9, 10, 11]]

    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
                  for slot in [4, 5, 6]]

    # load pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tipracks20)
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tipracks200)

    # mapping
    beads = reag_plate.rows()[0][0]
    ethanol_wash1 = reag_plate.rows()[0][1]
    ethanol_wash2 = reag_plate.rows()[0][2]
    elute = reag_plate.rows()[0][3]
    trash = reag_plate.rows()[0][-1]
    sample_cols = mag_plate.rows()[0]

    # transfer sample
    ctx.comment('\n\n------------Transferring Sample-------------\n')

    for s, d in zip(pcr_plate.rows()[0], mag_plate.rows()[0]):
        m20.pick_up_tip()
        m20.aspirate(12.5, s)
        m20.dispense(12.5, d)
        m20.blow_out()
        m20.drop_tip()

    ctx.pause("Mix plate on magnetic module. Put back on magnetic module")

    ctx.comment('\n\n------------Transferring Beads-------------\n')
    # premix beads
    m300.pick_up_tip()
    m300.mix(3, 200, beads)
    m300.drop_tip()

    # transfer beads
    for col in sample_cols:
        m20.pick_up_tip()
        m20.aspirate(20, beads, rate=0.75)
        m20.dispense(20, col)
        m20.blow_out()
        m20.drop_tip()

    ctx.pause("Mix, incubate 5 minutes off deck. Place back on mag deck.")

    ctx.comment('\n\n------------Engage Magnet, Remove Super-------------\n')
    mag_mod.engage()
    ctx.delay(minutes=5)

    # remove super
    for col in sample_cols:
        m300.pick_up_tip()
        m300.aspirate(50, col, rate=0.2)
        m300.aspirate(10, col.bottom(z=0.5), rate=0.2)
        m300.aspirate(5, col.bottom(z=0.2), rate=0.2)
        m300.dispense(m300.current_volume, trash, rate=0.2)
        m300.drop_tip()

    trash = reag_plate.rows()[0][-2]

    ctx.comment('\n\n------------Two Washes-------------\n')
    for wash in [ethanol_wash1, ethanol_wash2]:
        m300.pick_up_tip()
        for col in sample_cols:
            m300.aspirate(100, wash)
            m300.dispense(100, col.top())
            m300.blow_out()
        ctx.comment('\n')

        m300.aspirate(100, sample_cols[0], rate=0.2)
        m300.aspirate(10, sample_cols[0].bottom(z=0.5), rate=0.2)
        m300.aspirate(5, sample_cols[0].bottom(z=0.2), rate=0.2)
        m300.dispense(m300.current_volume, trash)
        m300.drop_tip()

        for col in sample_cols[1:]:
            m300.pick_up_tip()
            m300.aspirate(100, col, rate=0.2)
            m300.aspirate(10, col.bottom(z=0.5), rate=0.2)
            m300.aspirate(5, col.bottom(z=0.2), rate=0.2)
            m300.dispense(m300.current_volume, trash)
            m300.drop_tip()

        trash = reag_plate.rows()[0][-3]
        ctx.comment('\n\n\n')

    ctx.delay(minutes=5)
    mag_mod.disengage()

    ctx.comment('\n\n------------Adding Elute-------------\n')
    m300.pick_up_tip()
    m300.distribute(27,
                    elute,
                    [col.top() for col in sample_cols],
                    new_tip='never')
    m300.drop_tip()

    ctx.pause("""Mix samples. Put empty NEST 100ul pcr plate on slot 2.
                 Incubate 2 minutes off deck.""")

    mag_mod.engage()
    ctx.delay(minutes=5)

    # transfer sample
    ctx.comment('\n\n------------Transferring Sample-------------\n')

    for s, d in zip(mag_plate.rows()[0], pcr_plate.rows()[0]):
        m300.pick_up_tip()
        m300.aspirate(25, s, rate=0.2)
        m300.dispense(25, d)
        m300.blow_out()
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
    filename = f"detailed_action_json/0f3b60.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)