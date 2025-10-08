import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0d868e-part2/0d868e-part2.ot2.apiv2.py"

from opentrons import types
from opentrons import protocol_api
metadata = {
    'protocolName': 'Ilumina TruSeq Stranded mRNA - Part 2',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samp, p300_mount, p20_mount] = get_values(  # noqa: F821
        "num_samp", "p300_mount", "p20_mount")

    # module
    temp_mod = ctx.load_module('temperature module gen2', 3)
    reag_rack = temp_mod.load_labware('opentrons_24_aluminumblock_nest_2ml_snapcap')  # noqa: E501

    mag_mod = ctx.load_module('magnetic module gen2', 10)
    mag_plate = mag_mod.load_labware('froggabio_96_wellplate_300ul')

    # labware
    reag_plate = ctx.load_labware('froggabio_96_wellplate_300ul', 1)
    final_plate = ctx.load_labware('froggabio_96_wellplate_300ul', 4)
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 2)
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
               for slot in [7, 8, 9]]
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
              for slot in [5]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', p300_mount,
                               tip_racks=tips300)
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=tips20)

    ctx.max_speeds['Z'] = 125
    ctx.max_speeds['A'] = 125
    supernatant_headspeed_modulator = 10
    mag_height = 2

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            ctx.pause("Replace only completely empty tip racks.")
            pip.reset_tipracks()
            pick_up(pip)

    def remove_super(vol):
        ctx.comment('\n-------------REMOVING SUPERNATANT--------------\n\n')
        for i, dest in enumerate(samples):
            side = -1 if i % 2 == 0 else 1
            pick_up(m300)
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
    samples = mag_plate.rows()[0][:num_col]

    # reagents
    superscriptII = reag_rack.wells()[0]
    rsb = reag_rack.wells()[1]
    smm = reag_rack.wells()[2]
    atl = reag_rack.wells()[3]
    stl = reag_rack.wells()[4]

    beads = reag_plate.rows()[0][:num_col]
    ampur_beads = reag_plate.rows()[0][-1]
    rsb_plate = reag_plate.rows()[0][-2]
    eth = reservoir.wells()[0]
    waste = reservoir.wells()[-1]

    # protocol
    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    old_samples = samples
    samples = mag_plate.rows()[0][num_col:num_col+num_col]
    samples_single = [well for col in mag_plate.columns()[num_col:num_col+num_col] for well in col]  # noqa: E501

    ctx.comment('\n---------------MOVING SAMPLES----------------\n\n')
    for i, (s_col, d_col) in enumerate(zip(old_samples, samples)):
        side = -1 if i % 2 == 0 else 1
        pick_up(m300)
        m300.move_to(s_col.top())
        ctx.max_speeds['Z'] /= supernatant_headspeed_modulator
        ctx.max_speeds['A'] /= supernatant_headspeed_modulator
        m300.aspirate(20, s_col.bottom().move(types.Point(x=side,
                      y=0, z=1)),
                      rate=0.1)
        ctx.delay(seconds=1)
        m300.move_to(d_col.top())
        ctx.max_speeds['Z'] *= supernatant_headspeed_modulator
        ctx.max_speeds['A'] *= supernatant_headspeed_modulator
        m300.dispense(m300.current_volume, d_col)
        m300.drop_tip()

    mag_mod.disengage()

    ctx.pause('''Centrifuge FSA at 600 × g for 5 seconds.
    Add 50 μl SuperScript II to one tube of FSA. Pipette to mix,
    and then centrifuge briefly.
    Label the FSA tube to indicate that SuperScript II has been added.
    ''')

    ctx.comment('\n---------------ADDING SUPERSCRIPT----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(8, superscriptII)
        p20.dispense(8, well)
        p20.mix(6, 20, well)
        p20.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    Centrifuge at 280 × g for 1 minute.
    Place on the preprogrammed thermal cycler and run the Synthesize 1st Strand
    program. Each well contains 25 μl.
    Ensure SMM is centrifuged at 600 x g for 5 seconds before next section.
    Remove adhesive seal and place back on the magnetic module.
    ''')

    ctx.comment('\n---------------ADDING RSB----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(5, rsb)
        p20.dispense(5, well)
        p20.blow_out()
        p20.drop_tip()

    ctx.comment('\n---------------ADDING SMM----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(5, smm)
        p20.dispense(5, well)
        p20.mix(6, 20, well)
        p20.blow_out()
        p20.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    Centrifuge at 280 × g for 1 minute.
    Place on the preprogrammed thermal cycler and incubate at 16°C for 1 hour.
    Each well contains 50 μl.
    Let plate reach room temperature.
    Remove adhesive seal and place back on the magnetic module.
    ''')

    ctx.comment('\n---------------ADDING BEADS----------------\n\n')
    for s_col, d_col in zip(beads, samples):
        pick_up(m300)
        m300.mix(5, 90, s_col)
        m300.aspirate(90, s_col)
        m300.dispense(90, d_col)
        m300.mix(10, 75, d_col)
        m300.drop_tip()

    ctx.delay(minutes=5)
    mag_mod.engage(height_from_base=mag_height)
    ctx.delay(minutes=5)

    remove_super(135)

    ctx.comment('\n---------------TWO WASHES----------------\n\n')
    for _ in range(2):
        pick_up(m300)
        for col in samples:
            m300.aspirate(200, eth)
            m300.dispense(200, col.top(), rate=0.5)
            m300.blow_out(col.top())
        m300.drop_tip()

        mag_mod.engage(height_from_base=mag_height)
        ctx.delay(seconds=30)
        remove_super(200)

    ctx.pause(''''
    Manual intervention for remainder of protocol.
    Use a 20 μl pipette to remove residual EtOH from each well.
    Air-dry on the magnetic stand for 15 minutes. Do not over dry beads.
    Remove from the magnetic stand.
    Add 17.5 μl RSB to each well, and then mix thoroughly as follows.
    [LS] Pipette up and down 10 times.
    Incubate at room temperature for 2 minutes.
    Place on a magnetic stand and wait until the liquid is clear (~5 minutes).
    Transfer 15 μl supernatant to the corresponding well of the ALP plate.
    Save the following ATAIL70 program on the thermal cycler:
    Choose the preheat lid option and set to 100°C
    37°C for 30 minutes
    70°C for 5 minutes
    Hold at 4°C
    Ensure ATL is centrifuged at 600 x g for 5 seconds before next section.
    Place plate back on magnetic module.
    ''')

    samples = mag_plate.rows()[0][num_col*2:num_col*3]
    samples_single = [well for col in mag_plate.columns()[num_col*2:num_col*3] for well in col]  # noqa: E501

    ctx.comment('\n---------------ADDING RSB----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(5, rsb)
        p20.dispense(5, well)
        p20.blow_out()
        p20.drop_tip()

    ctx.comment('\n---------------ADDING ATL----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(12.5, atl)
        p20.dispense(12.5, well)
        p20.blow_out()
        p20.drop_tip()

    ctx.comment('\n---------------MIXING SAMPLES----------------\n\n')
    for col in samples:
        pick_up(m300)
        m300.mix(10, 22, col)
        m300.drop_tip()

    ctx.pause('''
    Seal plate with Microseal 'B' adhesive seal.
    Centrifuge at 280 × g for 1 minute.
    Incubate as follows.
    Place on the thermal cycler and run the ATAIL70 program.
    Each well contains 30 μl.
    Proceed in the protocol until step 12 of "Add Index Adapters" section.
    Remove adhesive seal and place back on the magnetic module.
    The next step will be STL addition (5ul).
    ''')

    ctx.comment('\n---------------ADDING STL----------------\n\n')
    for well in samples_single:
        pick_up(p20)
        p20.aspirate(5, stl)
        p20.dispense(5, well)
        p20.mix(5, 20, well)
        p20.blow_out()
        p20.drop_tip()

    ctx.pause('''
    Centrifuge at 280 × g for 1 minute.
    ''')

    bead_vols = [42, 50]
    rsb_vols = [52.5, 22.5]

    ctx.comment('\n---------------TWO ROUNDS----------------\n\n')
    for i, (bead_vol, rsb_vol) in enumerate(zip(bead_vols, rsb_vols)):
        for col in samples:
            pick_up(m300)
            m300.mix(7, 200, ampur_beads)
            m300.aspirate(bead_vol, ampur_beads)
            m300.dispense(bead_vol, col)
            m300.mix(6, 70, col)
            m300.blow_out()
            m300.drop_tip()
        ctx.delay(minutes=15)
        mag_mod.engage(height_from_base=mag_height)
        ctx.delay(minutes=5)
        remove_super(92)
        ctx.comment('\n---------------TWO WASHES----------------\n\n')
        for _ in range(2):
            pick_up(m300)
            for col in samples:
                m300.aspirate(200, eth)
                m300.dispense(200, col.top(), rate=0.5)
                m300.blow_out(col.top())
            m300.drop_tip()

            mag_mod.engage(height_from_base=mag_height)
            ctx.delay(seconds=30)
            remove_super(200)

        ctx.pause('''
        Place plate on magnetic stand.
        Use a 20 μl pipette to remove residual EtOH from each well.
        Air-dry on the magnetic stand for 15 minutes.
        Remove from the magnetic stand.
        ''')

        mag_mod.disengage()

        for col in samples:
            pick_up(m300)
            m300.aspirate(rsb_vol, rsb_plate)
            m300.dispense(rsb_vol, col)
            m300.mix(5, 40, col)
            m300.drop_tip()

        ctx.delay(minutes=2)

        mag_mod.engage(height_from_base=mag_height)
        ctx.delay(minutes=5)

        if i == 0:
            old_samples = samples
            samples = mag_plate.rows()[0][num_col*3:num_col*4]
            samples_single = [well for col in mag_plate.columns()[num_col*3:num_col*4] for well in col]  # noqa: E501

            ctx.comment('\n---------------MOVING SAMPLES----------------\n\n')
            for i, (s_col, d_col) in enumerate(zip(old_samples, samples)):
                side = -1 if (i+num_col*2) % 2 == 0 else 1
                pick_up(m300)
                m300.move_to(s_col.top())
                ctx.max_speeds['Z'] /= supernatant_headspeed_modulator
                ctx.max_speeds['A'] /= supernatant_headspeed_modulator
                m300.aspirate(50, s_col.bottom().move(types.Point(x=side,
                              y=0, z=1)),
                              rate=0.1)
                ctx.delay(seconds=1)
                m300.move_to(d_col.top())
                ctx.max_speeds['Z'] *= supernatant_headspeed_modulator
                ctx.max_speeds['A'] *= supernatant_headspeed_modulator
                m300.dispense(m300.current_volume, d_col)
                m300.drop_tip()

        if i == 1:
            old_samples = samples
            samples = final_plate.rows()[0][:num_col]
            samples_single = [well for col in final_plate.columns()[:num_col] for well in col]  # noqa: E501

            ctx.comment('\n---------------MOVING SAMPLES----------------\n\n')

            for i, (s_col, d_col) in enumerate(zip(old_samples, samples)):

                side = -1 if (i+num_col*3) % 2 == 0 else 1
                pick_up(m300)
                m300.move_to(s_col.top())
                ctx.max_speeds['Z'] /= supernatant_headspeed_modulator
                ctx.max_speeds['A'] /= supernatant_headspeed_modulator
                m300.aspirate(20, s_col.bottom().move(types.Point(x=side,
                              y=0, z=1)),
                              rate=0.1)
                ctx.delay(seconds=1)
                m300.move_to(d_col.top())
                ctx.max_speeds['Z'] *= supernatant_headspeed_modulator
                ctx.max_speeds['A'] *= supernatant_headspeed_modulator
                m300.dispense(m300.current_volume, d_col)
                m300.drop_tip()

        ctx.comment('\n\n\n\n\n\n\n\n\n')

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
    filename = f"detailed_action_json/0d868e-part2.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)