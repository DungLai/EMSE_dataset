# Start with repo-metadata.csv from Microsoft Paper

# Criteria to filter:

# (Check by the original csv file) Language (the projects must be written in python).
# (Check by the original csv filee) Applied AI project only

import os
import io
import json
import csv

path_to_jsons = "applied_AI_python_repo_info"

def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f

def main():
	data = [] # list of 1. applied AI project 2. written in python 3. Still exist and 4. other information: Star, last commit date and date of creation
	data.append(["Name","URL", "Created_at", "Star", "Last commit"]) # Header
	
	files = listdir_nohidden(path_to_jsons)

	for json_file in files:
		print(json_file)

		with open("applied_AI_python_repo_info/{}".format(json_file), "r") as f:
			repo_dict = json.loads(f.read())

			data.append([
				repo_dict["full_name"],
				repo_dict["html_url"],
				repo_dict["created_at"],
				repo_dict["stargazers_count"], # star count
				repo_dict["pushed_at"] #last commit date
				])

	file = open('2_applied_AI_python_dataset.csv','w', newline='')
	with file:
		write = csv.writer(file)
		write.writerows(data)
	
main()