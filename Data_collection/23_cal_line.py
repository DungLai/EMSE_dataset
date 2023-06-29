def main():

	file = open("22_all_issues.csv", "r")

	rows = file.read().split('\n')
	header = rows[0]
	data = rows[1:]

	clean_data_header = "Project Name, Issue URL, PR URL, Line Change, Fix duration (days), Category\n"
	new_file = open("23_all_issues_clean.csv", "w")
	new_file.write(clean_data_header)
	for row in data:
		row_list = row.split(",")
		line_add = row_list[4]
		line_del = row_list[5]
		project_name = row_list[0]
		issue_url = row_list[1]
		fix_pr = row_list[3]
		pr_url = "https://github.com/{}/pull/{}".format(project_name,fix_pr)
		category = row_list[7]
		fix_duration = row_list[6]
		line_change = abs(int(line_add)-int(line_del))
		print(row_list)	
		print(line_change)
		new_file.write("{},{},{},{},{},{}\n".format(project_name, issue_url, pr_url, line_change,fix_duration,category))


main()