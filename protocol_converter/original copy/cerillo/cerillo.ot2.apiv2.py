import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/cerillo/cerillo.ot2.apiv2.py"

metadata = {
    'protocolName': 'Cerillo Plate Reader Protocol',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.13'
}


def run(ctx):

    [csv_stock, csv_buff, dilute_stock, sol_vol,
        p300_mount, m300_mount] = get_values(  # noqa: F821
        "csv_stock", "csv_buff", "dilute_stock", "sol_vol",
            "p300_mount", "m300_mount")

#     csv_stock = """
# x,1,2,3,4,5,6,7,8,9,10,11,12
# A,x,20,20,20,20,20,20,20,20,20,20,20
# B,X,40,40,40,40,40,40,40,40,40,40,40
# C,x,29,29,29,29,29,29,29,29,29,29,29
# D,40,40,40,40,40,40,40,40,40,40,40,40
# E,29,29,29,29,29,29,29,29,29,29,29,29
# F,40,40,40,40,40,40,40,40,40,40,40,40
# G,29,29,29,29,29,29,29,29,29,29,29,29
# H,40,40,40,40,40,40,40,40,40,40,40,40
#     """
#
#     csv_buff = """
# x,1,2,3,4,5,6,7,8,9,10,11,12
# A,20,40,34,20,22,44,89,90,92,29,84,29
# B,74,29,49,72,49,32,89,29,88,44,22,40
# C,20,40,34,20,22,44,89,90,92,29,84,29
# D,74,29,49,72,49,32,89,29,88,44,22,40
# E,20,40,34,20,22,44,89,90,92,29,84,29
# F,74,29,49,72,49,32,89,29,88,44,22,40
# G,20,40,34,20,22,44,89,90,92,29,84,29
# H,74,29,49,72,49,32,89,29,88,44,22,40
#     """

    # labware
    reservoir = ctx.load_labware('nest_12_reservoir_15ml', 5)
    plate_reader = ctx.load_labware('cerillo_stratus_armadillo_flatbottom_200ul', 1)  # noqa: E501
    deepwell = ctx.load_labware('nest_96_wellplate_2ml_deep', 3)
    tips = [ctx.load_labware('opentrons_96_filtertiprack_200ul', slot)
            for slot in [7, 8, 9]]

    # pipettes
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)
    p300 = ctx.load_instrument('p300_single_gen2', p300_mount, tip_racks=tips)

    csv_lines_stock = [[val.strip() for val in line.split(',')][1:]
                       for line in csv_stock.splitlines()
                       if line.split(',')[0].strip()][1:]

    csv_lines_buff = [[val.strip() for val in line.split(',')][1:]
                      for line in csv_buff.splitlines()
                      if line.split(',')[0].strip()][1:]

    # mapping
    stock_solution = reservoir.wells()[0]
    buffer = reservoir.wells()[1]
    cells = reservoir.wells()[-1]

    if dilute_stock:

        # protocol
        ctx.comment('\n---------------ADDING BUFFER TO PLATE-------------\n\n')
        p300.pick_up_tip()
        for line, row in zip(csv_lines_buff, deepwell.rows()):
            for well_vol, well_name in zip(line, row):
                if well_vol.lower() == 'x':
                    continue
                well_vol = int(well_vol)
                dest_well = well_name
                p300.aspirate(well_vol, buffer)
                p300.dispense(well_vol, dest_well)
        p300.drop_tip()

        ctx.comment('\n---------------ADDING STOCK TO PLATE--------------\n\n')
        p300.pick_up_tip()
        for line, row in zip(csv_lines_stock, deepwell.rows()):
            for well_vol, well_name in zip(line, row):
                if well_vol.lower() == 'x':
                    continue
                well_vol = int(well_vol)
                dest_well = well_name
                p300.aspirate(well_vol, stock_solution)
                p300.dispense(well_vol, dest_well.top())
        p300.drop_tip()

        ctx.comment('\n-------------Mixing solution and stock------------\n\n')
        for s, d in zip(deepwell.rows()[0], plate_reader.rows()[0]):
            m300.pick_up_tip()
            m300.mix(5, 50, s)
            m300.aspirate(sol_vol, s)
            m300.dispense(sol_vol, d)
            m300.drop_tip()

    else:
        ctx.comment('\n-----------Transferring solution to reader-------\n\n')
        for s, d in zip(deepwell.rows()[0], plate_reader.rows()[0]):
            m300.pick_up_tip()
            m300.aspirate(sol_vol, s)
            m300.dispense(sol_vol, d)
            m300.drop_tip()

    ctx.comment('\n-------------Transferring cells to reader-------------\n\n')
    m300.pick_up_tip()
    m300.mix(20, 200, cells)
    for col in plate_reader.rows()[0]:
        m300.aspirate(180, cells)
        m300.dispense(180, col)
        m300.mix(3, 150, col)
    m300.drop_tip()

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
    filename = f"detailed_action_json/cerillo.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)