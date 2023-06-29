import requests
import urllib.request
import json

def find_all(github_user, github_repo, item_type):
	if (item_type != "pulls") and (item_type != "issues"):
		print("Wrong item type, must be pulls or issues")

	page_number = 1
	item_number_list = []
	while True:
		url = "https://api.github.com/repos/{}/{}/{}?state=all&per_page=100&page={}".format(github_user,github_repo,item_type,page_number)
		print("page number: " + str(page_number))
		page_number+=1
		token = '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'
		hdr = {'Accept':'application/vnd.github.groot-preview+json', 'Authorization': 'token ' + token}
		req = urllib.request.Request(url, headers = hdr)
		response = urllib.request.urlopen(req)
		content = response.read()
		content = content.decode("utf-8")
		if content == "[]":
			break
		issue_json = json.loads(content)
		for i in range(len(issue_json)):
			item_number_list.append(issue_json[i]["number"])
	return item_number_list	

def main():

	file = open("3_filtered_repo.csv", "r")
	data = file.read().split('\n')
	i=310
	for row in data[310:]:
		i+=1
		print(i)
		row = row.split(",")
		name = row[0]
		print(name)
		owner = name.split("/")[0]
		repo = name.split("/")[1]

		# all_issues = find_all(owner,repo, "issues")
		all_pulls = find_all(owner,repo, "pulls")

		# # some issue get redirect to a pull, remove these
		# for i in all_pulls:
		# 	print("remove " + str(i))
		# 	all_issues.remove(i)

		with open("pulls_list/{}*{}.txt".format(owner,repo), "w") as output:
			output.write(str(all_pulls))

		# with open("{}-{}/all_pulls.txt".format(owner,repo), "w") as output:
		# 	output.write(str(all_pulls))

main()