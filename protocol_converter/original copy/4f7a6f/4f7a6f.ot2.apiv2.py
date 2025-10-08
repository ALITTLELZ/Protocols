import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/4f7a6f/4f7a6f.ot2.apiv2.py"

from opentrons.types import Point
from opentrons import protocol_api

metadata = {
    'protocolName': 'SuperScript III: qRT-PCR Prep with CSV File',
    'author': 'Rami Farawi <rami.farawi@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.11'
}


def run(ctx):

    [
     csv,
     init_vol_buff1,
     init_vol_buff2,
     init_vol_buff3,
     m300_mount] = get_values(  # noqa: F821
        "csv",
        "init_vol_buff1",
        "init_vol_buff2",
        "init_vol_buff3",
        "m300_mount")

    init_vol_buff1 *= 1000
    init_vol_buff2 *= 1000
    init_vol_buff3 *= 1000

    # load module
    temp_mod_dia = ctx.load_module('temperature module gen2', 10)
    temp_mod_buff = ctx.load_module('temperature module gen2', 7)
    dialysis_plate = temp_mod_dia.load_labware('htd_96_wellplate_200ul')
    cool_buff = temp_mod_buff.load_labware('nest_1_reservoir_195ml')
    temp_mod_dia.set_temperature(4)
    temp_mod_buff.set_temperature(4)

    # load labware
    buffer_reservoirs = [ctx.load_labware('nest_1_reservoir_195ml', slot)
                         for slot in [4, 5, 6]]
    waste_reservoirs = [ctx.load_labware('nest_1_reservoir_195ml', slot)
                        for slot in [8, 9, 11]]
    tips = [ctx.load_labware('opentrons_96_tiprack_300ul', slot)
            for slot in [1, 2, 3]]

    # load instrument
    m300 = ctx.load_instrument('p300_multi_gen2', m300_mount, tip_racks=tips)

    # mapping
    init_volume_var1 = init_vol_buff1  # - 5 as floor
    init_volume_var2 = init_vol_buff2
    init_volume_var3 = init_vol_buff3
    init_buffer_vols = {0: init_volume_var1,
                        1: init_volume_var2,
                        2: init_volume_var3}

    csv_rows = [[val.strip() for val in line.split(',')]
                for line in csv.splitlines()
                if line.split(',')[0].strip()][1:]

    waste_ctr = 0
    waste_vol = 0
    which_buff_res = 0

    for i, row in enumerate(csv_rows):
        num_samp = int(row[0])
        num_col = int(num_samp/8)

        transfer_vol = int(row[1])
        buffer_vol = int(row[2])
        incubation_time = int(row[6])

        ctx.comment('\n\nREMOVING WASTE TO RESERVOIR\n')
        m300.starting_tip = tips[0].wells_by_name()['A2']
        for col in dialysis_plate.rows()[0][:num_col]:
            try:
                m300.pick_up_tip()
            except protocol_api.labware.OutOfTipsError:
                ctx.pause("Replace all tip racks")
                m300.reset_tipracks()
                m300.starting_tip = tips[0].wells_by_name()['A2']
                m300.pick_up_tip()
            m300.aspirate(transfer_vol, col.bottom(z=1).move(
                          Point(y=-(col.diameter/2-2))))
            m300.dispense(transfer_vol, waste_reservoirs[waste_ctr].wells()[0])
            m300.blow_out()
            m300.drop_tip()
            waste_vol += transfer_vol/1000*8
            if waste_vol > 180:
                waste_ctr += 1
                waste_vol = 0
                if waste_ctr == 2:
                    ctx.pause("Empty waste reservoirs on slots 8, 9, and 11")

        ctx.comment('\n\nADDING BUFFER TO PLATE\n')
        m300.pick_up_tip(tips[0].wells_by_name()['A1'])

        for col in dialysis_plate.rows()[0][:num_col]:
            m300.aspirate(buffer_vol, waste_reservoirs[waste_ctr].wells()[0])
            m300.dispense(buffer_vol, col.top(z=0).move(
                          Point(y=-(col.diameter/2-2))))
            m300.blow_out()

        ctx.comment('\n\nREPLENISHING BUFFER TO TEMPERATURE MODULE\n')

        for _ in range(num_col):

            if buffer_vol/1000*8 > init_buffer_vols[2]-5 and which_buff_res == 2:  # noqa: E501

                ctx.pause(f"""Replenish buffer reservoirs in slots 4, 5, and 6
                              with initial volumes at the beginning
                              of the run. {init_vol_buff1}mL in slot 4,
                              {init_vol_buff2}mL in slot 5,
                              and {init_vol_buff3}mL in slot 6,
                                """)
                which_buff_res = 0
                init_buffer_vols[0] = init_vol_buff1
                init_buffer_vols[1] = init_vol_buff2
                init_buffer_vols[2] = init_vol_buff3

            m300.aspirate(buffer_vol,
                          buffer_reservoirs[which_buff_res].wells()[0])
            m300.dispense(buffer_vol, cool_buff.wells()[0].top())
            m300.blow_out()

            init_buffer_vols[which_buff_res] -= buffer_vol/1000*8
            if init_buffer_vols[which_buff_res] < 5 and which_buff_res != 2:
                which_buff_res += 1

        m300.return_tip()

        ctx.comment('\n')

        ctx.delay(minutes=incubation_time)

        ctx.comment('\n\n\n\n')

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
    filename = f"detailed_action_json/4f7a6f.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)