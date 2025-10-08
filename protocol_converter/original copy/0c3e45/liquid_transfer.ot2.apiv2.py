import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0c3e45/liquid_transfer.ot2.apiv2.py"

import json
import os

metadata = {
    'protocolName': 'Liquid Transfer',
    'author': 'Nick Diehl <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.12'
}

TIP_TRACK = True


def run(ctx):

    plates = [ctx.load_labware(
        'nest_96_wellplate_200ul_flat', str(slot), f'plate {slot}')
        for slot in range(1, 10)]
    reservoir = ctx.load_labware('nest_1_reservoir_195ml', '10')
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '11')]

    m300 = ctx.load_instrument('p300_multi_gen2', 'right', tip_racks=tiprack)
    m300.flow_rate.aspirate = 300
    m300.flow_rate.dispense = 300

    sivi_1 = reservoir.wells()[0]

    tip_log = {val: {} for val in ctx.loaded_instruments.values()}

    folder_path = '/data/liquid_transfer'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                for pip in tip_log:
                    if pip.name in data:
                        tip_log[pip]['count'] = data[pip.name]
                    else:
                        tip_log[pip]['count'] = 0
        else:
            for pip in tip_log:
                tip_log[pip]['count'] = 0
    else:
        for pip in tip_log:
            tip_log[pip]['count'] = 0

    for pip in tip_log:
        if pip.type == 'multi':
            tip_log[pip]['tips'] = [tip for rack in pip.tip_racks
                                    for tip in rack.rows()[0]]
        else:
            tip_log[pip]['tips'] = [tip for rack in pip.tip_racks
                                    for tip in rack.wells()]
        tip_log[pip]['max'] = len(tip_log[pip]['tips'])

    def find_tip(pip, loc=None):
        if tip_log[pip]['count'] == tip_log[pip]['max'] and not loc:
            ctx.pause(f'Replace {str(pip.max_volume)}µl tipracks before  resuming.')
            pip.reset_tipracks()
            tip_log[pip]['count'] = 0
        if loc:
            tip = loc
        else:
            tip = tip_log[pip]['tips'][tip_log[pip]['count']]
            tip_log[pip]['count'] += 1
        return tip

    # liquid transfers
    tip = find_tip(m300)
    column_ind = tiprack[0].rows()[0].index(tip)

    ctx.home()
    ctx.pause(f'Ensure tips are placed in column {column_ind+1} of tiprack on  slot 11 before resuming.')
    m300.pick_up_tip(tip)
    for plate in plates:
        for d in plate.rows()[0]:
            m300.aspirate(20, sivi_1.top())
            m300.aspirate(100, sivi_1.bottom(1))
            m300.dispense(m300.current_volume, d.bottom(6.5))
    m300.drop_tip()

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {pip.name: tip_log[pip]['count'] for pip in tip_log}
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
    filename = f"detailed_action_json/0c3e45.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)