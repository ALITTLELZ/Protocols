import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/21u968/21u968.ot2.apiv2.py"

# flake8: noqa

def get_values(*names):
    import json
    _all_values = json.loads("""{"p300_mount":"left","tip_type":"opentrons_96_tiprack_300ul","plate_type":"biorad_96_wellplate_200ul_pcr"}""")
    return [_all_values[n] for n in names]


metadata = {
    'protocolName': 'PCR master mix distribution',
    'author': 'Iva <iva.h.pitelkova@uit.no>',
    'description': 'This protocols distributes 32 microL of PCR master mix in each well of 96-well plate.',
    'apiLevel': '2.9'
   
}


def run(protocol):

    [p300_mount, tip_type, plate_type] = get_values(  # noqa: F821
        "p300_mount", "tip_type", "plate_type")

    # Load Labware
    tiprack = protocol.load_labware(tip_type, 7)
    plate = protocol.load_labware(plate_type, 9)
    reservoir = protocol.load_labware(
            'opentrons_6_tuberack_falcon_50ml_conical', 8)
   

    # Load Pipette
    p300 = protocol.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tiprack])

    # Solutions
    MasterMix = reservoir['A1']
   

    # Wells to dispense MasterMix
    master_mix = [well for well in plate.wells()]
   
    # Distribute MasterMix solution to wells
    p300.distribute(32, MasterMix, master_mix, disposal_vol=0, blow_out=True)

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
    filename = f"detailed_action_json/21u968.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
  