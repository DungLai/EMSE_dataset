# token = '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'
token = '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'

def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

def get_git_diff(owner, repo, merge_commit_sha):
	import os
	os.system(f'cd {repo}; git diff {merge_commit_sha} > ../commit_diff/{merge_commit_sha}.txt; cd ..')
def remove_empty_text_file(folder_path):
	import os
	# loop over all files in the folder
	for filename in os.listdir(folder_path):
	# check if the file is a text file and if it is empty
		if filename.endswith('.txt') and os.path.getsize(os.path.join(folder_path, filename)) == 0:
		# remove the file
			os.remove(os.path.join(folder_path, filename))

def main():
	file = open("../14_issue_keyword_and_ML.csv", "r")
	rows = file.read().split("\n")
	i=1
	project_names = []
	for row in rows:
		print("Processing row " + str(i))
		i+=1
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		issue_url = row[1]
		issue_number = row[2]
		pr_list = row[3]
		pr_list_list = pr_list.split(" ")
		pr = pr_list_list[0] # only consider the first PR, for testing purpose, this will need to be hand picked manually later
		import json
		pr = json.load(open("../pulls/{}*{}/{}.json".format(owner, repo, pr)))
		merge_commit_sha = pr["merge_commit_sha"]
		print(merge_commit_sha)
		diff_output = get_git_diff(owner, repo, merge_commit_sha)
		remove_empty_text_file("commit_diff")
	# urls = []
	# for name in project_names:
	# 	owner = name.split("/")[0]
	# 	repo = name.split("/")[1]
	# 	clone_url = "https://github.com/{}/{}.git".format(owner,repo)
	# 	clone_url = "https://github.com/{}/{}".format(owner,repo)

	# 	urls.append(clone_url)

	# clone_projects(urls)
	# print(urls)
main()