import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/04eeb1/04eeb1.ot2.apiv2.py"

from opentrons import types

metadata = {
    'protocolName': 'Illumina COVIDSeq Test: Anneal RNA',
    'author': 'Sakib <sakib.hossain@opentrons.com>',
    'description': 'Custom Protocol Request',
    'apiLevel': '2.10'
}


def run(ctx):

    [m20_mount, reservoir_type, plate_1_cols,
        plate_2_cols, temperature] = get_values(  # noqa: F821
        "m20_mount", "reservoir_type", "plate_1_cols", "plate_2_cols",
        "temperature")

    # Labware
    tips200ul = ctx.load_labware('opentrons_96_filtertiprack_20ul', 10)
    temp_mod = ctx.load_module('temperature module gen2', 1)
    reservoir = temp_mod.load_labware(reservoir_type, "Master Mix Reservoir")
    plate_1 = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 11, "Plate 1")
    plate_2 = ctx.load_labware('biorad_96_wellplate_200ul_pcr', 8, "Plate 2")

    # Pipettes
    m20 = ctx.load_instrument('p20_multi_gen2', m20_mount,
                              tip_racks=[tips200ul])

    # Wells
    plate_1_wells = plate_1.rows()[0]
    plate_2_wells = plate_2.rows()[0]
    mm = reservoir['A1']

    # Helper Functions
    def includeCols(includedCols, plateCols):
        included_cols = []
        if includedCols != "":
            included_cols = [int(i)-1 for i in includedCols.split(",")]
            dests = [col for i, col in enumerate(plateCols) if i
                     in included_cols]
            return dests

    def distribute(pipette, vol, source, dest, disposal_vol, asp_height,
                   disp_height):

        use_vol = pipette.max_volume - disposal_vol
        num_distribute = use_vol // vol

        def well_lists(wells, n):
            for i in range(0, len(wells), n):
                yield wells[i:i + n]

        asp_vols = []

        def calc_vol(wells, vol):

            for wells in dest_wells:
                aspirate_vol = vol*len(wells) + disposal_vol
                asp_vols.append(aspirate_vol)

        dest_wells = list(well_lists(dest, int(num_distribute)))
        calc_vol(dest_wells, vol)

        # Aspirate from source
        pipette.pick_up_tip()
        for wells, asp_vol in zip(dest_wells, asp_vols):
            pipette.aspirate(asp_vol, source.bottom(z=asp_height))

            # Add Movement Path Code Here
            pipette.move_to(ctx.deck.position_for('4').move(types.Point(x=20,
                            z=50)))

            for well in wells:
                pipette.dispense(vol, well.bottom(z=disp_height))
            pipette.dispense(disposal_vol, source.bottom(z=asp_height))
        pipette.drop_tip()

    # Protocol Steps
    temp_mod.set_temperature(temperature)
    distribute(m20, 8.5, mm, includeCols(plate_1_cols, plate_1_wells), 3, 1, 1)
    if reservoir_type == 'biorad_96_wellplate_200ul_pcr':
        ctx.pause('''Please refill the master mix before continuing to Plate 2.
                Click Resume when ready.''')
    distribute(m20, 8.5, mm, includeCols(plate_2_cols, plate_2_wells), 3, 1, 1)

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
    filename = f"detailed_action_json/04eeb1.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)