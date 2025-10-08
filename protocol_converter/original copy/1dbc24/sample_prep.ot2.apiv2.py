import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1dbc24/sample_prep.ot2.apiv2.py"

metadata = {
    'protocolName': 'Reagent Addition',
    'author': 'Nick <ndiehl@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.12'
}


def run(ctx):

    num_samples, _tip_start_column = get_values(  # noqa: F821
        'num_samples', '_tip_start_column')

    # labware setup
    plate = ctx.load_labware('corning_96_wellplate_360ul_flat', '2')
    tiprack300 = ctx.load_labware('opentrons_96_tiprack_300ul', '3')
    wistd = ctx.load_labware('reagent_1_reservoir_130000ul', '5',
                             'WISTD').wells()[0]
    water = ctx.load_labware('reagent_1_reservoir_130000ul', '6',
                             'water').wells()[0]

    # instrument setup
    m300 = ctx.load_instrument('p300_multi_gen2', 'left',
                               tip_racks=[tiprack300])

    if num_samples >= 12:
        samples = plate.rows()[0]
    else:
        samples = plate.rows()[0][:num_samples]

    # start at proper tip
    start_index = _tip_start_column - 1
    for col in tiprack300.columns()[:start_index]:
        for well in col:
            well.has_tip = False

    # transfer WISTD to wells
    for reagent in [wistd, water]:
        m300.pick_up_tip()
        m300.mix(3, 250, reagent)
        for dest in samples:
            m300.transfer(250, reagent, dest.top(-1), new_tip='never')
            m300.blow_out(dest.top(-1))
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
    filename = f"detailed_action_json/1dbc24.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)