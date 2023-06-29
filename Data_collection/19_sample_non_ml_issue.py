# This script randomly sample non-ML (issue that does not satisfy ML criteria, both not including title and not have ML library in )
# in equal proportion with ML issue per project
# Each non_ml issue need to be closed by a PR (151 non-ml issue will be collected)


# random from issue_with_closed_pr.csv
# exclude from 18_line_change_and_duration.csv

def plot_pie(values, labels):
	import matplotlib.pyplot as plt
	# Sort data
	sorted_data = sorted(zip(values, labels), reverse=True)

	# Separate sorted values and labels
	sorted_values = [x[0] for x in sorted_data]
	sorted_labels = [x[1] for x in sorted_data]

	# Create bar chart
	fig, ax = plt.subplots()
	ax.bar(range(len(sorted_values)), sorted_values)

	# Set x-tick labels
	ax.set_xticks(range(len(sorted_labels)))
	ax.set_xticklabels(sorted_labels)

	# Add value number to the top of each bar
	for i, v in enumerate(sorted_values):
	    ax.text(i, v+1, str(v), ha='center')

	# Show chart
	plt.show()

def main():
	all_issues = open("issue_with_closed_pr.csv", "r")
	all_issues = all_issues.read().split("\n")[1:]
	
	ml_issues = open("18_line_change_and_duration.csv", "r")
	ml_issues = ml_issues.read().split("\n")[1:]

	project_names = [] #name of projects (without duplication)
	issue_count_per_project = [] # count number of issue correspond to projects_names

	ml_issue_urls = []

	# Count number of ML issues per projects
	for ml_issue in ml_issues:
		ml_issue = ml_issue.split(",")
		name = ml_issue[0]
		issue_url = ml_issue[1]
		ml_issue_urls.append(issue_url)
		issue_number = ml_issue[2]
		if name not in project_names:
			project_names.append(name)
			issue_count_per_project.append(0)
		issue_count_per_project[project_names.index(name)] += 1
			
	print(project_names)
	print(issue_count_per_project)
	print(sum(issue_count_per_project))
	print(len(project_names))
	plot_pie(issue_count_per_project, project_names)

	# put all non-ml issues url to a list
	all_non_ml_issue_urls = []
	non_ml_urls = []
	for issue in all_issues:
		issue_list = issue.split(",")
		name = issue_list[0]
		issue_url = issue_list[1]
		issue_number = issue_list[2]
		closed_pr = issue_list[3]

		if issue_url not in ml_issue_urls:
			all_non_ml_issue_urls.append(issue_url)

	excluded_project = [] # These are the projects with less non_ml issues with closed pr than ml issues


	# random sample non ml issue
	# First, put all non_ml url to a list, then put all non-ml url per project by a list and sample n random entries from there
	for i in range(len(project_names)):
		name = project_names[i]		
		count = issue_count_per_project[i]	
		all_non_ml_issue_urls_per_project = [] 
		for url in all_non_ml_issue_urls:
			if name in url:
				all_non_ml_issue_urls_per_project.append(url)

		import random
		# print("Count: ",count)
		# print("Number of non_ML issue",len(all_non_ml_issue_urls_per_project))
		if count > len(all_non_ml_issue_urls_per_project):
			excluded_project.append(name)
			continue

		non_ml_urls_per_project_list = random.sample(all_non_ml_issue_urls_per_project, count)
		# print(len(non_ml_urls_per_project_list) - count)
		for url in non_ml_urls_per_project_list:
			non_ml_urls.append(url)

	print(len(non_ml_urls))
	print(excluded_project) # These project have 1 ml issues, and no more issue to sample non-ml from

	combine_dataset = open("combine_dataset.csv", "w")
	combine_dataset.write("Project Name, Issue URL, Issue number, Closed PR that mention, Category\n")

	for issue in all_issues:
		issue_list = issue.split(",")
		name = issue_list[0]
		issue_url = issue_list[1]
		issue_number = issue_list[2]
		closed_pr = issue_list[3]

		if issue_url in non_ml_urls and name not in excluded_project:
			combine_dataset.write("{},{},{},{},{}\n".format(name,issue_url,issue_number,closed_pr,"non-ml"))

	for issue in ml_issues:
		issue_list = issue.split(",")
		name = issue_list[0]
		issue_url = issue_list[1]
		issue_number = issue_list[2]
		closed_pr = issue_list[3]
		if name not in excluded_project:
			combine_dataset.write("{},{},{},{},{}\n".format(name,issue_url,issue_number,closed_pr,"ml"))


main()














