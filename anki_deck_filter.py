# Anki Deck Filter
# author: yaranawr
# repo: github.com/yaranawr/AnkiDeckFilter
# 
# Sometimes you like a deck, but you only want to study the first 200 core words or so.
# This script extracts those cards into a new deck, filtering based on a wordlist you provide.
# It's essentially the same deck, but with only the words of your choice 
# (assuming the words in your wordlist are in the provided deck).
#
# Requirements:
#   - Python3: https://www.python.org/downloads/
#   - Compatible with Windows and Linux
# Usage: 
#   - In powershell or any shell, enter:
#       python anki_deck_filter.py deck_that_should_be_filtered.apkg wordlist.txt "new apkg name of your choice"
#   - The script will prompt you to select the field you want to filter.
#       - The content in this field will be compared with the wordlist. If the content matches, then it will be included 
#         in the new deck
#

import sqlite3
import json
import zipfile
import re
import os
import sys

usage = "Usage: python anki_deck_filter.py <file.apkg> <wordlist.txt> <\"new apkg name\">"

if sys.argv[1] == "-h" or sys.argv[1] == "--help":
    print(usage)
    sys.exit(0)

if len(sys.argv) < 4:
    print("Error: Missing arguments.")
    print(usage)
    sys.exit(1)


apkg_path = sys.argv[1] 
wordlist = sys.argv[2]
new_apkg_name = sys.argv[3]

temp_folder = os.getenv("TEMP") or "/tmp"
unzip_folder = os.path.join(temp_folder, "apkg")

try:
    os.makedirs(unzip_folder, exist_ok=True)
except OSError as e:
    print(f"Erro: {e}")
    sys.exit(1)

collection_path = os.path.join(unzip_folder, "collection.anki2")
media_path = os.path.join(unzip_folder, "media")

try:
    with zipfile.ZipFile(apkg_path, 'r') as apkg_file:
        apkg_file.extractall(unzip_folder)
        print("Content extracted successfully")
except zipfile.BadZipFile:
    print("Failed to extract. The apkg file may be corrupted.")
    sys.exit(1)
except FileNotFoundError:
    print("Apkg file not found")
    sys.exit(1)
except Exception as e:
    print("Unexpected error while trying to extract the dpkg file:", {e})
    sys.exit(1)

conn = sqlite3.connect(collection_path)
cursor = conn.cursor()

cursor.execute("SELECT models FROM col")
models_json = cursor.fetchone()[0]
models_data = json.loads(models_json)

first_model_id, first_model_info = next(iter(models_data.items()))

print(f"Model Name: {first_model_info['name']}")
print("Fields:")
field_index = 1
for field in first_model_info['flds']:
    print(f"{field_index} - {field['name']}")
    field_index += 1

while True:
    field_to_filter = input("Enter the field number to filter: ") 
    if field_to_filter.isdigit():
        field_to_filter = int(field_to_filter) - 1
        if field_to_filter >= 0 and field_to_filter <= field_index:
            break
        else:
            print(f"Invalid input. Please enter a number between 1 and {field_index}")
    else:
        print(f"Invalid input. Please enter a number.")

print("Selected field:", first_model_info['flds'][field_to_filter]['name'])

cursor.execute("SELECT id, flds FROM notes WHERE mid = ?", (first_model_id,))
notes = cursor.fetchall()

filtered_note_id = []
filtered_files = []
filtered_files_in_folder = [] 

with open(media_path, 'r', encoding='utf-8') as media_file:
    media_data = json.load(media_file)

def process_file(fields, media_data, type, filtered_files, filtered_files_in_folder):
    if type == "image":
        file_pattern = r'<img src="[^"]+"'
        file_name_pattern = r'<img src=["\']([^"\']+)["\']'
    else:
        file_pattern = r'^\[?sound:'
        file_name_pattern = r'sound:([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)'

    files = [line for line in fields if re.search(file_pattern, line)]

    if files:
        filtered_file_names = []
        for file in files:
            file_match = re.search(file_name_pattern, file)
            filtered_file_names.append(file_match.group(1))
    
        for file_name in filtered_file_names:
            if file_name in media_data.values():
                for key, value in media_data.items():
                    if value == file_name:
                        filtered_files.append(file_name)
                        filtered_files_in_folder.append(key)

try:
    with open(wordlist, 'r', encoding='utf-8-sig') as wordlist_file:
        file_items = [line.strip() for line in wordlist_file]
except FileNotFoundError:
    print("File not found")
    sys.exit(1)

for note_id, note_fields in notes:
    fields = note_fields.split('\x1f') 

    if fields[field_to_filter] in file_items: 
        filtered_note_id.append(note_id) 
        process_file(fields, media_data, "image", filtered_files, filtered_files_in_folder)
        process_file(fields, media_data, "sound", filtered_files, filtered_files_in_folder)
             
if filtered_files_in_folder:
    filtered_files_in_folder_set = set(filtered_files_in_folder)

    for file in os.listdir(unzip_folder):
        file_path = os.path.join(unzip_folder, file)
        
        if file not in filtered_files_in_folder_set and file != "collection.anki2" and file != "media":
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except FileNotFoundError:
                print("File not found")
            except Exception as e:
                print("Unexpected error while trying to delete a file:", e)

    updated_media_data = {} 
    for file in filtered_files:
        updated_media_data.update({key: value for key, value in media_data.items() if value == file})

    with open(media_path, 'w', encoding='utf-7') as media_file:
        json.dump(updated_media_data, media_file)

if filtered_note_id:
    note_ids_placeholder = ",".join("?" for _ in filtered_note_id)
    cursor.execute(f"DELETE FROM notes WHERE id NOT IN ({note_ids_placeholder})", filtered_note_id)
    cursor.execute(f"DELETE FROM cards WHERE nid NOT IN ({note_ids_placeholder})", filtered_note_id)
    conn.commit()

cursor.execute("SELECT decks FROM col")
decks_data = cursor.fetchone()[0]
decks_json = json.loads(decks_data)

deck_to_rename = None

for deck_id, deck_info in decks_json.items():
    if deck_info['name'] != "Default":
        deck_to_rename = deck_id
        break

if deck_to_rename:
    original_name = decks_json[deck_to_rename]["name"]
    decks_json[deck_to_rename]["name"] = new_apkg_name

updated_decks_data = json.dumps(decks_json)
cursor.execute("UPDATE col SET decks = ? WHERE id = 1", (updated_decks_data,))
conn.commit()

with zipfile.ZipFile("./" + new_apkg_name + ".apkg", "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(unzip_folder):
        for file in files:
            file_path = os.path.join(root, file)
            zipf.write(file_path, os.path.relpath(file_path, unzip_folder))

cursor.close()
conn.close()
