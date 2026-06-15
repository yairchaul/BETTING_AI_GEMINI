import chardet

def detect_and_remove_bom(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)

    with open(file_path, 'w', encoding=result['encoding']) as file:
        file.write(raw_data.decode(result['encoding']))

detect_and_remove_bom('C:\\Users\\Yair\\Desktop\\BETTING_AI\\main_vision_completo.py')
