import requests
import urllib.request
import json

# token = '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'
token = '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'
def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

def get_pull_json(owner, repo_name, pull_number):
	api_repo_info = "https://api.github.com/repos/{}/{}/pulls/{}".format(owner, repo_name, pull_number)
	hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
	req = urllib.request.Request(api_repo_info, headers = hdr)
	
	try: # Check that the repo still exist 
		response = urllib.request.urlopen(req)
	except: 
		print("Error: " + api_repo_info)

	content = response.read()
	content = content.decode("utf-8")
	return content

def main():
	file = open("issue_pr.csv", "r")
	data = file.read().split('\n')
	i=1
	for row in data[1:]: # Note to delete later: put number of folder in issues here to continue the api call
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]

		print("Project: {} ({}/{})".format(name,i,len(data)))
		i+=1

		pr_list = row[3]
		pr_list = pr_list.split(" ")[:-1]
		for pr in pr_list:
			pr = pr.strip()
		print(pr_list)

		for pr_number in pr_list:
			# check if already download
			import os.path
			path = "pulls/{}*{}/{}.json".format(owner,repo,pr_number)
			print(path)
			if os.path.exists(path):
				print("already download: " + path)
				continue

			pull_json = get_pull_json(owner,repo,pr_number)

			create_folder_if_not_exist("pulls")
			create_folder_if_not_exist("pulls/{}*{}".format(owner,repo))

			with open("pulls/{}*{}/{}.json".format(owner,repo,pr_number), "w") as output:
				output.write(str(pull_json))

main()