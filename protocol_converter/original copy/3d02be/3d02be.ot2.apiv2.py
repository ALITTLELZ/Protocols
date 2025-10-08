import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3d02be/3d02be.ot2.apiv2.py"

metadata = {
    'protocolName': 'Plate Aliquoting with CSV',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [csv_sample, mount, source_plate, dest_plate1,
        dest_plate2, dest_plate3,
        disp_height, asp_speed, disp_speed] = get_values(  # noqa: F821
        "csv_sample", "mount", "source_plate", "dest_plate1",
            "dest_plate2", "dest_plate3",
            "disp_height", "asp_speed", "disp_speed")

    # load labware
    source_plate = ctx.load_labware(source_plate, '1')
    dest_plate1 = ctx.load_labware(dest_plate1, '4')
    dest_plate2 = ctx.load_labware(dest_plate2, '7')
    dest_plate3 = ctx.load_labware(dest_plate3, '10')
    dest_plates = [dest_plate1, dest_plate2, dest_plate3]
    tiprack = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '3')]

    # load instrument
    p300 = ctx.load_instrument('p300_multi_gen2', mount, tip_racks=tiprack)
    p300.flow_rate.aspirate = asp_speed
    p300.flow_rate.dispense = disp_speed

    # csv file --> nested list
    transfer = [[val.strip().lower() for val in line.split(',')]
                for line in csv_sample.splitlines()
                if line.split(',')[0].strip()][1:]

    cols = [col for plate in dest_plates for col in plate.rows()[0]]
    destinations = [cols[i::12] for i in range(0, len(cols))][:12]

    airgap = 10
    for line, chunk in zip(transfer, destinations):
        p300.pick_up_tip()
        p300.aspirate(int(line[2]),
                      source_plate.rows()[0][int(line[0])-1].bottom(
                      z=int(line[1])))
        p300.air_gap(airgap)
        p300.touch_tip()
        for dest in chunk:
            p300.dispense(int(line[3])+airgap, dest.bottom(disp_height))
            p300.touch_tip()
            p300.air_gap(airgap)
        p300.air_gap(airgap)
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
    filename = f"detailed_action_json/3d02be.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)