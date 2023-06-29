def remove_duplicates(input_list):
    # Create an empty list to store unique elements
    unique_list = []
    
    # Iterate over the input list
    for item in input_list:
        # If the item is not already in the unique list, append it
        if item not in unique_list:
            unique_list.append(item)
    
    # Return the list of unique elements
    return unique_list	

def get_keywords():
	file = open("google_ml_glossary/Keyword_list.csv", "r", encoding="latin-1")
	data = file.read().split("\n")[1:]
	key_list = []
	for row in data:
		key_list.append(row.split(",")[1])

	key_list = remove_duplicates(key_list) 
	for i in range(len(key_list)):
		key_list[i] = key_list[i].lower()
		key_list[i].strip()
	while("" in key_list):
		key_list.remove("")	
	print(key_list)
	return key_list	

# file = open("issue_pr.csv", "r")
file = open("13_issue_contain_ML.csv", "r")
keys = get_keywords()
print(len(keys))
# header = file.read().split("\n")[0]
data = file.read().split("\n")[1:]
issue_with_keywords = [] # Contain at least 1 keywords from the list
for row in data:
	row = row.split(",")
	title = row[4]
	title_words = title.split(" ")
	for i in range(len(title_words)):
		title_words[i] = title_words[i].lower()
		title_words[i] = title_words[i].replace('.'," ")
		title_words[i] = title_words[i].replace(','," ")	
		title_words[i] = title_words[i].replace('"',"")	
		title_words[i] = title_words[i].replace("'","")	
		title_words[i] = title_words[i].replace("`","")	
		title_words[i] = title_words[i].replace("[","")	
		title_words[i] = title_words[i].replace("]","")	
		title_words[i] = title_words[i].replace("(","")	
		title_words[i] = title_words[i].replace(")","")	
		title_words[i] = title_words[i].replace(">"," ")	
		title_words[i] = title_words[i].replace("<"," ")	
		title_words[i] = title_words[i].replace("="," ")	
		title_words[i] = title_words[i].strip()	
		# Remove comma, stop 
	for key in keys:
		if key in title_words:
			issue_with_keywords.append(row)
			# print("Key: {}\n Found in {}".format(key,title))
			# print("")
			break

# print(len(data))
# print(len(issue_with_keywords))

import csv
file = open("14_issue_keyword_and_ML.csv",'w', newline='')

# with file:
# 	write = csv.writer(file)
# 	# write.writerow([header])
# 	write.writerows(issue_with_keywords)

