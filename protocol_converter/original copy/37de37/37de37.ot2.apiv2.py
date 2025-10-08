import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/37de37/37de37.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cherrypicking DNA and Pooling with CSV input',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [csv, num_plates, p20_mount] = get_values(  # noqa: F821
         "csv", "num_plates", "p20_mount")

    # load labware
    final_plate = ctx.load_labware('corning_96_wellplate_360ul_flat', '4')
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '5')
    initial_plates = [ctx.load_labware('corning_96_wellplate_360ul_flat', slot)
                      for slot in ['1', '2', '3'][:num_plates]]
    tipracks = [ctx.load_labware('opentrons_96_tiprack_20ul', slot)
                for slot in ['6', '9']]

    # load instrument
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount, tip_racks=tipracks)

    plate_map = [[val.strip() for val in line.split(',')]
                 for line in csv.splitlines()
                 if line.split(',')[0].strip()][1:]

    # csv_number columns
    plate_number = 1
    source_well = 2
    dest_well = 3
    sample_vol = 6
    diluent_vol = 7

    # load reagents
    diluent = reservoir.wells()[0]

    # transfer diluent
    p20.pick_up_tip()
    for row in plate_map:
        p20.transfer(float(row[diluent_vol]),
                     diluent,
                     final_plate.wells_by_name()[row[dest_well]],
                     new_tip='never')
    p20.drop_tip()
    ctx.comment('\n\n\n')

    # transfer sample and then pool
    for row in plate_map:
        p20.pick_up_tip()

        p20.transfer(float(row[sample_vol]),
                     initial_plates[int(row[plate_number])-1].wells_by_name()[
                     row[source_well]],
                     final_plate.wells_by_name()[row[dest_well]],
                     mix_before=(5, 20),
                     mix_after=(5, 20),
                     new_tip='never')
        p20.aspirate(5, final_plate.wells_by_name()[row[dest_well]])
        p20.dispense(5, final_plate.wells_by_name()['H12'])
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
    filename = f"detailed_action_json/37de37.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)