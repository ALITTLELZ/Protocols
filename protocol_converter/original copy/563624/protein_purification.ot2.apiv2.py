import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/563624/protein_purification.ot2.apiv2.py"

metadata = {
    'protocolName': 'Phytip Protein Purification',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [m300_mount, deep_name, plate_name, start_column,
     end_column] = get_values(  # noqa: F821
        'm300_mount', 'deep_name', 'plate_name', 'start_column', 'end_column')

    # load labware
    tiprack = ctx.load_labware('phynexus_96_tiprack_300ul', '1',
                               '300ul resin tiprack')
    plate_labels = [
        'equilibration buffer', 'sample', 'wash buffer 1', 'wash buffer 2'
    ]
    mix_plates = [
        ctx.load_labware(deep_name, str(slot), name + ' plate')
        for slot, name in zip(range(2, 6), plate_labels)] + [
            ctx.load_labware('eppendorftwintec_96_wellplate_150ul', '6',
                             'elution buffer plate')
    ]

    # check
    if start_column < 1 or end_column > 12:
        raise Exception('Invalid columns must be between 1 and 12.')
    if start_column > end_column:
        raise Exception('Start column must be before end column')

    m300 = ctx.load_instrument(
        'p300_multi_gen2', m300_mount, tip_racks=[tiprack])
    m300.flow_rate.aspirate = 5
    m300.flow_rate.dispense = 5

    # mix sequences
    def plate_mix(cycles, volume, plate, col, delay=20, blow_out=False):
        mix_loc = plate.rows_by_name()['A'][col]
        for _ in range(cycles):
            m300.aspirate(volume, mix_loc)
            ctx.delay(seconds=delay)
            m300.dispense(volume, mix_loc)
            ctx.delay(seconds=delay)
            if blow_out:
                m300.blow_out(mix_loc.top(-2))

    for col in range(start_column-1, end_column):
        tip_loc = tiprack.rows_by_name()['A'][col]
        m300.pick_up_tip(tip_loc)

        # perform
        plate_mix(2, 90, mix_plates[0], col)
        plate_mix(4, 180, mix_plates[1], col, blow_out=True)
        plate_mix(2, 180, mix_plates[2], col)
        plate_mix(2, 180, mix_plates[3], col, blow_out=True)
        plate_mix(4, 70, mix_plates[4], col, blow_out=True)
        m300.return_tip()

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
    filename = f"detailed_action_json/563624.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)