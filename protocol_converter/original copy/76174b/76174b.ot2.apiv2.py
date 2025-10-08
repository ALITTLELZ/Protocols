import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/76174b/76174b.ot2.apiv2.py"

from opentrons import types
from opentrons.protocol_api.labware import OutOfTipsError

metadata = {
    'protocolName': '''Perkin Elmer AlphaLISA''',
    'author': 'Steve Plonk <protocols@opentrons.com>',
    'apiLevel': '2.11'
}


def run(ctx):

    # get parameter values from json above
    [count_plates] = get_values(  # noqa: F821
      'count_plates')

    ctx.set_rail_lights(True)

    if not 1 <= count_plates <= 2:
        raise Exception('Count of 384-well plates must be 1 or 2.')

    # helper functions

    # notify user to replenish tips
    def pick_up_or_refill(self):
        try:
            self.pick_up_tip()
        except OutOfTipsError:
            self.move_to(ctx.loaded_labwares[4].wells()[0].top().move(
             types.Point(x=0, y=0, z=100)))
            ctx.pause(
             """Please Refill the {} Tip Boxes
                and Empty the Tip Waste.""".format(self))
            self.reset_tipracks()
            self.pick_up_tip()

    # yield list chunks of length n
    def create_chunks(list_name, n):
        for i in range(0, len(list_name), n):
            yield list_name[i:i+n]

    # tips, p20 multi
    tips20 = [ctx.load_labware(
     "opentrons_96_tiprack_20ul", str(slot)) for slot in [1, 4, 5, 7, 8, 9]]
    p20m = ctx.load_instrument(
        "p20_multi_gen2", 'left', tip_racks=tips20)

    optiplate = ctx.load_labware(
     'perkinelmer_384_wellplate_105ul', '2', 'OptiPlate')

    serialdilutions = ctx.load_labware(
     'corning_96_wellplate_320ul', '3', 'Sample Serial Dilutions')

    reagents = ctx.load_labware(
     'corning_96_wellplate_320ul', '6',
     'Anti-Ligand, Acceptor, Donor, Ligands')
    [antiligand, acceptor, donor] = [
     chunk for chunk in [*create_chunks(reagents.columns(), count_plates)][:3]]
    ligands = list(reversed(reagents.columns()))[:count_plates][::-1]

    for item, location in zip(
     ['receptors', 'samples', 'ligands', 'anti-ligand', 'acceptor', 'donor'],
     [optiplate, serialdilutions, ligands, antiligand, acceptor, donor]):
        ctx.comment("\nPlace {0} in {1}\n".format(item, location))

    ctx.comment("Transferring 8 uL Sample Serial Dilution to OptiPlate 1")
    for chunk_index in [0, 1]:
        for row in optiplate.rows()[:2]:

            for source, dest in zip(serialdilutions.rows()[0],
                                    [*create_chunks(row, 12)][chunk_index]):

                pick_up_or_refill(p20m)
                p20m.aspirate(8, source.bottom(1))
                p20m.dispense(8, dest.bottom(1))
                p20m.drop_tip()

    for rep in range(count_plates):

        if rep:
            ctx.pause("Place OptiPlate 2 in deck slot 2. Resume")

        ctx.comment("Transferring 4 uL Ligand to OptiPlate")
        for row in optiplate.rows()[:2]:
            for well in row:
                pick_up_or_refill(p20m)
                p20m.aspirate(4, ligands[rep][0].bottom(1))
                p20m.dispense(4, well.bottom(1))
                p20m.drop_tip()

        ctx.pause("Robot paused. Resume when ready.")

        ctx.comment("Transferring 4 uL anti-Ligand to OptiPlate")
        for row in optiplate.rows()[:2]:
            for well in row:
                pick_up_or_refill(p20m)
                p20m.aspirate(4, antiligand[rep][0].bottom(1))
                p20m.dispense(4, well.bottom(1))
                p20m.drop_tip()

        ctx.comment("Transferring 4 uL acceptor to OptiPlate")
        for row in optiplate.rows()[:2]:
            for well in row:
                pick_up_or_refill(p20m)
                p20m.aspirate(4, acceptor[rep][0].bottom(1))
                p20m.dispense(4, well.bottom(1))
                p20m.drop_tip()

        ctx.pause("Robot paused. Resume when ready.")

        ctx.comment("Transferring 4 uL donor to OptiPlate")
        for row in optiplate.rows()[:2]:
            for well in row:
                pick_up_or_refill(p20m)
                p20m.aspirate(4, donor[rep][0].bottom(1))
                p20m.dispense(4, well.bottom(1))
                p20m.drop_tip()

    ctx.comment(
     '''Process Complete.''')

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
    filename = f"detailed_action_json/76174b.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)