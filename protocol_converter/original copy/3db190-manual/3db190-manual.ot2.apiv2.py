import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/3db190-manual/3db190-manual.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR/qPCR prep - Manual',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(protocol):

    [total_samples, p20_mount, p1000_mount] = get_values(  # noqa: F821
        "total_samples", "p20_mount", "p1000_mount")

    total_samples = int(total_samples)

    # Load Tip Racks
    tipracks_20ul = [protocol.load_labware('opentrons_96_filtertiprack_20ul',
                                           slot) for slot in ['7']]
    tipracks_1000ul = [protocol.load_labware(
        'opentrons_96_filtertiprack_1000ul', slot) for slot in ['4']]

    # Load Plates
    # 1 mL Deepwell Microtiter Plate
    deepwell_plate = protocol.load_labware('eppendorf_96_deepwell_1000ul', 2)
    # PCR Plate resting on top of the thermal block
    pcr_plate = protocol.load_labware('enduraplate_96_wellplate_200ul', 3)

    # Load Instruments
    p20 = protocol.load_instrument('p20_single_gen2', p20_mount,
                                   tip_racks=tipracks_20ul)
    p1000 = protocol.load_instrument('p1000_single_gen2', p1000_mount,
                                     tip_racks=tipracks_1000ul)

    deep_samples = deepwell_plate.wells()[:total_samples]
    pcr_samples = pcr_plate.wells()[:total_samples]

    # Protocol Steps

    # Mix and Add 5 uL from Deep Well Block to PCR Plate
    # Mix 5x with P1000 set at 150 uL, (Uses new tip each time)
    # then transfer with P20 at 5 uL (Uses new tip each time)
    protocol.comment('Starting the mixing and transfer of specimen process...')
    for source, dest in zip(deep_samples, pcr_samples):
        p1000.pick_up_tip()
        p1000.mix(5, 150, source)
        p1000.drop_tip()
        p20.transfer(5, source,
                     dest, new_tip='always')

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
    filename = f"detailed_action_json/3db190-manual.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)