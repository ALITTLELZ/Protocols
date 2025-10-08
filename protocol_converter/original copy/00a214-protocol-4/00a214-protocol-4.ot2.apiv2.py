import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/00a214-protocol-4/00a214-protocol-4.ot2.apiv2.py"

import csv
import os

metadata = {
    'protocolName': 'Media Exchange',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [num_plates, asp_speed,
     asp_height, disp_height, sec_ex] = get_values(  # noqa: F821
        'num_plates', 'asp_speed', 'asp_height', 'disp_height', 'sec_ex')

    # load labware and pipettes
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', '1')

    if num_plates > 6:
        raise Exception('This protocol can only accommodate up to 6 plates')

    plates = [
        protocol.load_labware(
            'eppendorf_96_wellplate_200ul',
            str(s)) for s in range(2, 8)][:num_plates]

    res = protocol.load_labware('nest_12_reservoir_15ml', '10')
    media1 = res.wells()[:num_plates]
    media2 = res.wells()[6:6+num_plates]

    waste = protocol.load_labware('nest_1_reservoir_195ml', '11',
                                  'Liquid Waste').wells()[0].top()

    p300 = protocol.load_instrument('p300_multi_gen2', 'left')

    p300.flow_rate.aspirate = asp_speed
    p300.flow_rate.dispense = asp_speed
    p300.flow_rate.blow_out = 300

    # create pick_up function for tips
    # Tip tracking between runs
    if not protocol.is_simulating():
        file_path = '/data/csv/tiptracking.csv'
        file_dir = os.path.dirname(file_path)
        # check for file directory
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        # check for file; if not there, create initial tip count tracking
        if not os.path.isfile(file_path):
            with open(file_path, 'w') as outfile:
                outfile.write("0, 0\n")

    tip_count_list = []
    if protocol.is_simulating():
        tip_count_list = [0, 0]
    else:
        with open(file_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            tip_count_list = next(csv_reader)

    tip300count = int(tip_count_list[0])

    def pick_up():
        nonlocal tip300count

        if tip300count == 12:
            for _ in range(6):
                protocol.set_rail_lights(not protocol.rail_lights_on)
                protocol.delay(seconds=1)
            protocol.pause('Please replace tips.')
            p300.reset_tipracks()
            tip300count = 0
        p300.pick_up_tip(tips300.rows()[0][tip300count])
        tip300count += 1

    for idx, (plate, res_src) in enumerate(zip(plates, media1)):
        wells = plate.rows()[0]
        protocol.comment(f'Removing media from plate {idx+1}...')
        pick_up()
        for well in wells:
            p300.aspirate(120, well.bottom(asp_height))
            p300.dispense(120, waste)
        protocol.comment(f'Adding differentiation media to plate {idx+1}...')
        for well in wells:
            p300.aspirate(140, res_src)
            p300.dispense(140, well.bottom(disp_height))
        p300.drop_tip()

    if sec_ex == 'Yes':
        for idx, (plate, res_src) in enumerate(zip(plates, media2)):
            wells = plate.rows()[0]
            protocol.comment(f'Removing 140uL media from plate {idx+1}...')
            pick_up()
            for well in wells:
                p300.aspirate(140, well.bottom(asp_height))
                p300.dispense(140, waste)
            protocol.comment(f'Adding differentiation media to plate {idx+1}')
            for well in wells:
                p300.aspirate(140, res_src)
                p300.dispense(140, well.bottom(disp_height))
            p300.drop_tip()

    # write updated tipcount to CSV
    new_tip_count = str(tip300count)+", "+str(tip_count_list[1])+"\n"
    if not protocol.is_simulating():
        with open(file_path, 'w') as outfile:
            outfile.write(new_tip_count)

    protocol.comment('Protocol complete!')

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
    filename = f"detailed_action_json/00a214-protocol-4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)