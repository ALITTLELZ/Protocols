import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/29f643/29f643.ot2.apiv2.py"

from opentrons import protocol_api
import math
import string

metadata = {
    'protocolName': 'Alpco Human Insulin ELISA',
    'author': 'Chaz Childers <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx: protocol_api.ProtocolContext):
    [
     _num_samps,
     _multi_mnt
    ] = get_values(  # noqa: F821 (<--- DO NOT REMOVE!)
        "_num_samps",
        "_multi_mnt")

    # VARIABLES
    num_samps = _num_samps
    multi_mnt = _multi_mnt

    # load labware
    dest_plate = ctx.load_labware(
        'nunc_maxisorp_96_wellplate_250ul', '1')
    if num_samps > 40:
        dest_plate2 = ctx.load_labware(
            'nunc_maxisorp_96_wellplate_250ul', '4')
    res12 = ctx.load_labware('nest_12_reservoir_15ml', '7')
    tips = [
        ctx.load_labware(
            'opentrons_96_tiprack_300ul', s) for s in [10, 11]
            ]

    num_racks = math.ceil((num_samps+8)/24)
    samp_racks = [
        ctx.load_labware(
            'opentrons_24_aluminumblock_nest_1.5ml_snapcap',
            s) for s in [2, 3, 5, 6][:num_racks]
            ]

    # load pipette
    m300 = ctx.load_instrument('p300_multi_gen2', multi_mnt, tip_racks=tips)
    s_mnt = 'left' if multi_mnt == 'right' else 'right'
    p300 = ctx.load_instrument('p300_single_gen2', s_mnt, tip_racks=tips)

    # reagent locations
    antibody = res12.wells()[:2]
    tmb = res12.wells()[3:5]
    stop_sol = res12.wells()[6:8]

    # Transfer 25ul of standards, controls, samples
    # standards/controls
    ctx.comment('Adding 25ul of standards and controls')
    for src, dest in zip(samp_racks[0].wells()[:8], string.ascii_uppercase):
        p300.pick_up_tip()
        p300.mix(3, 50, src)
        p300.aspirate(60, src)
        p300.dispense(25, dest_plate[dest+'1'])
        p300.dispense(25, dest_plate[dest+'2'])
        p300.dispense(10, src)
        if num_samps > 40:
            p300.mix(3, 50, src)
            p300.aspirate(60, src)
            p300.dispense(25, dest_plate2[dest+'1'])
            p300.dispense(25, dest_plate2[dest+'2'])
            p300.dispense(10, src)
        p300.drop_tip()

    ctx.comment('Adding 25ul of sample in duplicate')
    samp_tubes = [
        well for rack in samp_racks for well in rack.wells()][8:num_samps+8]
    samp_dests = []
    for lc, rc in zip(dest_plate.columns()[2::2], dest_plate.columns()[3::2]):
        for lwell, rwell in zip(lc, rc):
            samp_dests.append([lwell, rwell])
    if num_samps > 40:
        for lc, rc in zip(
                dest_plate2.columns()[2::2], dest_plate2.columns()[3::2]):
            for lwell, rwell in zip(lc, rc):
                samp_dests.append([lwell, rwell])

    for src, dests in zip(samp_tubes, samp_dests):
        p300.pick_up_tip()
        p300.mix(3, 50, src)
        p300.aspirate(60, src)
        p300.dispense(25, dests[0])
        p300.dispense(25, dests[1])
        p300.dispense(10, src)
        p300.drop_tip()

    # Add 100ul detection antibody
    ctx.comment(
        '\nAdding 100uL Dettection Antibody from A1 of 12-Well Reservoir')
    num_cols = math.ceil((8+num_samps)/8) * 2
    if num_samps > 40:
        total_cols = dest_plate.rows()[0] + dest_plate2.rows()[0]
        all_cols = total_cols[:num_cols]
    else:
        all_cols = dest_plate.rows()[0][:num_cols]

    m300.pick_up_tip()
    for idx, col in enumerate(all_cols):
        src = antibody[0] if idx < 12 else antibody[1]
        if m300.current_volume == 0:
            m300.aspirate(200, src)
        m300.dispense(100, col.top(-1))
        if m300.current_volume == 0:
            m300.touch_tip(col)
            m300.blow_out(col.top(-1))
    if m300.current_volume > 0:
        m300.dispense(m300.current_volume, src)
    m300.drop_tip()

    ctx.pause(
        '\nAddition of Detection Antibody complete. Please cover plate  and place on shaker for 1 hour at room temperature. When ready \
        for next steps, replace plate and click RESUME.')

    # Add 100uL of TMB Sustrate
    ctx.comment('\nAdding 100uL of TMB Substrate')
    m300.pick_up_tip()
    for idx, col in enumerate(all_cols):
        src = tmb[0] if idx < 12 else tmb[1]
        if m300.current_volume == 0:
            m300.aspirate(200, src)
        m300.dispense(100, col.top(-1))
        if m300.current_volume == 0:
            m300.touch_tip(col)
            m300.blow_out(col.top(-1))
    if m300.current_volume > 0:
        m300.dispense(m300.current_volume, src)
    m300.drop_tip()

    ctx.pause('\nPlease place plate on shaker for 15 minutes.  When ready, replace plate and click RESUME')

    # Add 100uL of Stop Solution
    ctx.comment('\nAdding 100uL of Stop Solution')

    m300.pick_up_tip()
    for idx, col in enumerate(all_cols):
        src = stop_sol[0] if idx < 12 else stop_sol[1]
        if m300.current_volume == 0:
            m300.aspirate(200, src)
        m300.dispense(100, col.top(-1))
        if m300.current_volume == 0:
            m300.touch_tip(col)
            m300.blow_out(col.top(-1))
    if m300.current_volume > 0:
        m300.dispense(m300.current_volume, src)
    m300.drop_tip()

    ctx.comment('Protocol complete!')

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
    filename = f"detailed_action_json/29f643.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)