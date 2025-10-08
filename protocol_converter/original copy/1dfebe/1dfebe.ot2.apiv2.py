import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1dfebe/1dfebe.ot2.apiv2.py"

import itertools
from types import MethodType

metadata = {
    'protocolName': 'Urine Toxicology Using Enzyme Hydrolysis',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [use_csv, csv_samp, num_samp, tip_withdrawal_speed,
        samp_asp_height, disp_height, p300_mount] = get_values(  # noqa: F821
        "use_csv", "csv_samp", "num_samp",
        "tip_withdrawal_speed", "samp_asp_height", "disp_height", "p300_mount")

    if not 1 <= num_samp <= 81:
        raise Exception("Enter a sample number between 1-81")

    if not 5 <= tip_withdrawal_speed <= 50:
        raise Exception("Enter a gantry speed between 5 and 50 mm/s")

    # load labware
    tuberacks = [ctx.load_labware('custom_24_tuberack_7500ul',
                                  slot, label="SAMPLE RACK")
                 for slot in ['4', '1', '5', '2']]
    plate = ctx.load_labware('nest_96_wellplate_1000ul', '3')
    tiprack = ctx.load_labware('opentrons_96_tiprack_300ul', '10')

    # load instrument
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=[tiprack])

    if csv_samp[0] == ',':
        csv_samp = csv_samp[1:]
    plate_map_nest = [[val.strip() for val in line.split(',')][1:]
                      for line in csv_samp.splitlines()
                      if line.split(',')[0].strip()][1:]

    # protocol
    tube_map_double_nest = [

                  [tuberacks[j].columns()[i]+tuberacks[j+1].columns()[i]
                   for i in range(len(tuberacks[0].columns()))]
                  for j in range(0, 4, 2)

                  ]

    tube_map_nest = list(itertools.chain.from_iterable(tube_map_double_nest))
    full_tube_map = list(itertools.chain.from_iterable(tube_map_nest))
    asp_height_concat = list(itertools.chain.from_iterable(plate_map_nest))
    controls = 15

    tube_map = full_tube_map[controls:controls+num_samp]
    sample_plate = plate.wells()[controls:controls+num_samp]
    asp_height_map = asp_height_concat[controls:controls+num_samp]

    def create_chunks(list, n):
        for i in range(0, len(list), n):
            yield list[i:i+n]

    def slow_tip_withdrawal(
     self, speed_limit, well_location):
        if self.mount == 'right':
            axis = 'A'
        else:
            axis = 'Z'
        previous_limit = None
        if axis in ctx.max_speeds.keys():
            for key, value in ctx.max_speeds.items():
                if key == axis:
                    previous_limit = value
        ctx.max_speeds[axis] = speed_limit
        self.move_to(well_location.top())
        ctx.max_speeds[axis] = previous_limit

    # bind additional methods to pipettes
    for pipette_object in [p300]:
        for method in [slow_tip_withdrawal]:
            setattr(
             pipette_object, method.__name__,
             MethodType(method, pipette_object))

    ctx.comment('Moving urine to plate')
    # move urine sample to plate
    for tube, dest_well, height in zip(tube_map, sample_plate, asp_height_map):
        p300.pick_up_tip()
        if use_csv:
            p300.aspirate(50, tube.bottom(
                          z=samp_asp_height
                          if height == 'X' or height == 'x' else 1))
        else:
            p300.aspirate(50, tube.bottom(z=samp_asp_height))
        p300.slow_tip_withdrawal(tip_withdrawal_speed, tube)
        p300.touch_tip()
        p300.dispense(50, dest_well.bottom(disp_height))
        p300.touch_tip(radius=0.9, v_offset=-2)
        p300.drop_tip()
    ctx.comment('\n\n\n\n\n\n')

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
    filename = f"detailed_action_json/1dfebe.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)