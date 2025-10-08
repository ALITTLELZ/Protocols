import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/199721/pooling.ot2.apiv2.py"

import os
import json

# metadata
metadata = {
    'protocolName': 'Pooling',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.4'
}


def run(ctx):

    [sample_vol, num_pool_sources, num_pools, p1000_mount, asp_speed,
     dispense_speed, asp_height, dispense_height, mix_reps, mix_vol,
     tip_strategy, tip_track] = get_values(  # noqa: F821
        'sample_vol', 'num_pool_sources', 'num_pools', 'p1000_mount',
        'asp_speed', 'dispense_speed', 'asp_height', 'dispense_height',
        'mix_reps', 'mix_vol', 'tip_strategy', 'tip_track')

    # labware
    primary_racks = [
        ctx.load_labware('alpaquaprimaryv3_24_tuberack_2000ul', slot,
                         'primary rack ' + str(i+1))
        for i, slot in enumerate(['4', '7', '10', '5', '8', '11'])]
    secondary_racks = [
        ctx.load_labware('alpaquasecondaryv3_24_tuberack_750ul', slot,
                         'secondary rack ' + str(i+1))
        for i, slot in enumerate(['2', '3'])]
    tipracks1000 = [
        ctx.load_labware('opentrons_96_tiprack_1000ul', slot)
        for slot in ['1', '6', '9']]

    sources_reordered = [
        row[i*3:i*3+num_pool_sources]
        for rack in primary_racks
        for row in rack.rows()
        for i in range(2)][:num_pools]
    dests = [
        well for rack in secondary_racks for well in rack.wells()][:num_pools]

    # pipette
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', p1000_mount, tip_racks=tipracks1000)
    p1000.flow_rate.aspirate = asp_speed
    p1000.flow_rate.dispense = dispense_speed

    # determine starting tip
    tip_log_file_path = '/data/pooling/tip_track.json'
    # tip_log_file_path = 'protocols/199721/pooling/tip_track.json'
    tip_log_folder_path = os.path.dirname(tip_log_file_path)

    tip_count = 0
    if not ctx.is_simulating():
        if not os.path.exists(tip_log_folder_path):
            os.makedirs(tip_log_folder_path)
        if (
                tip_track
                and os.path.isfile(tip_log_file_path)
                and os.stat(tip_log_file_path).st_size > 0):
            with open(tip_log_file_path, 'r') as tip_file:
                data = json.load(tip_file)
                if 'tips1000' in data:
                    tip_count = data['tips1000']

    tip_log = {
        p1000: {
            'tip_list': [
                tip for rack in tipracks1000 for tip in rack.wells()],
            'tip_max': len(tipracks1000) * 96,
            'tip_count': tip_count
        }
    }

    def pick_up(pip):
        if tip_log[p1000]['tip_count'] >= tip_log[p1000]['tip_max']:
            ctx.pause('Please replace 1000ul tipracks in slots 1, 6, and 9  before resuming.')
            tip_log[p1000]['tip_count'] = 0
        p1000.pick_up_tip(
            tip_log[p1000]['tip_list'][tip_log[p1000]['tip_count']])
        tip_log[p1000]['tip_count'] += 1

    for source_set, dest in zip(sources_reordered, dests):
        if tip_strategy == 'once':
            pick_up(p1000)
        for i, source in enumerate(source_set):
            if tip_strategy == 'always':
                pick_up(p1000)
            if p1000.current_volume > 0:
                p1000.dispense(p1000.current_volume, source.top())
            p1000.mix(mix_reps, mix_vol, source.bottom(asp_height))
            p1000.transfer(sample_vol, source.bottom(asp_height),
                           dest.bottom(dispense_height), air_gap=20,
                           new_tip='never')
            if i == len(source_set) - 1:
                p1000.mix(mix_reps, mix_vol, dest.bottom(dispense_height))
            p1000.blow_out(dest.top(-2))
            p1000.touch_tip(dest)
            p1000.air_gap(20)
            if tip_strategy == 'always':
                p1000.drop_tip()
        if tip_strategy == 'once':
            p1000.drop_tip()

    if not ctx.is_simulating():
        with open(tip_log_file_path, 'w') as tip_file:
            data = {'tips1000': tip_log[p1000]['tip_count']}
            json.dump(data, tip_file)

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
    filename = f"detailed_action_json/199721.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)