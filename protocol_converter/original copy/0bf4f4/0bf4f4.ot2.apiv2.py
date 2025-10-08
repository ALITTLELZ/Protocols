import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0bf4f4/0bf4f4.ot2.apiv2.py"

"""Protocol."""
from opentrons.types import Point

metadata = {
    'protocolName': 'Ilumina DNA Prep Part 1 - Tagment DNA',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):
    """Protocol."""
    [num_samp, p300_tip_start_col,
        m20_mount, m300_mount] = get_values(  # noqa: F821
      "num_samp", "p300_tip_start_col", "m20_mount", "m300_mount")

    if not 1 <= p300_tip_start_col <= 12:
        raise Exception("Enter a 200ul tip start column 1-12")

    num_samp = int(num_samp)
    num_col = int(num_samp/8)
    p300_tip_start_col = p300_tip_start_col-1

    # load labware
    reagent_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '1',
                                     label='Mastermix Plate')
    samples = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '2',
                               label='Sample Plate')
    final_plate = ctx.load_labware('biorad_96_wellplate_200ul_pcr', '3',
                                   label='Final Plate')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '4')
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
               for slot in ['5', '6', '7']]
    tiprack300 = ctx.load_labware('opentrons_96_filtertiprack_200ul', '8')

    # load instrument
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount, tip_racks=tiprack)
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount,
                               tip_racks=[tiprack300])

    # number of tips trash will accommodate before prompting user to empty
    switch = True
    drop_count = 0
    drop_threshold = 120

    def _drop(pip):
        nonlocal switch
        nonlocal drop_count
        side = 30 if switch else -18
        drop_loc = ctx.loaded_labwares[12].wells()[0].top().move(Point(x=side))
        pip.drop_tip(drop_loc)
        switch = not switch
        if pip.type == 'multi':
            drop_count += 8
        else:
            drop_count += 1
        if drop_count >= drop_threshold:
            m300.home()
            ctx.pause('Please empty tips from waste before resuming.')
            ctx.home()  # home before continuing with protocol
            drop_count = 0

    # reagents
    water = reservoir.wells()[0]
    mastermix = reagent_plate.rows()[0][0]

    # add water to empty bio rad plate
    m20.pick_up_tip()
    for col in final_plate.rows()[0][:num_col]:
        m20.aspirate(10, water)
        m20.dispense(10, col)
        m20.blow_out(col.top())
    _drop(m20)
    ctx.comment('\n\n')

    # add dna to plate
    for i, (dna, dest) in enumerate(zip(samples.rows()[0],
                                    final_plate.rows()[0][:num_col])):
        m20.pick_up_tip()
        m20.mix(10, 15, dna)
        m20.aspirate(5, dna)
        m20.dispense(5, dest)
        m20.mix(10, 12, dest)
        _drop(m20)
    ctx.comment('\n\n')

    # add mastermix to plate
    m20.flow_rate.aspirate = 4
    m20.flow_rate.dispense = 4

    for i, col in enumerate(final_plate.rows()[0][:num_col]):
        if i % 3 == 0:
            m300.pick_up_tip(tiprack300.rows()[0][p300_tip_start_col])
            m300.mix(15, 80, mastermix)
            m300.blow_out(mastermix.top())
        if num_col-i <= 3 and m300.has_tip:
            _drop(m300)
        elif m300.has_tip:
            m300.return_tip()
        m20.pick_up_tip()
        m20.aspirate(10, mastermix)
        ctx.delay(seconds=1.5)
        m20.dispense(10, col)
        m20.mix(15, 18, col)
        m20.blow_out(col.top())
        _drop(m20)

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
    filename = f"detailed_action_json/0bf4f4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)