import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0045f1/0045f1.ot2.apiv2.py"

from types import MethodType

metadata = {
    'protocolName': 'Variable Slide Dispensing',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [num_tubes, num_slides, spot_labware,
     spot_volume, asp_rate, disp_rate, p20_mount] = get_values(  # noqa: F821
        "num_tubes", "num_slides", "spot_labware",
        "spot_volume", "asp_rate", "disp_rate", "p20_mount")
    num_tubes = int(num_tubes)

    if not 1 <= num_slides <= 6:
        raise Exception("Enter a slide number 1-6")
    if not 1 <= spot_volume <= 6:
        raise Exception("Enter a volume between 1-20ul")
    num_plates = 2 if num_slides > 3 else 1

    # load labware
    tuberack = ctx.load_labware(
                'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap', '3')
    tiprack = ctx.load_labware('opentrons_96_filtertiprack_10ul', '4')
    slide_plates = [ctx.load_labware(spot_labware,
                    slot) for slot in ['1', '2'][:num_plates]]

    # load instrument
    p20 = ctx.load_instrument('p20_single_gen2',
                              p20_mount,
                              tip_racks=[tiprack])

    p20.flow_rate.aspirate = p20.flow_rate.aspirate*asp_rate
    p20.flow_rate.dispense = p20.flow_rate.dispense*disp_rate

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
        self.move_to(well_location.top(z=10))
        ctx.max_speeds[axis] = previous_limit

    # bind additional methods to pipettes
    for pipette_object in [p20]:
        for method in [slow_tip_withdrawal]:
            setattr(
             pipette_object, method.__name__,
             MethodType(method, pipette_object))

    all_wells = []

    for z in [2, 4]:
        for k in range(4):
            for i in range(2):
                for j, plate in enumerate(slide_plates):
                    if j > 0:
                        rel_slides = num_slides - 3
                    for column in plate.columns()[k:(rel_slides if j > 0
                                                  else num_slides)*4:4]:
                        for well in column[z+i:14+i:4]:
                            all_wells.append(well)

    all_wells_chunks = [all_wells[i:i+3*num_slides]
                        for i in range(0, len(all_wells), 3*num_slides)]

    for tube, chunk in zip(tuberack.wells()[:num_tubes], all_wells_chunks):
        p20.pick_up_tip()
        dispense_ctr = 0
        tot_vol = len(chunk)*spot_volume
        for well in chunk:

            # ASPIRATE
            if p20.current_volume <= spot_volume:
                if p20.current_volume > 0:
                    p20.dispense(p20.current_volume, ctx.fixed_trash['A1'])
                p20.aspirate(tot_vol+1 if tot_vol+1 < 10 else 10,
                             tube)
                p20.touch_tip(radius=0.9)

            # MOVE TO
            p20.move_to(well.top(z=10))
            ctx.delay(seconds=1.5)
            p20.dispense(spot_volume, well.top())

            # SLOW WITHDRAWAL
            ctx.delay(seconds=1.5)
            p20.slow_tip_withdrawal(10, well)
            dispense_ctr += 1
            tot_vol -= spot_volume
        if p20.current_volume > 0:
            p20.dispense(p20.current_volume, ctx.fixed_trash['A1'])
        p20.drop_tip()
        ctx.comment('\n')

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
    filename = f"detailed_action_json/0045f1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)