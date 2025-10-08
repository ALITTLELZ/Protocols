import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/211fe1/mass_spec_sample_prep.ot2.apiv2.py"

metadata = {
    'protocolName': 'Mass Spec Sample Prep',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.0'
    }


def run(ctx):
    [samples_csv, p50_mount,
        incubation_temperature] = get_values(  # noqa: F821
            'samples_csv', 'p50_mount', 'incubation_temperature'
        )

    tc = ctx.load_module('thermocycler')
    tc_plate = tc.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    tuberack = ctx.load_labware(
        'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
        '1',
        'reagent tuberack'
    )
    tipracks = [
        ctx.load_labware('opentrons_96_tiprack_300ul', slot, '300ul tiprack')
        for slot in ['2', '3', '5']
    ]

    # sample and reagent setup
    sample_names = [
        well.strip().upper()
        for well in samples_csv.splitlines()[0].split(',')
        if well

    ]
    samples = [
        tc_plate.wells_by_name()[well]
        for well in sample_names
        if well in tc_plate.wells_by_name()
    ]
    enzyme = tuberack.wells()[0]
    reagents = [tuberack.wells()[i] for i in [1, 2]]

    # pipettes
    p50 = ctx.load_instrument(
        'p50_single', p50_mount, tip_racks=tipracks)

    # transfer enzyme
    for s in samples:
        p50.pick_up_tip()
        p50.transfer(
            10, enzyme, s.bottom(2), mix_after=(3, 7), new_tip='never')
        p50.blow_out(s.top(-2))
        p50.drop_tip()

    tc.set_block_temperature(incubation_temperature)
    tc.set_lid_temperature(incubation_temperature)
    tc.close_lid()
    ctx.delay(minutes=60)
    tc.open_lid()

    # transfer reagents
    for i, r in enumerate(reagents):
        for s in samples:
            p50.pick_up_tip()
            p50.transfer(
                5, r, s.bottom(2), mix_after=(3, 7), new_tip='never')
            p50.blow_out(s.top(-2))
            p50.drop_tip()

        if i == 0:
            tc.close_lid()
            ctx.delay(minutes=30)
            tc.open_lid()

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
    filename = f"detailed_action_json/211fe1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)