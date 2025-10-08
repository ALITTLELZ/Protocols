import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/sci-dynabeads-tube-1/Dynabeads_IP_96well.ot2.apiv2.py"

# flake8: noqa
from opentrons.types import Point

metadata = {
    'protocolName': 'DYNABEADS FOR IP - 96 well',
    'author': 'Boren Lin <boren.lin@opentrons.com>',
    'source': '',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_samples] = get_values(  # noqa: F821
        'num_samples')

    asp_height = 0.5
    length_from_side = 2.5
    p300_mount = 'left'
    wash_volume = 200
    wash_times = 3
    asp_count = num_samples//5
    leftover = num_samples%5


    total_cols = int(num_samples//8)
    r1 = int(num_samples%8)
    if r1 != 0: total_cols = total_cols + 1

    # load labware
    #wash_res = ctx.load_labware('nest_12_reservoir_15ml', '2', 'wash')

    mag_mod = ctx.load_module('magnetic module gen2', '1')
    mag_plate = mag_mod.load_labware('nest_96_wellplate_2ml_deep')
    #temp_mod = ctx.load_module('temperature module gen2', '3')
    #elution_plate = temp_mod.load_labware('opentrons_96_aluminumblock_nest_wellplate_100ul')
    reagent_tube = ctx.load_labware('opentrons_15_tuberack_nest_15ml_conical', '4', 'reagents')
    samples = ctx.load_labware('nest_96_wellplate_2ml_deep', '5', 'samples')
    tiprack = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in ['7', '8']]
    waste_res = ctx.load_labware('nest_1_reservoir_195ml', '9', 'waste')

    # load pipette
    pip = ctx.load_instrument('p300_multi_gen2', p300_mount, tip_racks=tiprack)
    pip_single = ctx.load_instrument('p300_single_gen2', 'right', tip_racks=tiprack)

    # liquids
    #wash = wash_res.wells()[:total_cols]

    beads = reagent_tube.rows()[0][0]
    ab = reagent_tube.rows()[0][1]
    #elution = reagent_tube.rows()[0][4]
    waste = waste_res.wells()[0]
    samples = samples.rows()[0][:total_cols]
    working_cols = mag_plate.rows()[0][:total_cols]
    #final_cols = elution_plate.rows()[0][:total_cols]

    def remove_supernatant(vol):
        ctx.comment('\n\n\n~~~~~~~~REMOVING SUPERNATANT~~~~~~~~\n')
        pip.pick_up_tip()
        pip.flow_rate.aspirate = 45
        for i, col in enumerate(working_cols):
            side = -1 if i % 2 == 0 else 1
            aspirate_loc = col.bottom(z=asp_height).move(
                            Point(x=(col.length/2-length_from_side)*side))
            pip.transfer(vol,
                         aspirate_loc,
                         waste.bottom(z=25),
                         new_tip='never'
                         )
        pip.flow_rate.aspirate = 92
        pip.drop_tip()

    # protocol
    mag_mod.disengage()
    ctx.comment('\n\n\n~~~~~~~~MIXING BEADS~~~~~~~~\n')
    pip_single.pick_up_tip()
    for i in range(total_cols):
        h = 5 + i * 3
        pip_single.mix(5, 250, beads.bottom(z=h), rate = 5)

    ctx.comment('\n\n\n~~~~~~~~ADDING BEADS TO PLATE~~~~~~~~\n')
    for i in range(0, asp_count):
        pip_single.mix(5, 250, beads.bottom(z=2), rate = 5)
        pip_single.aspirate(250, beads.bottom(z=1))
        for j in range(0, 5):
            beads_well = mag_plate.wells()[j+i*5]
            pip_single.dispense(50, beads_well.bottom(z=10))
        pip_single.touch_tip()
    if leftover != 0:
        pip_single.mix(5, leftover*50, beads.bottom(z=2), rate = 5)
        pip_single.aspirate(leftover*50, beads.bottom(z=1))
        for j in range(0, leftover):
            beads_well = mag_plate.wells()[j+asp_count*5]
            pip_single.dispense(50, beads_well.bottom(z=10))
        pip_single.touch_tip()
    pip_single.drop_tip()

    mag_mod.engage(height_from_base=4.2)
    ctx.delay(minutes=2)
    remove_supernatant(60)
    mag_mod.disengage()

    ctx.comment('\n\n\n~~~~~~~~ADDING Ab~~~~~~~~\n')
    pip_single.pick_up_tip()
    for i in range(0, asp_count):
        pip_single.mix(5, 250, ab.bottom(z=2), rate = 5)
        pip_single.aspirate(250, ab.bottom(z=1))
        for j in range(0, 5):
            ab_well = mag_plate.wells()[j+i*5]
            pip_single.dispense(50, ab_well.bottom(z=10))
        pip_single.touch_tip()
    if leftover != 0:
        pip_single.mix(5, leftover*50, ab.bottom(z=2), rate = 5)
        pip_single.aspirate(leftover*50, ab.bottom(z=1))
        for j in range(0, leftover):
            ab_well = mag_plate.wells()[j+asp_count*5]
            pip_single.dispense(50, ab_well.bottom(z=10))
        pip_single.touch_tip()
    pip_single.drop_tip()

    ctx.comment('\n\n\n~~~~~~~~ADDING SAMPLE~~~~~~~~\n')
    for sample, dest in zip(samples, working_cols):
        pip.pick_up_tip()
        pip.aspirate(200, sample.bottom(z=1))
        pip.dispense(200, dest.bottom(z=5))
        pip.mix(10, 180, dest.bottom(z=1), rate =3)
        pip.drop_tip()

    ctx.pause('10 MINUTE GENTLE SHAKING, ROOM TEMP')

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
    filename = f"detailed_action_json/sci-dynabeads-tube-1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)