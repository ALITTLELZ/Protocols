import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1adec6-5/1adec6-5.ot2.apiv2.py"

metadata = {
    'protocolName': 'Custom Supernatant Removal and PrestoBlue test [5/7]',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(protocol):
    [mnt300, cellHt, transfer2] = get_values(  # noqa: F821
     'mnt300', 'cellHt', 'transfer2')

    # load labware
    tips = [
        protocol.load_labware('opentrons_96_tiprack_300ul', '7')
        ]

    m300 = protocol.load_instrument('p300_multi_gen2', mnt300, tip_racks=tips)
    srcPlate = protocol.load_labware('spl_96_wellplate_200ul_flat', '1')
    destPlate = protocol.load_labware('spl_96_wellplate_200ul_flat', '4')
    if transfer2:
        destPlate2 = protocol.load_labware('spl_96_wellplate_200ul_flat', '5')
        dest2Wells = destPlate2.rows()[0][:10]
    rsvr = protocol.load_labware('nest_12_reservoir_15ml', '6')

    # Variables
    pbs = rsvr['A2']
    srcWells = srcPlate.rows()[0][:10]
    destWells = destPlate.rows()[0][:10]

    # Transfer 220uL supernatant from src to dest
    m300.flow_rate.aspirate = 30
    for idx, (src, dest) in enumerate(zip(srcWells, destWells)):
        m300.pick_up_tip()
        m300.transfer(
            220, src.bottom(cellHt), dest, air_gap=20, new_tip='never')
        if transfer2:
            m300.transfer(
                110, dest, dest2Wells[idx], air_gap=20, new_tip='never')
        m300.drop_tip()

    # Transfer 100uL PBS to src wells
    m300.flow_rate.aspirate = 50
    m300.pick_up_tip()
    for well in srcWells:
        m300.transfer(100, pbs, well.top(-2), air_gap=20, new_tip='never')
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
    filename = f"detailed_action_json/1adec6-5.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)