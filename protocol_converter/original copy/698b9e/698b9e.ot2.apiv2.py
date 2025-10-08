import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/698b9e/698b9e.ot2.apiv2.py"

metadata = {
    'protocolName': 'PCR Prep with 1.5 mL Tubes Part 1 - Plate Filling',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [num_plates, reagent, p20_mount,
        p300_mount] = get_values(  # noqa: F821
        "num_plates", "reagent", "p20_mount", "p300_mount")

    if not 1 <= num_plates <= 10:
        raise Exception("Enter a plate number 1-9")

    plate_slots = [str(num) for num in range(3, 3+num_plates)]

    if reagent == 'buffer':
        plate = 'nunc_96_wellplate_450ul'
        tips = 'opentrons_96_filtertiprack_200ul'
        pipette = 'p300_multi_gen2'
        mount = p300_mount
        reagent_vol = 80

    elif reagent == 'mastermix':
        plate = 'microamp_96_wellplate_100ul'
        tips = 'opentrons_96_filtertiprack_20ul'
        pipette = 'p20_single_gen2'
        mount = p20_mount
        reagent_vol = 7.6
        airgap = 3

    # load labware
    plates = [ctx.load_labware(plate, slot) for slot in plate_slots]
    tiprack = [ctx.load_labware(tips, '2')]
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', '1')

    # load instruments
    pip = ctx.load_instrument(pipette, mount, tip_racks=tiprack)

    # distribute mastermix
    if reagent == 'buffer':
        pip.pick_up_tip()
        for i, plate in enumerate(plates):
            for col in plate.rows()[0]:
                pip.aspirate(reagent_vol, reservoir.wells()[i])
                pip.dispense(reagent_vol, col)
                pip.blow_out()
                pip.touch_tip()
        pip.drop_tip()

    elif reagent == 'mastermix':
        wells = [well for plate in plates for well in plate.wells()]
        chunks = [wells[i:i+2] for i in range(0, len(wells), 2)]
        pip.pick_up_tip()
        for chunk in chunks:
            pip.aspirate(reagent_vol, reservoir.wells()[0])
            pip.air_gap(airgap)
            pip.aspirate(reagent_vol, reservoir.wells()[0])
            pip.touch_tip()
            for well in chunk:
                pip.dispense(reagent_vol+airgap, well)
                pip.touch_tip()
        pip.drop_tip()

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
    filename = f"detailed_action_json/698b9e.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)