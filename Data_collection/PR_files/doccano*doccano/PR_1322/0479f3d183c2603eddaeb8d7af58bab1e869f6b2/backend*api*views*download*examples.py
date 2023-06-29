Category_CSV = """
text,label
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
        "text": "Terrible customer service.",
        "label": ["negative"]
    }
]
"""

Category_JSONL = """
{"text": "Terrible customer service.", "label": ["negative"]}
{"text": "Really great transaction.", "label": ["positive"]}
{"text": "Great price.", "label": ["positive"]}
"""

Text_CSV = """
text,label
"Hello!","ããã«ã¡ã¯ï¼"
"Good morning.","ãã¯ãããããã¾ãã"
"See you.","ããããªãã"
"""

Text_JSON = """
[
    {
        "text": "Hello!",
        "label": ["ããã«ã¡ã¯ï¼"]
    }
]
"""

Text_JSONL = """
{"text": "Hello!", "label": ["ããã«ã¡ã¯ï¼"]}
{"text": "Good morning.", "label": ["ãã¯ãããããã¾ãã"]}
{"text": "See you.", "label": ["ããããªãã"]}
"""

Offset_JSONL = """
{"text": "EU rejects German call to boycott British lamb.", "label": [ [0, 2, "ORG"], [11, 17, "MISC"], ... ]}
{"text": "Peter Blackburn", "label": [ [0, 15, "PERSON"] ]}
{"text": "President Obama", "label": [ [10, 15, "PERSON"] ]}
"""
