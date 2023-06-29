# gh pr view <pr number> --json additions,deletions
def create_folder_if_not_exist(folder_name):
	import os
	if not os.path.isdir(folder_name):
	    os.makedirs(folder_name)

def get_fix_duration(owner, repo, issue_number):
	import json
	import datetime
	with open("issues/{}*{}/issue/{}.json".format(owner, repo, issue_number), "r") as f:
		data = json.load(f)
		created_at = datetime.datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
		closed_at = datetime.datetime.strptime(data["closed_at"], "%Y-%m-%dT%H:%M:%SZ") if data["closed_at"] else None
		days_open = (closed_at - created_at).days

	return days_open

def get_lines_change(owner, repo, pr_number):
	import os
	os.system(f'cd projects_clone; cd {repo}; gh pr view {pr_number} --json additions,deletions > temp.txt; cd ..')
	import json
	with open("projects_clone/{}/temp.txt".format(repo), "r") as f:
		data = json.load(f)
		return int(data["additions"]), int(data["deletions"])
	print("Error: project not found")

def main():
	header = ["Name", "Issue_URL", "Issue_number", "PR", "Line added", "Line deleted", "Fix duration (days)"]
	issues = [] 
	file = open("17_issue_pr.csv", "r")
	rows = file.read().split("\n")
	i=1
	for row in rows[1:]:
		# print("Processing row " + str(i))
		i+=1
		print(i)
		row = row.split(",")
		name = row[0]
		owner = name.split("/")[0]
		repo = name.split("/")[1]
		issue_url = row[1]
		issue_number = row[2]
		pr = row[3]
	
		line_add, line_delete = get_lines_change(owner,repo,pr)
		fix_duration = get_fix_duration(owner,repo,issue_number)

		issues.append([name,issue_url,issue_number,pr,line_add,line_delete,fix_duration])

	import csv
	file = open("18_line_change_and_duration.csv",'w', newline='')

	with file:
		write = csv.writer(file)
		write.writerow(header)
		write.writerows(issues)
main()