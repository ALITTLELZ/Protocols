import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1464-3/ELISA_protocol_part3.ot2.apiv2.py"

metadata = {
    'protocolName': 'Substrate and Stop Solution Addition',
    'author': 'Alise <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.14'
}


def run(ctx):
    [number_of_columns] = get_values(  # noqa: F821
     'number_of_columns')

    if number_of_columns > 12:
        raise Exception('The number of columns cannot exceed 12.')
    if number_of_columns % 2 == 1:
        raise Exception('The number of columns should be even.')

    # labware setup
    trough = ctx.load_labware('nest_12_reservoir_15ml', '8')
    plate = ctx.load_labware('corning_96_wellplate_360ul_flat', '9')

    tiprack_m300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
                    for slot in ['3', '7']]

    # instrument setup
    m300 = ctx.load_instrument(
        'p300_multi_gen2',
        mount='left',
        tip_racks=tiprack_m300)

    # reagents setup
    TMB_substrate = trough.wells_by_name()['A6']
    stop_solution = trough.wells_by_name()['A12']

    """
    Adding TMB substrate
    """

    chunks = [
              plate.rows()[0][i:i+2]
              for i in range(0, len(plate.rows()[0][:number_of_columns]),
                             2)
                    ]
    m300.pick_up_tip()
    for chunk in chunks:
        m300.aspirate(200, TMB_substrate)
        for i, well in enumerate(chunk):
            m300.dispense(100, well.top())
            if i == 1:
                ctx.delay(seconds=1.5)
                m300.blow_out()
        ctx.comment('\n')
    m300.drop_tip()

    ctx.delay(minutes=30)

    """
    Adding Stop Solution
    """
    for col in plate.columns()[:number_of_columns]:
        m300.pick_up_tip()
        m300.transfer(100, stop_solution, col, new_tip='never')
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
    filename = f"detailed_action_json/1464-3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)