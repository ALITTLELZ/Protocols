import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/49de51-pt1/49de51-pt1.ot2.apiv2.py"

metadata = {
    'protocolName': 'MagMAX Plant DNA Isolation Kit [1/2]',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):
    [num_plates, deep_plate] = get_values(  # noqa: F821
        'num_plates', 'deep_plate')

    # load labware and pipette
    plate1, plate2 = [protocol.load_labware(
        deep_plate, s) for s in ['2', '5']]

    deep_plates = [protocol.load_labware(
        deep_plate, s) for s in ['3', '6']]

    tips = [protocol.load_labware(
        'opentrons_96_filtertiprack_200ul', s) for s in ['7', '10', '11']]
    res_lysis = protocol.load_labware('nest_1_reservoir_195ml', '4')
    res_precip = protocol.load_labware('nest_12_reservoir_15ml', '1')

    pip = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=tips)

    # create variables
    wells1 = plate1.rows()[0]
    wells2 = plate2.rows()[0]
    lysis_buffer = res_lysis['A1']
    precip1, precip2 = res_precip.wells()[:2]
    lysis_wells = wells1+wells2 if num_plates == 2 else wells1
    deep_wells = [well for row in deep_plates for well in row.rows()[0]]

    # Add 590uL of buffer
    protocol.comment('Adding 590uL of buffer to wells...')

    pip.pick_up_tip()

    for well in lysis_wells:
        for _ in range(3):
            pip.aspirate(196, lysis_buffer)
            pip.dispense(196, well.top(-2))

    pip.drop_tip()

    protocol.pause('Please remove plate for 10min incubation @ 65C. When ready  return plate(s) to deck and click RESUME')

    # Add 130uL of precipitation solution

    protocol.comment('Adding 130uL of precipitation to solution to wells...')

    pip.pick_up_tip()

    for well in wells1:
        pip.aspirate(130, precip1)
        pip.dispense(130, well.top(-2))

    if num_plates == 2:
        for well in wells2:
            pip.aspirate(130, precip2)
            pip.dispense(130, well.top(-2))

    pip.drop_tip()

    protocol.pause('Please remove plate(s), invert 2-3 times, and incubate on  ice for 5 minutes. When ready to continue, place plates back on deck and \
    click RESUME')

    # Transfer 400uL of sample to deep well plate

    protocol.comment('Transferring 400uL of supernatant to deep well plates')

    for src, dest in zip(lysis_wells, deep_wells):
        pip.pick_up_tip()
        for _ in range(2):
            pip.aspirate(200, src)
            pip.dispense(200, dest)
        pip.blow_out()
        pip.drop_tip()

    protocol.comment('Protocol complete. Store samples or move to DNA  purification')

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
    filename = f"detailed_action_json/49de51-pt1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)