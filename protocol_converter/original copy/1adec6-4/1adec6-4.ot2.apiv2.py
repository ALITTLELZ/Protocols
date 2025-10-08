import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1adec6-4/1adec6-4.ot2.apiv2.py"

metadata = {
    'protocolName': 'Transfer Small Molecules - CSV Input [4/7]',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(protocol):
    [pip, mnt20, mnt300, transferCSV] = get_values(  # noqa: F821
     'pip', 'mnt20', 'mnt300', 'transferCSV')

    # Load Labware
    tips = [
        protocol.load_labware(
            'opentrons_96_tiprack_20ul', s) for s in [4, 5, 7, 8, 10, 11]
            ]

    p20 = protocol.load_instrument(pip, mnt20, tip_racks=tips)

    tips300 = [protocol.load_labware('opentrons_96_tiprack_300ul', '3')]
    m300 = protocol.load_instrument(
        'p300_multi_gen2', mnt300, tip_racks=tips300)

    srcPlate = protocol.load_labware('thermofast_96_wellplate_200ul', '1')
    destPlate = protocol.load_labware('spl_96_wellplate_200ul_flat', '2')

    # Parse CSV; Each line should be --> Src Well, Vol, Dest Well
    data = [r.split(',') for r in transferCSV.strip().splitlines() if r][1:]

    # Make transfers based on CSV and create dest columns to mix
    destSet = set()
    for line in data:
        src, vol, dest = line
        p20.transfer(
            float(vol), srcPlate[src], destPlate[dest],
            mix_before=(3, 15))
        destSet.add(int(dest[1:]))

    destList = sorted(destSet)
    destList = [x-1 for x in destList]

    # mix cells in wells
    for i, col in enumerate(destList):
        dest = destPlate.rows()[0][col]
        m300.pick_up_tip()
        m300.mix(4, 200, dest)
        m300.drop_tip(tips300[0].rows()[0][i-1]) if i != 0 else m300.drop_tip()

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
    filename = f"detailed_action_json/1adec6-4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)