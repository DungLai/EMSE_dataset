# Start with repo-metadata.csv from Microsoft Paper, this script download json files of repo data and filter by applied AI category and python language

# Criteria to filter:
# 1. (Check by current date - 1 Jan 2023) Newness (the projects must be created in the last 5 years)
# 2. (Check by current date - 1 Jan 2023) Popularity (the projects must have at least 100 stars)
# 3. (Check by current date - 1 Jan 2023) Activeness (the projects must have at least a commit in the last 2 years)
# 4. (Check by the original csv file) Language (the projects must be written in python).
# 5. (Check by the original csv filee) Applied AI project only

import requests
import urllib.request
import json
import csv

def main():
	file = open("repo-metadata.csv", "r") # Load microsoft dataset
	rows = file.read().split("\n")
	headers = rows[0] # Header of original dataset
	data = [] # list of 1. applied AI project 2. written in python 3. Still exist and 4. other information: Star, last commit date and date of creation
	data.append(["Name","URL", "Created_at", "Star", "Last commit"]) # Header
	for row in rows[1:]:
		row = row.split(",")
		# Only save and process project that is writen in python and is applied AI projects
		if (row[0].lower().strip() == "applied") and (row[16].lower().strip() == "python"):
			owner = row[4]
			repo_name = row[3]
			url = "https://github.com/{}/{}".format(owner, repo_name)
			api_repo_info = "https://api.github.com/repos/{}/{}".format(owner, repo_name)

			token = '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'
			hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
			req = urllib.request.Request(api_repo_info, headers = hdr)
			
			try: # Check that the repo still exist 
				response = urllib.request.urlopen(req)
			except: 
				continue
			content = response.read()
			content = content.decode("utf-8")
			# Save api response to json file, this is the repository information
			with open("applied_AI_python_repo_info/{}*{}.json".format(owner,repo_name), "w") as output:
				output.write(content)
			repo_dict = json.loads(content)

			data.append([
				repo_dict["full_name"],
				repo_dict["html_url"],
				repo_dict["created_at"],
				repo_dict["stargazers_count"], # star count
				repo_dict["pushed_at"] #last commit date
				])

	file = open('1_applied_AI_python_dataset.csv','w+', newline='')
	with file:
		write = csv.writer(file)
		write.writerows(data)
	
main()