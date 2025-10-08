import builtins
builtins.event_logs = []
__protocol_file__ = r"/Users/guangxinzhang/Documents/Deep_Potential/published_protocol/Protocols/protocol_converter/original copy/33y0f3/33y0f3.ot2.apiv2.py"

# flake8: noqa

metadata = {
    'protocolName': 'Bacterial Plating and Dilution',
    'author': 'Lachlan <lajamu@biosustain.dtu.dk',
    'apiLevel': '2.2'
}

def run(protocol):

	#Load Tips1
    tips20= [protocol.load_labware('opentrons_96_tiprack_20ul', '9')]


    p20Multi = protocol.load_instrument("p20_multi_gen2", "left", tip_racks=tips20)
  


    plate_type = "corning_96_wellplate_360ul_flat"
    locs = [4, 5, 6, 10, 11]

    dilutionPlates = [protocol.load_labware(plate_type, slot, label="Dilution Plates")
    				for slot in locs]

    agar_plate_type = "biorad_96_wellplate_200ul_pcr" #can be any 96 that isn't the same as dil plate
    agar_locs = [1, 2, 3, 7, 8]
    agar_plates = [protocol.load_labware(agar_plate_type, slot, label="Agar")
    				for slot in agar_locs]

        
    def spot(dest, spot_vol):
        """Takes a diluted transformed culture and spots the defined volume onto agar 
        in a Nunc omnitray"""

        SAFE_HEIGHT = 15  
        spotting_dispense_rate=0.025 
        p20Multi.move_to(dest.top(SAFE_HEIGHT))
        protocol.max_speeds["Z"] = 50
        p20Multi.move_to(dest.top(2))
        p20Multi.dispense(volume=spot_vol, rate=spotting_dispense_rate)
        p20Multi.move_to(dest.top(0))
        del protocol.max_speeds["Z"]
    
    def spot_then_dilute(sourceCol, agar_dest, destcol, spot_vol):
        p20Multi.aspirate(spot_vol, sourceCol)
        spot(agar_dest, spot_vol)
        p20Multi.transfer(10, sourceCol, destcol, mix_after=(5, 20), new_tip="never")
        
    
    def spot_dilute_plate(plate, agar, spot_vol):
        p20Multi.pick_up_tip()
        for col in range(1, 10):
            w = "A"+str(col)
            x = "A" + str(col+1)
            spot_then_dilute(plate[w], agar[w], 
                             plate[x], spot_vol)
            #Spot final dilution THIS S THE PROBLEM, DOUBLE UP WITH LINE 52-55
            p20Multi.aspirate(spot_vol, plate[x])
            spot(agar[x], spot_vol)
        p20Multi.drop_tip()
        
    for pl, ag in zip(dilutionPlates, agar_plates):
        spot_dilute_plate(pl, ag, 5)
        
    protocol.comment("Run Complete!")

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
    filename = f"detailed_action_json/33y0f3.json"
    output_data = {
        "event_logs": builtins.event_logs,
        "liquid_locations": liquid_locations
    }

    with open(filename, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
        
        


    
