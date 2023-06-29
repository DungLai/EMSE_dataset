# token = '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'
token = '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'

def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

# def get_commit_sha(owner, repo, pr):
# 	import json
# 	pr = json.load(open("pulls/{}*{}/{}.json".format(owner, repo, pr)))
# 	return pr["merge_commit_sha"]
def clone_projects(repos):
	import os

	# Local directory where the repositories will be cloned
	local_dir = ''

	# Loop through the repositories and clone them to the local directory
	for repo in repos:
		# Extract the repository name from the URL
		repo_name = repo.split('/')[-1].split('.')[0]

		# Construct the full local path where the repository will be cloned
		local_path = os.path.join(local_dir, repo_name)


		# Clone the repository using Git command line tool
		os.system(f'git clone {repo}')

	print('All repositories have been cloned successfully!')



def main():
	file = open("../14_issue_keyword_and_ML.csv", "r")
	rows = file.read().split("\n")
	i=1
	project_names = []
	for row in rows:
		# print("Processing row " + str(i))
		i+=1
		row = row.split(",")
		name = row[0]
		if name in project_names:
			continue 
		project_names.append(name)

	urls = []
	for name in project_names:
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		clone_url = "https://github.com/{}/{}.git".format(owner,repo)
		clone_url = "https://github.com/{}/{}".format(owner,repo)

		urls.append(clone_url)

	clone_projects(urls)
	print(urls)
main()