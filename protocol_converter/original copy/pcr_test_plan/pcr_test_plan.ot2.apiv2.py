import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/pcr_test_plan/pcr_test_plan.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Prep',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library',
    'apiLevel': '2.0'
    }


def run(protocol_context):
    [dna_volume, primer_volume, master_mix_volume] = get_values(  # noqa: F821
        'dna_volume', 'primer_volume', 'master_mix_volume')

    # labware setup
    total_volume = dna_volume + 2*primer_volume + master_mix_volume
    if total_volume != 25:
        raise Exception("Total reaction volume must be 25 uL.")

    tipracks_10ul = [protocol_context.load_labware(
        'opentrons_96_tiprack_10ul', slot) for slot in [1, 2]]
    tiprack_300ul = protocol_context.load_labware(
        'opentrons_96_tiprack_300ul', 3)

    rt_reagents = protocol_context.load_labware(
        'opentrons_24_tuberack_nest_1.5ml_snapcap', 6)

    thermocycler = protocol_context.load_module('thermocycler')
    reaction_plate = thermocycler.load_labware(
        'nest_96_wellplate_100ul_pcr_full_skirt')

    # open thermocycler lid and keep block temperature at 4°C
    thermocycler.open_lid()
    thermocycler.set_block_temperature(4)

    # instrument setup
    p10 = protocol_context.load_instrument('p10_single', 'left',
                                           tip_racks=tipracks_10ul)
    p50 = protocol_context.load_instrument('p50_single', 'right',
                                           tip_racks=[tiprack_300ul])

    # reagent setup
    master_mix = rt_reagents.wells()[0]
    primer_1 = rt_reagents.wells()[4]
    primer_2 = rt_reagents.wells()[5]

    # transfer master mix
    volume_in_tube = master_mix.max_volume
    for well in reaction_plate.wells():
        p50.pick_up_tip()
        if volume_in_tube < master_mix_volume:
            master_mix = master_mix
        p50.aspirate(master_mix_volume, master_mix)
        p50.dispense(master_mix_volume, well)
        p50.blow_out(well.top())
        p50.drop_tip()

    # transfer primer 1
    for well in reaction_plate.wells():
        p10.pick_up_tip()
        p10.aspirate(primer_volume, primer_1)
        p10.dispense(primer_volume, well)
        p10.blow_out(well.bottom(3))
        p10.drop_tip()

    # transfer primer 2
    for well in reaction_plate.wells():
        p10.pick_up_tip()
        p10.aspirate(primer_volume, primer_2)
        p10.dispense(primer_volume, well)
        p10.blow_out(well.bottom(3))
        p10.drop_tip()

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
    filename = f"detailed_action_json/pcr_test_plan.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)