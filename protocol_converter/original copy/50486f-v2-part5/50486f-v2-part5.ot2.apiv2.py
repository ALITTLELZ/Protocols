import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/50486f-v2-part5/50486f-v2-part5.ot2.apiv2.py"

metadata = {
    'protocolName': 'APIv2 PCR Prep: POOL',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [p20_mount, tip_strategy] = get_values(  # noqa: F821
        'p20_mount', 'tip_strategy')

    ctp = 'custom_pcr_plate_for_tempdeck'

    pcr_plates = [
        protocol.load_labware(
            ctp, str(slot), 'PCR product Plate') for slot in range(2, 6)]
    pcr_well = protocol.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
        '1', 'chilled aluminum block w/ PCR strip')
    tipracks = [
        protocol.load_labware(
            'opentrons_96_tiprack_20ul', str(slot)) for slot in range(6, 11)]

    pip20 = protocol.load_instrument(
        'p20_multi_gen2', p20_mount, tip_racks=tipracks)

    tip20_max = len(tipracks)*12
    tip20_count = 0

    def pick_up(pip):
        nonlocal tip20_count

        if tip20_count == tip20_max:
            protocol.pause(
                'Replace 20ul tipracks before resuming.')
            pip20.reset_tipracks()
            tip20_count = 0
        pip20.pick_up_tip()
        tip20_count += 1

    dest = pcr_well['A1']

    # transfer 2ul of sample to 8-well PCR strip
    if tip_strategy == 'different tip':
        for plate in pcr_plates:
            for col in plate.rows()[0]:
                pick_up(pip20)
                pip20.transfer(2, col, dest, new_tip='never')
                pip20.blow_out()
                pip20.drop_tip()
    else:
        pick_up(pip20)
        for plate in pcr_plates:
            for col in plate.rows()[0]:
                pip20.transfer(2, col, dest, new_tip='never')
                pip20.blow_out()
        pip20.drop_tip()

    protocol.comment("Pooling protocol now complete.")

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
    filename = f"detailed_action_json/50486f-v2-part5.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)