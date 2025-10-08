import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/111210-part-10/111210-part-10.ot2.apiv2.py"

from opentrons import protocol_api, types

metadata = {
    'protocolName': '''GeneRead QIAact Lung RNA Fusion UMI Panel Kit:
                       Cleanup of Universal PCR with QIAseq Beads''',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [samples, p300_mount,
        p20_mount, engage_height] = get_values(  # noqa: F821
        "samples", "p300_mount", "p20_mount", "engage_height")

    if not 1 <= samples <= 12:
        raise Exception('''Invalid number of samples.
                        Sample number must be between 1-12.''')

    # Load Labware
    tipracks_200ul = ctx.load_labware('opentrons_96_filtertiprack_200ul', 9)
    tipracks_20ul = ctx.load_labware('opentrons_96_filtertiprack_20ul', 6)
    tc_mod = ctx.load_module('thermocycler module')
    tc_plate = tc_mod.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')
    mag_mod = ctx.load_module('magnetic module gen2', 1)
    mag_plate = mag_mod.load_labware('nest_96_wellplate_2ml_deep')
    temp_mod = ctx.load_module('temperature module gen2', 3)
    temp_plate = temp_mod.load_labware(
                    'opentrons_24_aluminumblock_nest_1.5ml_screwcap')
    pcr_tubes = ctx.load_labware(
                    'opentrons_96_aluminumblock_generic_pcr_strip_200ul',
                    2)
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 5)
    trash = ctx.loaded_labwares[12]['A1']

    # Load Pipettes
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount,
                               tip_racks=[tipracks_200ul])
    p20 = ctx.load_instrument('p20_single_gen2', p20_mount,
                              tip_racks=[tipracks_20ul])

    # Wells
    mag_plate_wells = mag_plate.wells()[:samples]
    tc_plate_wells = tc_plate.wells()[:samples]
    beads = temp_plate['A1']
    nfw = reservoir['A12']
    ethanol = reservoir['A1']

    # Helper Functions
    def pick_up(pip, loc=None):
        try:
            if loc:
                pip.pick_up_tip(loc)
            else:
                pip.pick_up_tip()
        except protocol_api.labware.OutOfTipsError:
            pip.home()
            pip.pause("Please replace the empty tip racks!")
            pip.reset_tipracks()
            pip.pick_up_tip()

    sides = [-1 + (((n // 8) % 2) * 1*2)
             for n in range(96)]

    def getWellSide(well, plate, custom_sides=None):
        index = plate.wells().index(well)
        if custom_sides:
            return custom_sides[index]
        return sides[index]

    def remove_supernatant(vol, src, dest, side, pip=p300, mode=None):
        if mode == 'elution':
            p300.flow_rate.aspirate = 10
        else:
            p300.flow_rate.aspirate = 30
            p300.flow_rate.dispense = 30
        while vol > 200:
            p300.aspirate(
                200, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
            p300.dispense(200, dest)
            p300.aspirate(10, dest)
            vol -= 200
        p300.aspirate(vol, src.bottom().move(types.Point(x=side, y=0, z=0.5)))
        p300.dispense(vol, dest)
        if mode == 'elution':
            p300.blow_out()
        if dest == trash:
            p300.blow_out()
        p300.flow_rate.aspirate = 50

    def reset_flow_rates():
        p300.flow_rate.aspirate = 46.43
        p300.flow_rate.dispense = 46.43

    def remove_residiual_supernatant():
        for well in mag_plate_wells:
            pick_up(p20)
            p20.aspirate(10, well.bottom().move(types.Point(
                        x=getWellSide(well, mag_plate), y=0, z=0.5)))
            p20.dispense(10, trash)
            p20.drop_tip()

    def etoh_wash(reps):
        for _ in range(reps):
            pick_up(p300)
            for well in mag_plate_wells:
                p300.aspirate(200, ethanol)
                p300.dispense(200, well.top(10))
            p300.drop_tip()

            ctx.delay(minutes=2, msg="Waiting for solution to clear.")

            for well in mag_plate_wells:
                pick_up(p300)
                remove_supernatant(200, well, trash, getWellSide(well,
                                                                 mag_plate))
                p300.drop_tip()

    # Protocol Steps

    # Transfer PCR Product to Magnetic Plate
    for src, dest in zip(tc_plate_wells, mag_plate_wells):
        pick_up(p300)
        p300.aspirate(20, src)
        p300.dispense(20, dest)
        p300.drop_tip()

    # Add 30 uL of Nuclease-free water
    pick_up(p300)
    for well in mag_plate_wells:
        p300.aspirate(30, nfw)
        p300.dispense(30, well.top(-5))
    p300.drop_tip()

    # Add 65 uL of Beads to Samples
    for well in mag_plate_wells:
        pick_up(p300)
        p300.aspirate(65, beads)
        p300.dispense(65, well)
        p300.mix(10, 55)
        p300.drop_tip()

    # Incubate at Room Temperature
    ctx.delay(minutes=5, msg="Incubating at Room Temperature")

    # Engage Magnetic Module
    mag_mod.engage(height=engage_height)
    ctx.delay(minutes=10, msg='Engaging Magnetic Module for 10 minutes.')

    # Remove Supernatant
    for well in mag_plate_wells:
        pick_up(p300)
        remove_supernatant(200, well, trash, getWellSide(well, mag_plate))
        p300.drop_tip()

    # Completely Remove Residual Supernatant
    remove_residiual_supernatant()

    # Ethanol Wash (2x)
    etoh_wash(2)

    # Centrifuge Samples
    mag_mod.disengage()
    ctx.pause('''Centrifuge the samples and replace the
                 plate on the magnetic module.''')

    # Engaging Magnet for 2 minutes
    mag_mod.engage(height=engage_height)
    ctx.delay(minutes=2, msg='Engaging Magnetic Module for 2 minutes.')

    # Completely Remove Residual Supernatant
    remove_residiual_supernatant()

    # Air Dry Beads for 10 minutes
    ctx.delay(minutes=10, msg='Air Drying Beads for 10 minutes.')
    mag_mod.disengage()

    # Add 30 uL of Nuclease-Free Water to Elute DNA
    for well in mag_plate_wells:
        pick_up(p300)
        p300.aspirate(30, nfw)
        p300.dispense(30, well.bottom(3))
        p300.mix(10, 20, well.bottom(1))
        p300.drop_tip()

    # Engaging Magnet for 5 minutes
    mag_mod.engage(height=engage_height)
    ctx.delay(minutes=5, msg='Engaging Magnetic Module for 5 minutes.')

    pcr_tube_wells = pcr_tubes.wells()[:samples]

    # Transfer Supernatant to PCR Tubes
    for src, dest in zip(mag_plate_wells, pcr_tube_wells):
        pick_up(p300)
        p300.aspirate(28, src.bottom().move(types.Point(
                        x=getWellSide(well, mag_plate), y=0, z=0.5)))
        p300.dispense(28, dest)
        p300.drop_tip()

    ctx.comment('Protocol Complete!')

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
    filename = f"detailed_action_json/111210-part-10.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)