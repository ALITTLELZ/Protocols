import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/751127/cherrypicking.ot2.apiv2.py"

from opentrons.types import Point, Location

metadata = {
    'protocolName': 'Cherrypicking from Coordinates',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [transfer_csv] = get_values(  # noqa: F821
        "transfer_csv")

    tiprack20 = [ctx.load_labware('opentrons_96_tiprack_20ul', '3',
                                  '20µl tiprack')]
    pipettes = [ctx.load_instrument('p20_single_gen2', mount,
                                    tip_racks=tiprack20)
                for mount in ['right', 'left']]

    # load labware
    transfer_info = [[val.strip().lower() for val in line.split(',')[1:]]
                     for line in transfer_csv.splitlines()
                     if line.split(',')[0].strip()][1:]
    src_a = Location(Point(
        float(transfer_info[0][0]), float(transfer_info[0][1]),
        float(transfer_info[0][2])), None)
    src_b = Location(Point(
        float(transfer_info[1][0]), float(transfer_info[1][1]),
        float(transfer_info[1][2])), None)
    if False:

        for line in transfer_info[2:]:
            dest = Location(
                Point(float(line[0]), float(line[1]), float(line[2])), None)
            vol = float(line[3])
            [p.pick_up_tip() for p in pipettes]
            [pip.home() for pip in pipettes]
            for src, p in zip([src_a, src_b], pipettes):
                p.aspirate(vol, src)
                p.home()
                p.dispense(vol, dest)
                p.home()
            [p.drop_tip() for p in pipettes]

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
    filename = f"detailed_action_json/751127.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)