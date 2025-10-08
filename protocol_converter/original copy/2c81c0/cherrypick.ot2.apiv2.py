import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2c81c0/cherrypick.ot2.apiv2.py"

import math

# metadata
metadata = {
    'protocolName': 'Cherrypicking from .csv',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}


def run(ctx):

    csv_input, p10_mount, p300_mount, change_tips = get_values(  # noqa: F821
        'csv_input', 'p10_mount', 'p300_mount', 'change_tips')

    # labware
    tiprack10 = [ctx.load_labware('biotix_96_filtertiprack_10ul', slot)
                 for slot in ['4', '9']]
    tiprack300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
                  for slot in ['7', '8']]

    # pipette
    p10 = ctx.load_instrument(
        'p10_single', p10_mount, tip_racks=tiprack10)
    p300 = ctx.load_instrument(
        'p300_single', p300_mount, tip_racks=tiprack300)
    p10.flow_rate.aspirate = 3.5
    p10.flow_rate.dispense = 7
    p10.flow_rate.blow_out = 500
    p300.flow_rate.aspirate = 105
    p300.flow_rate.dispense = 210
    p300.flow_rate.blow_out = 500

    # parse
    data = [
        [val.strip().upper() for val in line.split(',')]
        for line in csv_input.splitlines()
        if line and line.split(',')[0].strip()][1:]

    # loop and perform transfers
    labware_load_dict = {
        'plate': 'biorad_96_wellplate_200ul_pcr',
        'tuberack': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        'deepplate': 'nest_96_wellplate_2ml_deep'
    }
    for d in data:
        [s_lw, s_slot, s_well, vol, d_lw, d_slot, d_well, h_offset_src,
         h_offset_dest, vol_mix] = d
        vol, h_offset_src, h_offset_dest, vol_mix = [
            float(vol), float(h_offset_src), float(h_offset_dest),
            float(vol_mix)]
        s_lw, d_lw = s_lw.lower().strip(), d_lw.lower().strip()
        if int(s_slot) not in ctx.loaded_labwares:
            ctx.load_labware(
                labware_load_dict[s_lw], s_slot, 'source plate ' + s_slot)
        if int(d_slot) not in ctx.loaded_labwares:
            ctx.load_labware(
                labware_load_dict[d_lw], d_slot, 'destination plate ' + d_slot)
        source = ctx.loaded_labwares[int(s_slot)].wells_by_name()[s_well]
        dest = ctx.loaded_labwares[int(d_slot)].wells_by_name()[d_well]
        if h_offset_src > source.geometry._depth:
            ctx.pause('Warning: Specified source height may result in  crashing. Press resume to ignore.')
        if h_offset_dest > dest.geometry._depth:
            ctx.pause('Warning: Specified destination height may result in  crashing. Press resume to ignore.')

        pip = p300 if vol > 30 else p10
        num_trans = math.ceil(vol/pip.max_volume)
        vol_per_trans = vol/num_trans
        if change_tips == 'once per well':
            pip.pick_up_tip()
        for _ in range(num_trans):
            if change_tips == 'always':
                pip.pick_up_tip()
            if vol_mix != 0:
                pip.transfer(
                    vol_per_trans,
                    source.top(h_offset_src),
                    dest.top(h_offset_dest),
                    mix_after=(3, vol_mix),
                    new_tip='never'
                )
            else:
                pip.transfer(
                    vol_per_trans,
                    source.top(h_offset_src),
                    dest.top(h_offset_dest),
                    new_tip='never'
                )
            pip.blow_out(dest.top(h_offset_dest))
            pip.touch_tip(v_offset=h_offset_dest)
            if change_tips == 'always':
                pip.drop_tip()
        if change_tips == 'once per well':
            pip.drop_tip()

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
    filename = f"detailed_action_json/2c81c0.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)