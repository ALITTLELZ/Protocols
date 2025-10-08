import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/315118/315118.ot2.apiv2.py"

metadata = {
    'protocolName': 'mock pooling',
    'author': 'Steve <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    ctx.set_rail_lights(True)

    [same_tip, clearance_aspirate, clearance_dispense, pool_location,
     wells_to_be_pooled, tip_rack] = get_values(  # noqa: F821
        "same_tip", "clearance_aspirate", "clearance_dispense",
        "pool_location", "wells_to_be_pooled", "tip_rack")

    # tips and p300 multi
    tipracks = [ctx.load_labware('opentrons_96_tiprack_300ul', '4')]

    p300m = ctx.load_instrument('p300_multi_gen2', 'left')

    # labware
    [ninety_six_2_ml, tube_rack] = [
     ctx.load_labware(labware, slot) for labware, slot in zip(
      ['nest_96_wellplate_2ml_deep',
       'lvltechnologies_48_wellplate_2000ul'], ['5', '6'])]

    # pool tube
    pool = tube_rack.wells_by_name()[pool_location]

    # use only the rear-most channel of the p300 multi
    num_channels_per_pickup = 1  # (only pickup tips on rear-most channel)
    tips_ordered = [
        tip for rack in tipracks
        for row in rack.rows()[
         len(rack.rows())-num_channels_per_pickup::-1*num_channels_per_pickup]
        for tip in row]

    tip_count = 0

    def pick_up(pip):
        nonlocal tip_count
        pip.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # transfer 20 ul from designated wells to pool
    for index, well in enumerate(wells_to_be_pooled.split(',')):
        if same_tip is False:
            pick_up(p300m)
        else:
            if index == 0:
                pick_up(p300m)
        p300m.aspirate(20, ninety_six_2_ml.wells_by_name()[well].bottom(
         clearance_aspirate))
        p300m.dispense(20, pool.bottom(clearance_dispense))
        if same_tip is False:
            p300m.drop_tip()
        else:
            if index == len(wells_to_be_pooled.split(',')) - 1:
                p300m.drop_tip()

    ctx.set_rail_lights(False)
    ctx.delay(seconds=10)

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
    filename = f"detailed_action_json/315118.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)