import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/019968/019968.ot2.apiv2.py"

# flake8: noqa

import math

metadata = {
    'protocolName': 'Methanol Dilution for LCMS Analysis',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [num_samp, include_pause, single_dilution,
     init_vol_meth, init_vol_standard,
      p300_mount, p1000_mount] = get_values(  # noqa: F821
      "num_samp", "include_pause", "single_dilution",
      "init_vol_meth", "init_vol_standard", "p300_mount", "p1000_mount")

    # num_samp = 30
    # p300_mount = 'left'
    # p1000_mount = 'right'
    # init_vol_standard = 13
    # init_vol_meth = 45
    # include_pause = True
    # single_dilution = False

    # labware
    if single_dilution:
        waters_racks = [
                       ctx.load_labware('waters_48_tuberack_300ul',  # change this
                                        slot) for slot in [1, 2]]

        aluminum_racks = [
                       ctx.load_labware('opentrons_24_aluminumblock_generic_2ml_screwcap',
                                        slot) for slot in [4, 5, 7, 8]]

        tuberack = ctx.load_labware('opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', 11)

        tip300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                  for slot in [3, 6]]
        tip1000 = [ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
                   for slot in [9]]

    else:
        waters_racks = [
                       ctx.load_labware('opentrons_24_aluminumblock_generic_2ml_screwcap',
                                        slot) for slot in [1, 2]]

        aluminum_racks = [
                       ctx.load_labware('opentrons_24_aluminumblock_generic_2ml_screwcap',
                                        slot) for slot in [4, 5, 7, 8]]

        tuberack = ctx.load_labware('opentrons_10_tuberack_falcon_4x50ml_6x15ml_conical', 11)

        tip300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                  for slot in [3, 6]]
        tip1000 = [ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
                   for slot in [9]]

    # pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=tip300)
    p1000 = ctx.load_instrument('p1000_single_gen2', p1000_mount,
                                tip_racks=tip1000)

    # liquid height tracking
    v_naught_standard = init_vol_standard*1000
    v_naught_meth = init_vol_meth*1000

    radius_standard = tuberack.rows()[0][0].diameter/2
    radius_meth = tuberack.rows()[0][2].diameter/2

    h_naught_standard = 0.85*v_naught_standard/(math.pi*radius_standard**2)
    h_naught_meth = 0.85*v_naught_meth/(math.pi*radius_meth**2)

    h_standard = h_naught_standard
    h_meth = h_naught_meth

    def adjust_height(vol, standard_or_meth):
        nonlocal h_standard
        nonlocal h_meth

        if standard_or_meth == 'standard':
            radius = radius_standard
        elif standard_or_meth == 'meth':
            radius = radius_meth

        dh = (vol/(math.pi*radius**2))*1.33
        if standard_or_meth == 'standard':
            h_standard -= dh
        elif standard_or_meth == 'meth':
            h_meth -= dh

        if h_standard < 12:
            h_standard = 1
        if h_meth < 12:
            h_meth = 1

    # mapping
    methanol = tuberack['A3']
    standard = tuberack['A1']
    empty_sample_tubes = [tube
                          for rack in aluminum_racks[:2]
                          for row in rack.rows() for tube in row][:num_samp]
    sample_tubes = [tube
                    for rack in aluminum_racks[2:]
                    for row in rack.rows() for tube in row][:num_samp]

    final_tubes = [tube
                   for rack in waters_racks
                   for row in rack.rows() for tube in row][:num_samp]

    # protocol
    if single_dilution:
        ctx.comment('\n---------------ADDING METHANOL----------------\n\n')
        p1000.pick_up_tip()
        p1000.mix(1, 900, methanol.bottom(z=h_meth-5))
        for tube in empty_sample_tubes:
            p1000.aspirate(750, methanol.bottom(z=h_meth))
            p1000.dispense(750, tube.bottom(z=10))
            p1000.move_to(tube.top(z=-3))
            ctx.delay(seconds=2.5)
            p1000.blow_out()
            adjust_height(750, 'meth')
        p1000.drop_tip()
        ctx.comment('\n\n')

        ctx.comment('\n---------------ADDING STANDARD----------------\n\n')
        p300.pick_up_tip()
        p300.mix(1, 250, standard.bottom(z=h_standard-5))
        for tube in empty_sample_tubes:
            p300.aspirate(150, standard.bottom(z=h_standard))
            p300.dispense(150, tube.top())
            ctx.delay(seconds=2.5)
            p300.blow_out()
            adjust_height(150, 'standard')
        p300.drop_tip()
        ctx.comment('\n\n')

        ctx.comment('\n---------------ADDING SAMPLE----------------\n\n')
        for s, d in zip(sample_tubes, empty_sample_tubes):
            p300.pick_up_tip()
            p300.aspirate(100, s)
            p300.dispense(100, d)
            p300.drop_tip()

        if include_pause:
            ctx.pause("Please cap tubes, then select Resume in the app.")

        ctx.comment('\n---------------ADDING SAMPLE----------------\n\n')
        for s, d in zip(empty_sample_tubes, final_tubes):
            p300.pick_up_tip()
            p300.mix(2, 250, s)
            p300.aspirate(200, s)
            p300.dispense(200, d)
            p300.drop_tip()

    else:
        ctx.comment('\n---------------ADDING METHANOL----------------\n\n')
        p1000.pick_up_tip()
        p1000.mix(1, 900, methanol.bottom(z=h_meth-5))
        for tube in empty_sample_tubes:
            p1000.aspirate(900, methanol.bottom(z=h_meth))
            p1000.dispense(900, tube.bottom(z=10))
            p1000.move_to(tube.top(z=-3))
            ctx.delay(seconds=2.5)
            p1000.blow_out()
            adjust_height(900, 'meth')
        p1000.drop_tip()
        ctx.comment('\n\n')

        ctx.comment('\n---------------ADDING SAMPLE----------------\n\n')
        for s, d in zip(sample_tubes, empty_sample_tubes):
            p300.pick_up_tip()
            p300.aspirate(100, s)
            p300.dispense(100, d)
            p300.mix(3, 200, d)
            p300.drop_tip()

        if include_pause:
            ctx.pause("Please cap tubes, then select Resume in the app.")

        ctx.comment('\n---------------ADDING METHANOL----------------\n\n')
        p1000.pick_up_tip()
        p1000.mix(1, 900, methanol.bottom(z=h_meth-5))
        for tube in final_tubes:
            p1000.aspirate(750, methanol.bottom(z=h_meth))
            p1000.dispense(750, tube.bottom(z=10))
            p1000.move_to(tube.top(z=-3))
            ctx.delay(seconds=2.5)
            p1000.blow_out()
            adjust_height(750, 'meth')
        p1000.drop_tip()
        ctx.comment('\n\n')

        ctx.comment('\n---------------ADDING STANDARD----------------\n\n')
        p300.pick_up_tip()
        p300.mix(1, 250, standard.bottom(z=h_standard-5))
        for tube in final_tubes:
            p300.aspirate(150, standard.bottom(z=h_standard))
            p300.dispense(150, tube.top())
            ctx.delay(seconds=2.5)
            p300.blow_out()
            adjust_height(150, 'standard')
        p300.drop_tip()
        ctx.comment('\n\n')

        ctx.comment('\n---------------ADDING SAMPLE----------------\n\n')
        for s, d in zip(empty_sample_tubes, final_tubes):
            p300.pick_up_tip()
            p300.mix(2, 250, s)
            p300.aspirate(100, s)
            p300.dispense(100, d)
            p300.drop_tip()

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
    filename = f"detailed_action_json/019968.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)