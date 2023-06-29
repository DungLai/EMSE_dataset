def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

def get_commit_sha(owner, repo, pr):
	import json
	pr = json.load(open("pulls/{}*{}/{}.json".format(owner, repo, pr)))
	return pr["merge_commit_sha"]

def main():
	file = open("14_issue_keyword_and_ML.csv", "r")
	rows = file.read().split("\n")
	i=1
	for row in rows:
		# print("Processing row " + str(i))
		i+=1
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		issue_url = row[1]
		issue_number = row[2]
		pr_list = row[3]
		pr_list_list = pr_list.split(" ")
		for pr in pr_list_list:
			create_folder_if_not_exist("15_merge_commit_sha_of_pull")
			create_folder_if_not_exist("15_merge_commit_sha_of_pull/{}*{}".format(owner,repo))
			commit_sha = get_commit_sha(owner, repo, pr)
			file = open("15_merge_commit_sha_of_pull/{}*{}/{}.txt".format(owner,repo,pr), "w")
			file.write(commit_sha)
			file.close()
main()