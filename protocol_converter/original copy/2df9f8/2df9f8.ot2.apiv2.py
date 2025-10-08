import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/2df9f8/2df9f8.ot2.apiv2.py"

"""Protocol."""
metadata = {
    'protocolName': 'Plate Filling Heat Inactivated Covid Samples for PCR',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):
    """Protocol."""
    [num_samp, plate, m300_mount] = get_values(  # noqa: F821
        'num_samp', 'plate', 'm300_mount')

    if not 1 <= num_samp <= 94:
        raise Exception("Enter a number of samples between 1-94")

    # load labware
    plate = ctx.load_labware('nest_96_wellplate_2ml_deep', '5')
    reservoir = ctx.load_labware('nest_1_reservoir_195ml', '1')
    tiprack = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
               for slot in ['3', '4']]
    tuberacks = [ctx.load_labware(
        'opentrons_15_tuberack_5000ul', slot)
        for slot in ['6', '7', '8', '9', '10', '11', '2']]

    # load instrument
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=tiprack)

    # multi as single channel
    num_chan = 1
    tip_count = 0
    tips_ordered = [tip
                    for row in tiprack[1].rows()[
                     len(tiprack[1].rows())-num_chan::-1*num_chan]
                    for tip in row]

    def pick_up():
        nonlocal tip_count
        m300.pick_up_tip(tips_ordered[tip_count])
        tip_count += 1

    # protocol
    sample_tubes = [tube for rack in tuberacks
                    for row in rack.rows()
                    for tube in row][:num_samp]

    plate_wells = [well for row in plate.rows() for well in row]

    # distribute saline
    m300.pick_up_tip()
    for col in plate.rows()[0]:
        m300.aspirate(250, reservoir.wells()[0])
        m300.touch_tip()
        m300.dispense(250, col)
        m300.blow_out()
    m300.drop_tip()

    # distribute sample
    for s, d in zip(sample_tubes, plate_wells[2:]):
        pick_up()
        m300.aspirate(250, s)
        m300.touch_tip()
        m300.dispense(250, d)
        m300.blow_out()
        m300.drop_tip()

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
    filename = f"detailed_action_json/2df9f8.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)