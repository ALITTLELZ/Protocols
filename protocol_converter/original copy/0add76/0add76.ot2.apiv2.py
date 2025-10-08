import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0add76/0add76.ot2.apiv2.py"

metadata = {
    'protocolName': 'DNA and Water Transfer with CSV File',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [v_csv, p10_mount, p300_mount] = get_values(  # noqa: F821
        "v_csv", "p10_mount", "p300_mount")

    # load Labware
    reservoir = ctx.load_labware('ek_scientific_reservoir', '6')
    pcr_plate = ctx.load_labware('vwrpcr_96_wellplate_200ul', '8')
    tiprack_300 = ctx.load_labware('opentrons_96_tiprack_300ul', '9')
    dna_stock = ctx.load_labware('vwr_square_96_microplate_2000ul', '10')
    tiprack_10 = ctx.load_labware('geb_96_tiprack_10ul', '11')

    # load instruments
    p10 = ctx.load_instrument('p10_single', p10_mount,
                              tip_racks=[tiprack_10])

    p300 = ctx.load_instrument('p300_single', p300_mount,
                               tip_racks=[tiprack_300])

    # csv file --> nested list
    transfer = [[val.strip() for val in line.split(',')]
                for line in v_csv.splitlines()
                if line.split(',')[0].strip()][1:]

    for line in transfer:
        if not p300.has_tip:
            p300.pick_up_tip()
        vol_water = float(line[2])
        well = line[3]
        p300.transfer(vol_water, reservoir['A1'],
                      pcr_plate.wells_by_name()[well], new_tip='never')
    if p300.has_tip:
        p300.drop_tip()

    for line in transfer:
        vol_dna = float(line[1])
        well = line[3]
        p10.transfer(vol_dna, dna_stock.wells_by_name()[well],
                     pcr_plate.wells_by_name()[well])

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
    filename = f"detailed_action_json/0add76.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)