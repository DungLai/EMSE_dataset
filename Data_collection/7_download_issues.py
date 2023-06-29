import requests
import urllib.request
import json

token = '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'
# token = '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'
def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

def get_issue_json(owner, repo_name, issue_number):
	api_repo_info = "https://api.github.com/repos/{}/{}/issues/{}".format(owner, repo_name, issue_number)
	hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
	req = urllib.request.Request(api_repo_info, headers = hdr)
	
	try: # Check that the repo still exist 
		response = urllib.request.urlopen(req)
	except: 
		print("Error: " + api_repo_info)

	content = response.read()
	content = content.decode("utf-8")
	return content

def get_issue_timeline_json(owner, repo_name, issue_number):
	api_repo_info = "https://api.github.com/repos/{}/{}/issues/{}/timeline".format(owner, repo_name, issue_number)
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
	file = open("3_filtered_repo.csv", "r")
	data = file.read().split('\n')
	# start from holoclean
	# Mozilla done
	for row in data[1:]: # Note to delete later: put number of folder in issues here to continue the api call
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]

		issue_number_list = []
		f = open("cleaned_issues_number/{}*{}.txt".format(owner,repo),"r")
		list_issue = f.read()

		list_issue = list_issue.strip('][').split(', ')
		if (list_issue[0] == ""):
			print("{} has no issue".format(name))
			continue
		list_issue = [eval(i) for i in list_issue]

		for issue_number in list_issue[0:]:
			print("Project name: {}, issue number: {}, index: {}/{}".format(name,issue_number, list_issue.index(issue_number), len(list_issue)-1))

			issue_json = get_issue_json(owner,repo,issue_number)
			timeline_json = get_issue_timeline_json(owner,repo,issue_number)

			create_folder_if_not_exist("issues")
			create_folder_if_not_exist("issues/{}*{}".format(owner,repo))
			create_folder_if_not_exist("issues/{}*{}/issue".format(owner,repo))
			create_folder_if_not_exist("issues/{}*{}/timeline".format(owner,repo))

			with open("issues/{}*{}/issue/{}.json".format(owner,repo,issue_number), "w") as output:
				output.write(str(issue_json))
			with open("issues/{}*{}/timeline/{}.json".format(owner,repo,issue_number), "w") as output:
				output.write(str(timeline_json))

main()