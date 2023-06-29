from bs4 import BeautifulSoup
import requests

f = open("ML_Glossary.html", "r", encoding="utf-8")

data = f.read()

soup = BeautifulSoup(data,"html.parser")


tags = soup.find_all("h2", {"class": "hide-from-toc"})

keywords = []
for tag in tags:
    tag = str(tag)

    quotation_position =[pos for pos, char in enumerate(tag) if char == "\""]

    # position of #data-text attribute
    start = quotation_position[2]
    end = quotation_position[3]

    keywords.append(tag[start+1:end].strip())

print(len(keywords))

file = open("Keyword_list.csv", "w")
for key in keywords:
    file.writelines(key + "\n")

    # manually label up to 145