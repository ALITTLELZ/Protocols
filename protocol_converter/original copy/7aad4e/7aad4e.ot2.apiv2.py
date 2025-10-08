import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/7aad4e/7aad4e.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cell Culture Cherry Picking with CSV File',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [csv, p300_mount] = get_values(  # noqa: F821
        "csv", "p300_mount")

    # csv --> nested list
    list_of_rows = [[val.strip() for val in line.split(',')]
                    for line in csv.splitlines()
                    if line.split(',')[0].strip()][1:]

    # mapping
    source_slot = 0
    source_well = 1
    transfer_vol = 2
    dest_slot = 3
    dest_well = 4

    num_384_plates = []
    num_96_plates = []
    for row in list_of_rows:
        num_384_plates.append(int(row[source_slot]))
        num_96_plates.append(int(row[dest_slot]))
    num_384_plates = len(set(num_384_plates))

    num_96_plates = len(set(num_96_plates))

    # labware
    source_plates = [ctx.load_labware('perkinelmer_384_wellplate_110ul', slot)
                     for slot in ['1', '2', '3', '4', '5', '6'][:num_384_plates]]  # noqa: E501
    dest_plates = [ctx.load_labware('corning_96_wellplate_360ul', slot)
                   for slot in ['7', '8'][:num_96_plates]]
    tiprack200 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
                  for slot in ['10', '11']]

    # instruments
    p300 = ctx.load_instrument('p300_single_gen2',
                               p300_mount, tip_racks=tiprack200)  # noqa: E501

    airgap = 10
    for line in list_of_rows:
        source = source_plates[int(line[source_slot])-1].wells_by_name()[line[source_well]]  # noqa: E501
        dest = dest_plates[int(line[dest_slot])-1].wells_by_name()[line[dest_well]]  # noqa: E501
        p300.pick_up_tip()
        p300.mix(3, 0.80*int(line[transfer_vol]), source)
        p300.aspirate(int(line[transfer_vol]), source)
        p300.air_gap(airgap)
        p300.dispense(int(line[transfer_vol])+airgap, dest)
        p300.drop_tip()

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
    filename = f"detailed_action_json/7aad4e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)