# Some issue number redirect to a pull, this script exclude all issue that leads to a pull by filter out the issue number that is also in the pull list

def main():

	count_issue_after_clean = []
	file = open("3_filtered_repo.csv", "r")
	data = file.read().split('\n')
	names = []
	for row in data[1:]:
		row = row.split(",")
		name = row[0]
		names.append(name)
		print(name)
		owner = name.split("/")[0]
		repo = name.split("/")[1]

		issue_list = open("issues_list/{}*{}.txt".format(owner,repo), "r").read()
		pull_list = open("pulls_list/{}*{}.txt".format(owner,repo), "r").read()

		# Remove the bracket from the string
		issue_list = issue_list[1:-1].split(",")
		pull_list = pull_list[1:-1].split(",")

		issue_temp = []
		pull_temp = [] 

		# convert element in the list from string to int
		for issue in issue_list:
			# Skip incase there is no issue
			if issue == "":
				continue
			issue_temp.append(int(issue))

		for pull in pull_list:
			# Skip incase there is no pull
			if pull == "":
				continue
			pull_temp.append(int(pull))	

		issue_list = issue_temp
		pull_list = pull_temp

		# some issue get redirect to a pull, remove those
		for pull in pull_list:
			if pull in issue_list:
				issue_list.remove(pull)

		count_issue_after_clean.append(len(issue_list))


		with open("cleaned_issues_number/{}*{}.txt".format(owner,repo), "w") as output:
			output.write(str(issue_list))

	# sort 2 list 
	count_issue_after_clean, names = (list(t) for t in zip(*sorted(zip(count_issue_after_clean, names),reverse=True)))

	print(count_issue_after_clean)
	print(len(count_issue_after_clean))
	print(sum(count_issue_after_clean))

	import matplotlib.pyplot as plt

	x_axis = names
	y_axis = count_issue_after_clean

	plt.bar(x_axis, y_axis)
	plt.title('Number of issues for 435 projects')
	plt.xlabel("Repo name")
	plt.ylabel('Number of issues')
	plt.show()

main()