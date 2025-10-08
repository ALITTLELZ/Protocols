import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/illumina-nextera-XT-library-prep-part4/nexteraXT_dna_library_prep_part4.ot2.apiv2.py"

metadata = {
    'protocolName': 'Illumina Nextera XT NGS Prep 4: Pool Libraries',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.2'
    }


def run(protocol):
    [pip_type, pip_mount, samps, pools, pool_vol] = get_values(  # noqa: F821
        'pip_type', 'pip_mount', 'samps', 'pools', 'pool_vol')

    total_tips = samps * pools
    total_tr = total_tips // 96 + (1 if total_tips % 96 > 0 else 0)
    tip_size = pip_type.split('_')[0][1:]
    tip_size = '300' if tip_size == '50' else tip_size
    tip_name = 'opentrons_96_tiprack_'+tip_size+'ul'
    tips = [protocol.load_labware(tip_name, str(slot))
            for slot in range(3, 3+total_tr)]

    in_plate = protocol.load_labware(
        'biorad_96_wellplate_200ul_pcr', '1', 'Load Plate'
    )
    tuberack = protocol.load_labware(
        'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap',
        '2',
        'Tube Rack with 2mL Tube(s)'
    )

    pip = protocol.load_instrument(pip_type, pip_mount, tip_racks=tips)

    if samps <= 24:
        input = [well for col in in_plate.columns()[:6]
                 for well in col[:4]][:samps]
    else:
        input = [well for well in in_plate.wells()][:samps]

    # Transfer each library to pooling tube(s)
    for tube in tuberack.wells()[:pools]:
        pip.transfer(pool_vol, input, tube, new_tip='always')

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
    filename = f"detailed_action_json/illumina-nextera-XT-library-prep-part4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)