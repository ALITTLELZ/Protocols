import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1ccd23-station-A/generic_station_A.ot2.apiv2.py"

from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'Sample plating protocol',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.8'
}


def run(ctx: protocol_api.ProtocolContext):

    [num_samples, vol_sample, asp_height, p20_type, strip_type,
     tip_track] = get_values(  # noqa: F821
        'num_samples', 'vol_sample', 'asp_height', 'p20_type', 'strip_type',
        'tip_track')

    # load labware
    if 'multi' in p20_type:
        ic = ctx.load_labware(
            strip_type, '1',
            'chilled tubeblock for internal control (strip 1)').wells()[0]
    else:
        ic = ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', '1'
            '2ml Eppendorf tube for internal control (well A1)').wells()[0]
    source_racks = [
        ctx.load_labware('custom_24_tuberack_5ml', slot,
                         'source tuberack ' + str(i+1))
        for i, slot in enumerate(['2', '3', '5', '6'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '4', '96-deepwell sample plate')
    tipracks20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot,
                         '20µl filter tiprack')
        for slot in ['7', '8', '9']]
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', slot,
                                     '1000µl filter tiprack')
                    for slot in ['10', '11']]

    # load pipette
    pip20 = ctx.load_instrument(p20_type, 'left', tip_racks=tipracks20)
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:num_samples]
    dests_single = dest_plate.wells()[:num_samples]
    num_cols = math.ceil(num_samples/8)
    dests_multi = dest_plate.rows()[0][:num_cols]

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if tip_track and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][p1000] = data['tips1000']
                else:
                    tip_log['count'][p1000] = 0
                if 'tips20' in data:
                    tip_log['count'][pip20] = data['tips20']
                else:
                    tip_log['count'][pip20] = 0
    else:
        tip_log['count'] = {p1000: 0, pip20: 0}

    if 'multi' in p20_type:
        tips20 = [tip for rack in tipracks20 for tip in rack.rows()[0]]
    else:
        tips20 = [tip for rack in tipracks20 for tip in rack.wells()]
    tip_log['tips'] = {
        p1000: [tip for rack in tipracks1000 for tip in rack.wells()],
        pip20: tips20
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p1000, pip20]
    }

    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before  resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1

    # transfer sample
    for s, d in zip(sources, dests_single):
        pick_up(p1000)
        p1000.transfer(vol_sample, s.bottom(asp_height), d.bottom(5),
                       air_gap=100, new_tip='never')
        p1000.air_gap(100)
        p1000.drop_tip()

    # transfer internal control + proteinase K
    dests = dests_single if 'single' in p20_type else dests_multi
    for d in dests:
        pick_up(pip20)
        pip20.transfer(10, ic.bottom(2), d.bottom(10), air_gap=5,
                       new_tip='never')
        pip20.air_gap(5)
        pip20.drop_tip()

    ctx.comment('Move deepwell plate (slot 4) to Station B for RNA  extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][p1000],
            'tips20': tip_log['count'][pip20]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)

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
    filename = f"detailed_action_json/1ccd23-station-A.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)