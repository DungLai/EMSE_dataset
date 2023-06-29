import json
import urllib.request
import os

# token = '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'
token = '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'

# Return the list of commit urls in a PR
# Example: https://api.github.com/repos/tesseract-ocr/tesseract/git/commits/9ed901a26da687a43b4ae9859db179a2edce510f
def get_commit_urls(owner, repo, pr_number):
	commit_urls = []
	api = "https://api.github.com/repos/{}/{}/pulls/{}/commits".format(owner, repo, pr_number)
	hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
	req = urllib.request.Request(api, headers = hdr)
	response = urllib.request.urlopen(req)
	content = response.read()
	content = content.decode("ISO-8859-1")
	content_json = json.loads(content)
	number_of_commits = len(content_json)
	for i in range(number_of_commits):
		commit_urls.append(content_json[i]["commit"]["url"])
	return commit_urls

# Get the name of files that are modified in a commit then download it
# Example input: https://api.github.com/repos/tesseract-ocr/tesseract/git/commits/9ed901a26da687a43b4ae9859db179a2edce510f
def download_files_from_commit_url(commit_url, pr_number):	
	owner = commit_url.split("/")[4]
	repo = commit_url.split("/")[5]
	commit_sha = commit_url.split("/")[-1]
	create_folder_if_not_exist("PR_files")
	create_folder_if_not_exist("PR_files/{}*{}/PR_{}".format(owner,repo,pr_number))
	folder_path = "PR_files/{}*{}/PR_{}/{}".format(owner,repo,pr_number,commit_sha) # Create folder to store commit files
	create_folder_if_not_exist(folder_path)
	api = "https://api.github.com/repos/{}/{}/commits/{}".format(owner, repo, commit_sha)
	hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
	req = urllib.request.Request(api, headers = hdr)
	response = urllib.request.urlopen(req)
	content = response.read()
	content = content.decode("ISO-8859-1")
	content_json = json.loads(content)
	for file in content_json["files"]: # Loop through file change	
		raw_url = file["raw_url"]
		filename = file["filename"]
		extension = filename.split(".")[-1]
		if extension.lower() != "py":
			continue
		response = urllib.request.urlopen(raw_url) # Download the file
		file_content = response.read()
		file_content = file_content.decode("ISO-8859-1")
		filename = filename.replace("/", "*")
		f = open(folder_path + "/" + filename, "w")
		f.write(file_content)

def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

# Create folder and download files change in every commits associated to a PR
def download_pr_files(owner, repo, pr_number):
	commit_urls = get_commit_urls(owner, repo, pr_number)
	for commit_url in commit_urls:
		download_files_from_commit_url(commit_url, pr_number)

def main():
	file = open("issue_with_closed_pr.csv", "r")
	rows = file.read().split("\n")[1:]
	# check each issue
	i=144 #Row in excel file. The next line -2
	for row in rows[i-1:]:
		print("Processing row " + str(i+1))
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		issue_url = row[1]
		issue_number = row[2]
		pr_list = row[3]

		pr_list = pr_list.split(" ")

		for pull_number in pr_list:

			# Skip if PR already downloaded
			path = "PR_files/{}*{}/PR_{}".format(owner,repo,pull_number)
			if os.path.isdir(path):
				print("Already download: " + path)
				continue

			download_pr_files(owner, repo, pull_number)
		print("Done: Row {}/{}: {}, pull: {}".format(i+1, len(rows),issue_url, pull_number))
		i+=1

main()