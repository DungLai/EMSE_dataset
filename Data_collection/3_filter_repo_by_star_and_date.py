# Filter by criteria :
# 1. (Check by current date - 1 Jan 2023) Newness (the projects must be created in the last 5 years)
# 2. (Check by current date - 1 Jan 2023) Popularity (the projects must have at least 100 stars)
# 3. (Check by current date - 1 Jan 2023) Activeness (the projects must have at least a commit in the last 2 years)
import csv
def main():
	filtered_data = []
	filtered_data.append(["Name","URL", "Created_at", "Star", "Last commit"]) # Header

	with open("2_applied_AI_python_dataset.csv", "r") as f:

		rows = f.read().split("\n")
		for row in rows[1:]:
			data = row.split(",")

			created_at_year = data[2][:4]
			star_count = data[3]
			last_commit_year = data[4][:4]
			# Today date is 1 Jan 2023
			if (int(created_at_year) >= 2018) and (int(last_commit_year) >= 2021) and (int(star_count) >= 100): 
				filtered_data.append([data[0], data[1],data[2],data[3],data[4]])

	file = open('3_filtered_repo.csv','w', newline='')
	with file:
		write = csv.writer(file)
		write.writerows(filtered_data)
main()