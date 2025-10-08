import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/42d27b/42d27b.ot2.apiv2.py"

metadata = {
    'protocolName': 'Quant-iT dsDNA Broad-Range Assay Kit',
    'author': 'Chaz <chaz@opentrons.com',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.1'
}


def run(protocol):
    [p300mnt, p10mnt] = get_values(  # noqa: F821
        'p300mnt', 'p10mnt')

    # load labware and pipettes
    res = protocol.load_labware('nest_12_reservoir_15ml', '1')
    tips300 = [protocol.load_labware('opentrons_96_tiprack_300ul', '4')]
    tips10 = [protocol.load_labware('opentrons_96_tiprack_10ul', '5')]
    aplate = protocol.load_labware('axygen_96_wellplate', '2')
    tube_plate = protocol.load_labware('micronics_96_tubes', '3')

    p300 = protocol.load_instrument('p300_multi', p300mnt, tip_racks=tips300)
    p10 = protocol.load_instrument('p10_multi', p10mnt, tip_racks=tips10)

    # Step 1
    wells11 = ['A'+str(i) for i in range(1, 12)]

    p300.pick_up_tip()

    for well in wells11:
        p300.transfer(99, res['A1'], aplate[well].top(), new_tip='never')

    p300.drop_tip()

    # Step 2
    p300.transfer(95, res['A1'], aplate['A12'])

    # Step 3
    for well in wells11:
        p10.pick_up_tip()
        p10.transfer(1, tube_plate[well], aplate[well], new_tip='never')
        p10.blow_out(aplate[well].top())
        p10.drop_tip()

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
    filename = f"detailed_action_json/42d27b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)