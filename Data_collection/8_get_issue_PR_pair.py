# Loop through the issue and issue timeline
import csv
import json

def main():
	data = [] #issue pr pairs
	data.append(["Project Name","Issue URL", "issue number", "pr that mention", "title"]) # Header

	import os
	subfolders = [ f.path for f in os.scandir("issues") if f.is_dir() ]
	# Loop through each project
	for i in range(len(subfolders)):
		path = subfolders[i]
		path = path.split("/")[1]
		owner = path.split("*")[0]
		repo = path.split("*")[1]
		name = "{}/{}".format(owner,repo)

		from os import listdir
		from os.path import isfile, join
		# this get name of each json file 
		issue_files = [f for f in listdir("issues/{}/issue".format(path)) if isfile(join("issues/{}/issue".format(path), f))]
		for issue_json in issue_files:
			issue_number = issue_json.split(".")[0]
			issue = json.load(open("issues/{}/issue/{}".format(path,issue_json)))
			timeline = json.load(open("issues/{}/timeline/{}".format(path,issue_json)))

			issue_title = issue['title']
			pr_mention = []
			for event in timeline:
				if (event["event"] == "cross-referenced"):
					if ("pull_request" in event["source"]["issue"]):
						pr_url = event["source"]["issue"]["pull_request"]["url"]
						pr_owner = pr_url.split("/")[4]
						pr_repo = pr_url.split("/")[5]
						pr_number = pr_url.split("/")[-1]

						# Make sure pr is from the same project
						if (pr_owner == owner) and (pr_repo == repo):
							pr_mention.append(int(pr_number))
			
			issue_url = "https://github.com/{}/{}/issues/{}".format(owner,repo,issue_number)			
			if len(pr_mention) != 0:
				pr_string = ""
				for i in range(len(pr_mention)):
					pr_string+= str(pr_mention[i]) + " "
				data.append([name,issue_url,issue_number,pr_string,issue_title])
		
	file = open('issue_pr.csv','w', newline='')
	with file:
		write = csv.writer(file)
		write.writerows(data)
	


main()