def convert_string_to_list(string):
		# Convert list string to list
		import re
		elements = re.findall(r'\d+', string)
		list_string = [int(x) for x in elements]
		return list_string

def main():
	data = [] #issue pr pairs
	data.append(["Project Name","Issue URL", "issue number", "Closed PR that mention", "title"]) # Header
	
	file = open("issue_pr.csv", "r")
	rows = file.read().split("\n")[1:]
	# check each issue
	for row in rows:
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		issue_url = row[1]
		issue_number = row[2]
		pr_list = row[3]

		print(pr_list)

		# Some title have comma in it, this will concatenate them
		title = ""
		for i in range(4,len(row)):
			title += row[i]

		pr_list = pr_list.split(" ")[:-1]
		for pr in pr_list:
			pr = pr.strip()

		import json
		closed_pulls = []
		for pull_number in pr_list:
			pull_json = json.load(open("pulls/{}*{}/{}.json".format(owner, repo, pull_number)))
			if pull_json["state"] == "closed" and pull_json["merged_at"] != None:
				closed_pulls.append(pull_number)

		# Check issue are closed
		issue_json = json.load(open("issues/{}*{}/issue/{}.json".format(owner, repo, issue_number)))
		if issue_json["state"] == "closed" and len(closed_pulls)!=0: 
			closed_pulls_string = ""
			for p in closed_pulls:
				closed_pulls_string += str(p) + " "
			data.append([name,issue_url,issue_number,closed_pulls_string[:-1],title])

	import csv
	file = open("issue_with_closed_pr.csv",'w', newline='')
	with file:
		write = csv.writer(file)
		write.writerows(data)

main()