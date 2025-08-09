# Load Collection parameters from JSON and create collection.
import json

with open("collection-properties/barbie_collection.json", "r") as file:
    schema = json.load(file)

    print(schema)
    print(schema["class"])
