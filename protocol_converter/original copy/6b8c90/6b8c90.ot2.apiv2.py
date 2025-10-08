import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6b8c90/6b8c90.ot2.apiv2.py"

metadata = {
    'protocolName': '48 MCT to 1mL Vial',
    'author': 'Chaz <chaz@opentrons.com>',
    'apiLevel': '2.9'
}


def run(protocol):
    [mnt300, num_samps] = get_values(  # noqa: F821
     'mnt300', 'num_samps')

    # load labware
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', '7')
    p300 = protocol.load_instrument('p300_single', mnt300, tip_racks=[tips])

    mct = [
        protocol.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap_acrylic',
            s) for s in ['2', '5']
            ]
    mctSamps = [well for plate in mct for well in plate.wells()][:num_samps]

    v1ml = [
        protocol.load_labware(
            'custom1mltesttube_24_wellplate_5000ul',
            s) for s in ['3', '6']
            ]

    vials = [well for plate in v1ml for well in plate.wells()][:num_samps]

    for src, dest in zip(mctSamps, vials):
        p300.pick_up_tip()
        p300.aspirate(300, src.bottom(10))
        p300.dispense(300, dest.bottom(20))
        p300.blow_out()
        p300.touch_tip(dest, v_offset=-2)
        p300.drop_tip()

    protocol.comment('Protocol complete!')

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
    filename = f"detailed_action_json/6b8c90.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)