import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/50486f-v2-part4/50486f-v2-part4.ot2.apiv2.py"

metadata = {
    'protocolName': 'APIv2 PCR Prep 4/4: PCR',
    'author': 'Chaz <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}


def run(protocol):
    [p20_mount, number_of_plates] = get_values(  # noqa: F821
        'p20_mount', 'number_of_plates')

    # load labware
    pcrcoolplate = 'labcon_96_wellplate_pcr_on_cooler'
    pcrcoolstrip = 'labcon_8strip_pcr_on_cooler'

    tempplate = protocol.load_labware(
        pcrcoolplate, '1', 'Labcon Plate on PCR Cooler')

    pcr_well = protocol.load_labware(
        pcrcoolstrip, '2', 'PCR Strip on PCR Cooler')

    primer_plate = protocol.load_labware(
                'biorad_96_wellplate_200ul_pcr', '4', 'primer plate (BioRad)')
    dna_plate = protocol.load_labware(
                'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '3',
                'DNA plate on Aluminum Block')
    tipracks = [
        protocol.load_labware(
            'opentrons_96_tiprack_20ul', slot) for slot in range(5, 12)
    ]

    # Check number of plates
    if number_of_plates > 6 or number_of_plates < 1:
        raise Exception('The number of plates should be between 1 and 6.')

    # create pipette

    pip20 = protocol.load_instrument(
        'p20_multi_gen2', p20_mount, tip_racks=tipracks)

    tip20_max = len(tipracks)*12
    tip20_count = 0

    def pick_up(pip):
        nonlocal tip20_count

        if tip20_count == tip20_max:
            protocol.pause(
                'Replace 20ul tipracks before resuming.')
            pip20.reset_tipracks()
            tip20_count = 0
        pip20.pick_up_tip()
        tip20_count += 1

    dest = tempplate.rows()[0]
    primers = primer_plate.rows()[0]
    samps = dna_plate.rows()[0]

    for i in range(number_of_plates):
        # step 1

        pick_up(pip20)

        for d in dest:
            pip20.transfer(8.7, pcr_well['A1'], d, new_tip='never')
            pip20.blow_out()

        pip20.drop_tip()

        # step 2

        for p, d in zip(primers, dest):
            pick_up(pip20)
            pip20.transfer(1.3, p, d, new_tip='never')
            pip20.blow_out()
            pip20.drop_tip()

        # step 3

        for s, d in zip(samps, dest):
            pick_up(pip20)
            pip20.transfer(5, s, d, new_tip='never')
            pip20.blow_out()
            pip20.drop_tip()

        if i == number_of_plates-1:
            protocol.comment("Congratulations, you have completed step 4/4  of this protocol. Please remove samples from OT-2 \
            and properly store.")
        else:
            protocol.pause("Congratulations, you have completed step 4/4  of this protocol for plate "+str(i+1)+". Please remove samples \
            from OT-2 and properly store. When you're ready to fill the  next plate, please load proper materials and click RESUME.")

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
    filename = f"detailed_action_json/50486f-v2-part4.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)