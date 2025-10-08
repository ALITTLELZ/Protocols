import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/1adec6-3/1adec6-3.ot2.apiv2.py"

metadata = {
    'protocolName': 'Transfer Small Molecules [3/7]',
    'author': 'Chaz <chaz@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(protocol):
    [mnt20, numPlates, tVol, mixP300] = get_values(  # noqa: F821
     'mnt20', 'numPlates', 'tVol', 'mixP300')

    # load labware
    tips = [
        protocol.load_labware(
            'opentrons_96_tiprack_20ul', s) for s in [4, 7, 10]
            ]

    m20 = protocol.load_instrument('p20_multi_gen2', mnt20, tip_racks=tips)

    srcPlate = protocol.load_labware('thermofast_96_wellplate_200ul', '6')
    finalPlates = [
        protocol.load_labware(
            'spl_96_wellplate_200ul_flat', s) for s in [1, 2, 3]
        ][:numPlates]

    if mixP300:
        tips300 = [
            protocol.load_labware(
                'opentrons_96_tiprack_300ul', s) for s in [5, 8, 11]
                ]
        mnt300 = 'left' if mnt20 == 'right' else 'right'
        m300 = protocol.load_instrument(
            'p300_multi_gen2', mnt300, tip_racks=tips300)

    for plate in finalPlates:
        for src, dest in zip(srcPlate.rows()[0][:10], plate.rows()[0][:10]):
            m20.transfer(tVol, src, dest, mix_before=(5, 10))
        if mixP300:
            for dest in plate.rows()[0][:10]:
                m300.pick_up_tip()
                m300.mix(3, 200, dest)
                m300.drop_tip()
        protocol.pause('Please empty waste bin with used tips.')

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
    filename = f"detailed_action_json/1adec6-3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)