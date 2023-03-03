import json

files = ['001 (サイボーグの秘密).json', '002 (最初の一歩).json']

for file in files:
    file = f"translations/story/04/1026/{file}"
    new_file = open(file, 'r', encoding='utf-8')
    old_file = open(f"{file}.a", 'r', encoding='utf-8')

    new_data = json.load(new_file)
    old_data = json.load(old_file)

    new_file.close()
    old_file.close()

    for i in range(len(new_data['text'])):
        new_data['text'][i]['enName'] = old_data['text'][i]['enName']
        new_data['text'][i]['enText'] = old_data['text'][i]['enText']
        if 'choices' in old_data['text'][i]:
            new_data['text'][i]['choices'] = old_data['text'][i]['choices']
    
    new_file = open(file, 'w', encoding='utf-8')
    new_file.write(json.dumps(new_data, ensure_ascii=False, indent=4))
    new_file.close()