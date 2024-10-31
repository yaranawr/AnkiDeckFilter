# Anki Deck Filter

## Description

Sometimes you like a deck, but you only want to study the first 200 core words or so. This script extracts those cards into a new deck, filtering based on a wordlist you provide. It's essentially the same deck, but with only the words of your choice (assuming the words in your wordlist are in the provided deck). 

## Requirements

* Python 3
* Compatible with Windows, Linux, and probably Mac

## Usage

In PowerShell or any shell, run:

```bash
python anki_deck_filter.py deck_that_should_be_filtered.apkg wordlist.txt "new apkg name of your choice"
```

The script will prompt you to select the field you want to filter. The content in this field will be compared with the wordlist. If the content matches, it will be included in the new deck.