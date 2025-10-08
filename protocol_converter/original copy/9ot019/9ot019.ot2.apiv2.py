import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/9ot019/9ot019.ot2.apiv2.py"

# flake8: noqa
from opentrons import protocol_api
import math


def get_values(*names):
    import json
    _all_values = json.loads(
        """{"num_samples":5,
            "repeats_per_sample":3,
            "cryo_rack":"cryo_35_tuberack_1800ul",
            "sample_plate": "nest_96_wellplate_2ml_deep",
            "glycerol_plate": "opentrons_6_tuberack_falcon_50ml_conical",
            "pipette_type":"p1000_single_gen2",
            "pipette_mount":"right",
            "tip_type":"opentrons_96_tiprack_1000ul"
            }""")
    return [_all_values[n] for n in names]


metadata = {
    'apiLevel': '2.8',
    'protocolName': 'Glycerol Stock',
    'author': 'Tim Dobbs <tim@bioartbot.org>',
    'source': 'BioArtBot Project at LPI Paris',
    'description': """Adaptable protocol for making glycerol stocks"""
    }


def run(protocol: protocol_api.ProtocolContext):

    [num_of_samples, repeats_per_sample,
     cryo_rack, sample_plate, glycerol_plate,
     pipette_type, pipette_mount, tip_type] = get_values(
        'num_samples', 'repeats_per_sample',
        'cryo_rack', 'sample_plate', 'glycerol_plate', 
        'pipette_type', 'pipette_mount', 'tip_type')

    # a function that gets us the next available slot on the deck
    def slot_generator(available_slots):
        for slot in available_slots:
            yield slot
    available_slots = range(11, 0, -1)
    get_slot = slot_generator(available_slots)

    # a function that gets us the next available well on a plate
    # if the plate is full, the functions provisions another plate
    def well_generator(labware_type):
        while True:
            try:
                plate = protocol.load_labware(labware_type, next(get_slot))
            except StopIteration:
                    raise IndexError("""There aren't enough slots on the deck to run
                                        all of the samples you're attempting to run.
                                        Try doing it on two separate runs."""
                                    ) #Would prefer to raise StopIteration, but OT seems to be weird about handling it
            for well in plate.wells():
                yield well
    get_cryo_well = well_generator(cryo_rack)
    get_sample_well = well_generator(sample_plate)


    # load a tiprack and glycerol reservoir
    tipracks = list()
    for rack in range(math.ceil(num_of_samples / 95)):
        tipracks.append(protocol.load_labware(tip_type, next(get_slot)))
        
    protocol.comment('**CHECK BEFORE RUNNING**')
    protocol.comment('Ensure you have enough glycerol (500ul for each cryo tube)')
    glycerol_reservoir = protocol.load_labware(glycerol_plate, next(get_slot))

    # set the pipette we will be using
    pipette = protocol.load_instrument(
            pipette_type,
            mount=pipette_mount,
            tip_racks=tipracks
    )

    protocol.comment('Ensure you have matched the expected culture platemap:')
    source_list = list()
    for sample in range(num_of_samples):
        source_well = next(get_sample_well)
        source_list.append(source_well)
        protocol.comment(f'SAMPLE {sample + 1} -> {source_well}')

    well_mapping = {}
    for source in source_list:
        destination_list = []
        for repeat in range(repeats_per_sample):
            destination_list.append(next(get_cryo_well))
        well_mapping[source] = destination_list

    #load glycerol into all of the necessary tubes
    flat_well_list = [well for sublist in well_mapping.values() for well in sublist]
    pipette.distribute(source=glycerol_reservoir.wells("A1"),dest=flat_well_list,volume=500, disposal_volume=0)

    #load cultures into each appropriate tubes
    for source in well_mapping:
        pipette.distribute(source=source,dest=well_mapping[source],volume=500, disposal_volume=0)

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
    filename = f"detailed_action_json/9ot019.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)