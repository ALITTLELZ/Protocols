import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/0479ad-cp/normalization.ot2.apiv2.py"

from opentrons import protocol_api
from opentrons import types
from opentrons.protocol_api.labware import OutOfTipsError


metadata = {
    'protocolName': 'Normalization from plates with a single-channel pipette',
    'author': 'Andrew Sum',
    'source': 'Breakthrough Genomics',
    'apiLevel': '2.13'
}


def run(ctx: protocol_api.ProtocolContext):
    [volumes_csv,
     p300_mount,
     p20_mount,
     plate_type,
     res_type,
     filter_tip,
     tip_reuse] = get_values(  # noqa: F821
     "volumes_csv",
     "p300_mount",
     "p20_mount",
     "plate_type",
     "res_type",
     "filter_tip",
     "tip_reuse")

    ctx.set_rail_lights(True)

    # except statement to handle error during protocol analysis
    volumes_dna = [
        float(line.split(',')[1]) for line in volumes_csv.splitlines()[1:]
        if line and line.split(',')[0].strip()]
    volumes_water = [
        float(line.split(',')[2]) for line in volumes_csv.splitlines()[1:]
        if line and line.split(',')[0].strip()]
    num_samples = len(volumes_dna)

    # display date and volumes
    ctx.comment("Sample volumes: {}".format(volumes_dna))
    ctx.comment("Water volumes: {}".format(volumes_water))

    # create labware
    labware_tempmod = "thermofisher_96_well_pcrplate_200_aluminumblock"
    labware_tempmod2 = "thermofisher_96_well_pcrplate_200_aluminumblock"

    # Output plate
    temp = ctx.load_module('Temperature Module', '4')
    normalized_plate = temp.load_labware(
        labware_tempmod, 'Thermo PCR plate for normalized samples')
    temp.set_temperature(4)

    # Input sample plate
    temp2 = ctx.load_module('Temperature Module', '1')
    sample_plate = temp2.load_labware(
        labware_tempmod2,
        '{} samples in a Thermo PCR plate'.format(num_samples))
    temp.set_temperature(4)

    reservoir = ctx.load_labware(res_type, '2')
    water = reservoir.wells()[5]

    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '10')]
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '11')]

    p300 = ctx.load_instrument('p300_single_gen2', 'right', tip_racks=tips300)
    p20 = ctx.load_instrument('p20_single_gen2', 'left', tip_racks=tips20)

    # adjust pick_up_distance to prevent motor skipping during tip pickup
    pick_up_distance_p20 = 9
    ctx._hw_manager.hardware._attached_instruments[
        p20._implementation.get_mount()].update_config_item(
        'pick_up_distance', pick_up_distance_p20)

    pick_up_distance_p300 = 11
    ctx._hw_manager.hardware._attached_instruments[
        p300._implementation.get_mount()].update_config_item(
        'pick_up_distance', pick_up_distance_p300)

    def pick_up(pip):
        try:
            pip.pick_up_tip()
        except OutOfTipsError():
            ctx.pause("Please refill tip boxes")
            pip.reset_tipracks()
            pip.pick_up_tip()

    pick_up(p20)
    pick_up(p300)

    # Dispense appropriate volume of water into each well first to save tips
    for i, vol in enumerate(volumes_water):
        if vol != 0:
            if vol > 20:
                pipette = p300
            else:
                pipette = p20
            pipette.aspirate(vol, water.bottom(2))
            pipette.move_to(
                water.top(-2).move(types.Point(x=water.length / 2, y=0, z=0)))
            pipette.move_to(water.top())
            pipette.dispense(vol, normalized_plate.wells()[i])
            pipette.blow_out()
        else:
            pass

    p20.drop_tip()
    p300.drop_tip()

    # Transfer DNA from input plate to output plate
    for i, vol in enumerate(volumes_dna):
        pipette = p20 if vol <= 20 else p300
        pick_up(pipette)
        if vol > 20:
            loc = -0.2
        else:
            loc = 0.3
        pipette.aspirate(vol, sample_plate.wells()[i].bottom(loc), rate=0.8)
        pipette.dispense(vol, normalized_plate.wells()[i])
        pipette.blow_out()
        pipette.drop_tip()

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
    filename = f"detailed_action_json/0479ad-cp.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)