import json, os

files = [
    '00222e-dd.json','00222e-seed.json','07caf7.json','09cdbe.json','0f3b60.json',
    '26c304.json','29225e.json','5f791f.json','6a93a2-part3.json','6a93a2-part5.json',
    '6a93a2.json','9778eb.json','9778eb_spri.json','bpg-rna-extraction.json',
    'e54ada.json','ff5763_part2.json','ff5763_part5.json',
    'macherey-nagel-nucleomag-DNA-microbiome.json','macherey-nagel-nucleomag-dna-food.json',
    'macherey-nagel-nucleomag-pathogen.json','macherey-nagel-nucleomag-rna.json',
    'macherey-nagel-nucleomag-tissue.json','macherey-nagel-nucleomag-virus.json',
    'onsite-ganda-2.json','onsite-ganda-4.json','onsite_egenesis.json','sci-idt-xgen-mc.json'
]

for fn in files:
    with open(fn, encoding='utf-8') as f:
        data = json.load(f)
    print(f'=== {fn} ===')
    for i, action in enumerate(data.get('workflow', [])):
        args = action.get('action_args', {})
        vals = args.get('blow_out_air_volume', [])
        if any(v not in (0, None) for v in vals):
            src = args.get('sources', '')
            tgt = args.get('targets', '')
            print(f'  action[{i}]  src={src}  tgt={tgt}')
            print(f'    blow_out_air_volume = {vals}')
    print()
