Generic_TextFile = """
âââ 202104210943.txt
âââ 202104210944.txt
âââ 202104210945.txt
"""

Generic_ImageFile = """
âââ 202104210943.png
âââ 202104210944.png
âââ 202104210945.png
"""

Generic_AudioFile = """
âââ 202104210943.mp3
âââ 202104210944.mp3
âââ 202104210945.mp3
"""

Generic_TextLine = """
Terrible customer service.
Really great transaction.
Great price.
"""

Category_CSV = """
column_data,column_label
"Terrible customer service.","negative"
"Really great transaction.","positive"
"Great price.","positive"
"""

Category_fastText = """
__label__negative Terrible customer service.
__label__positive Really great transaction.
__label__positive Great price.
"""

Category_JSON = """
[
    {
        "column_data": "Terrible customer service.",
        "column_label": ["negative"]
    }
]
"""

Category_JSONL = """
{"column_data": "Terrible customer service.", "column_label": ["negative"]}
{"column_data": "Really great transaction.", "column_label": ["positive"]}
{"column_data": "Great price.", "column_label": ["positive"]}
"""

Text_CSV = """
column_data,column_label
"Hello!","ããã«ã¡ã¯ï¼"
"Good morning.","ãã¯ãããããã¾ãã"
"See you.","ããããªãã"
"""

Text_JSON = """
[
    {
        "column_data": "Hello!",
        "column_label": ["ããã«ã¡ã¯ï¼"]
    }
]
"""

Text_JSONL = """
{"column_data": "Hello!", "column_label": ["ããã«ã¡ã¯ï¼"]}
{"column_data": "Good morning.", "column_label": ["ãã¯ãããããã¾ãã"]}
{"column_data": "See you.", "column_label": ["ããããªãã"]}
"""

Offset_JSONL = """
{"column_data": "EU rejects German call to boycott British lamb.", "column_label": [ [0, 2, "ORG"], ... ]}
{"column_data": "Peter Blackburn", "column_label": [ [0, 15, "PERSON"] ]}
{"column_data": "President Obama", "column_label": [ [10, 15, "PERSON"] ]}
"""

Offset_CoNLL = """
EU  B-ORG
rejects O
German  B-MISC
call  O
to  O
boycott O
British B-MISC
lamb  O
. O

Peter B-PER
Blackburn I-PER
"""

IDSF_JSONL = """
{"text": "Find a flight from Memphis to Tacoma", "entities": [[0, 26, "City"], [30, 36, "City"]], "cats": ["flight"]}
{"text": "I want to know what airports are in Los Angeles", "entities": [[36, 47, "City"]], "cats": ["airport"]}
"""
