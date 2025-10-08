import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0d868e/0d868e.ot2.apiv2.py"

from opentrons import types
metadata = {
    'protocolName': 'Ilumina TruSeq Stranded mRNA - Part 1',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samp, p300_mount] = get_values(  # noqa: F821
        "num_samp", "p300_mount")

    # module
    temp_mod = ctx.load_module('temperature module gen2', 3)
    sample_plate = temp_mod.load_labware('froggabio_96_wellplate_300ul')
    temp_mod.set_temperature(4)
    mag_mod = ctx.load_module('magnetic module gen2', 10)
    mag_plate = mag_mod.load_labware('froggabio_96_wellplate_300ul')

    # labware
    reag_plate = ctx.load_labware('froggabio_96_wellplate_300ul', 1)
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 2)
    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [7, 8, 9]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', p300_mount, tip_racks=tips)

    ctx.max_speeds['Z'] = 125
    ctx.max_speeds['A'] = 125
    supernatant_headspeed_modulator = 10
    mag_height = 2

    def remove_super(vol):
        ctx.comment('\n-------------REMOVING SUPERNATANT--------------\n\n')
        for i, dest in enumerate(samples):
            side = -1 if i % 2 == 0 else 1
            m300.pick_up_tip()
            m300.move_to(dest.top())
            ctx.max_speeds['Z'] /= supernatant_headspeed_modulator
            ctx.max_speeds['A'] /= supernatant_headspeed_modulator
            m300.aspirate(vol, dest.bottom().move(types.Point(x=side,
                          y=0, z=1)),
                          rate=0.1)
            ctx.delay(seconds=1)
            m300.move_to(dest.top())
            ctx.max_speeds['Z'] *= supernatant_headspeed_modulator
            ctx.max_speeds['A'] *= supernatant_headspeed_modulator
            m300.dispense(m300.current_volume, waste)
            m300.blow_out()
            m300.air_gap(50)
            m300.drop_tip()

    # mapping
    num_col = int(num_samp/8)
    samples = sample_plate.rows()[0][:num_col]
    rpb = reag_plate.rows()[0][0]
    bwb = reag_plate.rows()[0][1:7][:num_col*2]
    elb = reag_plate.rows()[0][7]
    bbb = reag_plate.rows()[0][8]
    fpf = reag_plate.rows()[0][9]
    waste = reservoir.wells()[-1]

    # protocol
    ctx.comment('\n---------------ADDING RPB----------------\n\n')
    for col in samples:
        m300.pick_up_tip()
        m300.aspirate(50, rpb)
        m300.dispense(50, col)
        m300.mix(6, 75, col)
        m300.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    Incubate as follows.
    [LS] Place on the thermal cycler and run the mRNA Denaturation program.
    Each well contains 100 μl.
    Incubate for 5 minutes on bench.
    [LS] Centrifuge at 280 × g for 1 minute. Remove adhesive seal.
    Place plate back on magnetic module on OT-2.
    and select "Resume" on the Opentrons app.
    The protocol will incubate for 5 minutes then proceed in the protocol
    to engage magnet. Plate should NOT be on the temperature module any longer.
    ''')
    temp_mod.set_temperature(25)
    samples = mag_plate.rows()[0][:num_col]

    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    remove_super(100)

    mag_mod.disengage()

    ctx.comment('\n---------------ADDING BWB----------------\n\n')
    for s_col, d_col in zip(bwb[:num_col], samples):
        m300.pick_up_tip()
        m300.aspirate(200, s_col)
        m300.dispense(200, d_col)
        m300.mix(6, 75, d_col)
        m300.drop_tip()

    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    remove_super(200)

    mag_mod.disengage()

    ctx.comment('\n---------------ADDING ELB----------------\n\n')
    for col in samples:
        m300.pick_up_tip()
        m300.aspirate(50, elb)
        m300.dispense(50, col)
        m300.mix(6, 75, col)
        m300.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    [LS] Centrifuge at 280 × g for 1 minute.
    Incubate as follows.
    [LS] Place on the thermal cycler and run the mRNA Elution 1 program.
    Each well contains 50 μl.
    Remove adhesive seal.
    Place plate back on magnetic module for BBB addition.
    ''')

    ctx.comment('\n---------------ADDING BBB----------------\n\n')
    for col in samples:
        m300.pick_up_tip()
        m300.aspirate(50, bbb)
        m300.dispense(50, col)
        m300.mix(6, 75, col)
        m300.drop_tip()

    ctx.pause('''
    Seal the RBP plate with a Microseal 'B' adhesive seal before running
    the mRNA denaturation program.
    Centrifuge briefly then remove the adhesive seal.
    Place plate back on magnetic module.
    Protocol will incubate for 5 minutes then engage''')

    samples = mag_plate.rows()[0][:num_col]

    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    remove_super(100)

    mag_mod.disengage()

    ctx.comment('\n---------------ADDING BWB----------------\n\n')
    for s_col, d_col in zip(bwb[num_col:], samples):
        m300.pick_up_tip()
        m300.aspirate(200, s_col)
        m300.dispense(200, d_col)
        m300.mix(6, 75, d_col)
        m300.drop_tip()

    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    remove_super(200)

    mag_mod.disengage()

    ctx.comment('\n---------------ADDING FPF----------------\n\n')
    for col in samples:
        m300.pick_up_tip()
        m300.aspirate(20, fpf)
        m300.dispense(20, col)
        m300.mix(3, 20, col)
        m300.blow_out(col.top(z=-3))
        m300.touch_tip()
        m300.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    [LS] Centrifuge at 280 × g for 1 minute.
    Place on the thermal cycler and run the Elution 2 - Frag - Prime program.
    Each well contains 19.5 μl.
    Remove adhesive seal.
    ''')

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
    filename = f"detailed_action_json/0d868e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)