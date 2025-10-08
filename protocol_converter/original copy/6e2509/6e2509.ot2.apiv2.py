import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/6e2509/6e2509.ot2.apiv2.py"

import math

metadata = {
    'protocolName': 'Sample Plate Filling 96 Wells to 384 Well Plate',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.9'
}


def run(ctx):

    [m20_mount, samples, pcr_mix_vol, sample_vol, sample_asp_height,
        sample_disp_height, mm_asp_height,
        mm_disp_height] = get_values(  # noqa: F821
        "m20_mount", "samples", "pcr_mix_vol", "sample_vol",
        "sample_asp_height", "sample_disp_height", "mm_asp_height",
        "mm_disp_height")

    # Load Labware
    tipracks_20ul = [ctx.load_labware('opentrons_96_filtertiprack_20ul',
                                      slot) for slot in [7, 8, 10, 11, 9]]
    pcr_mix = ctx.load_labware('thermofisherscientific_96_wellplate_450ul', 6,
                               'PCR Mix Reservoir')['A1']
    pcr_plate = ctx.load_labware(
        'appliedbiosystems_microamp_optical_384_wellplate_30ul', 3,
        '384 Well PCR Plate')
    elution_plates = [ctx.load_labware('molgen_96_well_elution_plate',
                                       slot, f'Elution Plate {i}') for i,
                      slot in enumerate([1, 2, 4, 5], 1)]

    # Load Pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=tipracks_20ul)

    # Get columns
    columns = math.ceil(samples / 8)

    # Get sample and dest wells in correct order
    sample_wells = [well for i in range(4) for well in
                    elution_plates[i].rows()[0]][:columns]
    pcr_dests = [a for b in zip(pcr_plate.rows()[0],
                 pcr_plate.rows()[1]) for a in b][:columns]

    # Add RT-PCR Mix use spare tip rack
    m20.pick_up_tip(tipracks_20ul[-1]['A1'])
    for dest in pcr_dests:
        m20.transfer(pcr_mix_vol, pcr_mix.bottom(mm_asp_height),
                     dest.bottom(mm_disp_height),
                     new_tip='never')
    m20.drop_tip()

    # Add RNA Samples
    for source, dest in zip(sample_wells, pcr_dests):
        m20.transfer(sample_vol, source.bottom(sample_asp_height),
                     dest.bottom(sample_disp_height), new_tip='always',
                     mix_after=(5, 5))

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
    filename = f"detailed_action_json/6e2509.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)