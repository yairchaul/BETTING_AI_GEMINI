import sys

def remove_bom(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    with open(file_path, 'w', encoding='utf-8', newline='\n') as file:
        file.write(content)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python remove_bom.py <file_path>")
    else:
        file_path = sys.argv[1]
        remove_bom(file_path)
