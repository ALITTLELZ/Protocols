import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/testdrive/test_drive.ot2.apiv2.py"

from opentrons.types import Point

metadata = {
    'protocolName': 'OT-2 Guided Walk-through',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.7'
}


def run(ctx):

    [well_plate, pipette, tips, pipette_mount] = get_values(  # noqa: F821
        "well_plate", "pipette", "tips", "pipette_mount")

    # load labware
    plate = ctx.load_labware(well_plate, '1')
    tiprack = ctx.load_labware(tips, '2')

    # load instrument
    pip = ctx.load_instrument(pipette, pipette_mount, tip_racks=[tiprack])

    # protocol
    test_well = plate.wells()[0]

    pip.pick_up_tip()
    ctx.pause('''Welcome to the OT-2 Test Drive Protocol-
                    This is the `Pause` function.
                    Pauses can be put at any point during a protocol
                    to replace plates, reagents, spin down plates,
                    or for any other instance where human intervention
                    is needed. Protocols continue after a `Pause` when
                    the `Resume` button is selected. Select `Resume`
                    to see more OT-2 features.''')

    ctx.pause('''Pipettes can move almost anywhere within the OT-2-
                   Select `Resume` to see the pipette aspirate liquid
                   from the side of the well, and dispense at the top of the
                   well.''')

    if well_plate == 'corning_384_wellplate_112ul_flat':
        dimension = int(test_well.length)/2

    elif well_plate == 'nest_96_wellplate_2ml_deep':
        dimension = int(test_well.length)/2

    elif well_plate == 'usascientific_96_wellplate_2.4ml_deep':
        dimension = int(test_well.length)/2

    else:
        dimension = int(test_well.diameter)/2

    well_vol = test_well.geometry.max_volume
    vol = well_vol/1.5 if well_vol < pip.max_volume else pip.max_volume/1.5

    pip.move_to(plate['A1'].top())
    pip.aspirate(vol, test_well.bottom().move(
             Point(x=(dimension-1.1))))
    pip.dispense(vol, test_well.top())
    pip.aspirate(vol, test_well.bottom().move(
             Point(x=((dimension-1.1)*-1))))
    pip.dispense(vol, test_well.top())

    ctx.pause('''Now we will mix 3 times at the default flow rate.''')
    pip.mix(3, vol, test_well)

    ctx.pause('''Now, let's change the flow rate of the pipette to 1/2.''')
    pip.flow_rate.aspirate = 0.5*pip.flow_rate.aspirate
    pip.flow_rate.dispense = 0.5*pip.flow_rate.dispense
    for _ in range(2):
        pip.aspirate(vol, test_well)
        pip.dispense(vol, test_well.top())

    ctx.pause('''Doubling the flow rate of the pipette.''')
    pip.flow_rate.aspirate = 4*pip.flow_rate.aspirate
    pip.flow_rate.dispense = 4*pip.flow_rate.dispense
    for _ in range(2):
        pip.aspirate(vol, test_well)
        pip.dispense(vol, test_well.top())

    ctx.pause('''The touch tip functon can be called after aspirating
                   or dispensing. Touch tip is to move the pipette’s currently
                   attached tip to four opposite edges of a well, to knock off
                   any droplets that might be hanging from the tip.
                   Select `Resume` to see touch tip.''')

    for _ in range(2):
        pip.aspirate(vol, test_well)
        pip.touch_tip()
        pip.dispense(vol, test_well.top())

    ctx.pause('''The blow out function can be called after dispensing liquid.
                   To blow out is to push an extra amount of air through the
                   pipette’s tip, to make sure that any remaining droplets are
                   expelled. Select `Resume` to see blow out.''')

    for _ in range(2):
        pip.aspirate(vol, test_well)
        pip.dispense(vol, test_well.top())
        pip.blow_out()

    ctx.pause('''Now lets change the blow out flow rate, and blow out in the
                   trash on Slot 12. ''')

    pip.flow_rate.blow_out = 0.5*pip.flow_rate.blow_out
    pip.transfer(vol, plate.wells()[0], plate.wells()[16], blow_out=True,
                 lowout_location='trash', new_tip='never')
    pip.flow_rate.blow_out = 2*pip.flow_rate.blow_out

    ctx.pause('''Now let's drop a tip in the trash and pick up a new tip.''')
    pip.drop_tip()
    pip.pick_up_tip()
    pip.move_to(plate['A1'].top())

    ctx.pause('''The airgap function can be called after aspirating -
                 When dealing with certain liquids, you may need to aspirate
                 air after aspirating the liquid to prevent it from sliding out
                of the pipette’s tip. We will use the delay function to
                pause for 5 seconds after air-gapping. Delays are similar to
                pauses except for there is no `Resume` button that has to be
                selected by the user. Delays are especially useful for
                incubation periods, or after aspirating viscous liquid
                to achieve full volume.''')
    airgap = pip.max_volume/3
    for _ in range(3):
        pip.aspirate(vol/3, test_well)
        pip.air_gap(airgap)
        ctx.delay(seconds=5)
        pip.dispense(vol/2+airgap, test_well.top())

    ctx.pause('We can even airgap within the same tip')

    airgap = pip.max_volume/8
    for _ in range(2):
        pip.aspirate(vol/8, plate.wells()[0])
        pip.air_gap(airgap)
    ctx.delay(seconds=5)
    pip.blow_out()
    ctx.pause('''Now let's return the tip for later on in the protocol,''')
    pip.return_tip()
    pip.pick_up_tip()

    ctx.pause('''Now we can consolidate and distribute.
                 Volumes going to the same destination well are combined
                 within the same tip, so that multiple aspirates can be
                 combined to a single dispense (consolidation).
                 For the distribute function, volumes from the same source well
                 are combined within the same tip, so that one aspirate can
                 provide for multiple dispenses. Click `Resume` to see
                 a consolidate function call followed by a distribute''')

    pip.consolidate(vol/8,
                    plate.wells()[0:8], plate.wells()[8], new_tip='never')

    pip.drop_tip()
    ctx.pause('''Before we distribute, let's use our parked tip from before''')
    pip.pick_up_tip(tiprack.wells()[1])
    pip.distribute(vol/8,
                   plate.wells()[8], plate.wells()[0:8], new_tip='never')
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
    filename = f"detailed_action_json/testdrive.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)