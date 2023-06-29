# Here is the steps for the data collection process described in the EMSE journal paper:

Dataset:

* 23_all_issues_clean.csv: 147 ML issues and 147 non-ML issues being used for the data analysis to answer RQ1 and RQ2.
* Labelled_ML_issues_data.csv: 147 ML issues being manually labelled into 6 categories: (1 - GPU Usage; 2 - Model; 3 - Tensor and Input; 4 - Training Process; 5 - Third party usage; 6 - Other)

### Step 1
Input: repo-metadata.csv, 1_filter_repo.py
Output: Repo data json in applied_AI_python_repo_info folders,

Started with the dataset from Microsoft paper: repo-metadata.csv. This file contains 9325 repositories of non AI-ML projects, tools projects and applied AI projects.

1_filter_repo.py first filtered the applied AI projects written in python, this resulted in 2379 projects. In these 2379 projects, 37 projects were not found and cannot be retrieved using the api using the repo name and the owner name. This is either due to the projects have been deleted by the owner, set to private, or changed name. This script then downloaded the repository data by calling the api: https://api.github.com/repos/:owner/:repo 

The responses of the api were stored in json files in the folder applied_AI_python_repo_info (2342 json files). The format is as follow: owner\*repo.json. The star character was used to separate the owner name and the repo name, we wanted to avoid using underscore or dash because those characters can be used in the name of the repository.

### Step 2  
Input: json files in applied_AI_python_repo_info
Output: 2_applied_AI_python_dataset.csv

After getting the json files for all python and applied AI projects, we used the json files to create a CSV file that contains: Last commit date, creation date, and number of stars.

### Step 3
Filtered the csv file using the following criteria:
* (Check by current date - 1 Jan 2023) Newness (the projects must be created in the last 5 years)
* (Check by current date - 1 Jan 2023) Popularity (the projects must have at least 100 stars)
* (Check by current date - 1 Jan 2023) Activeness (the projects must have at least a commit in the last 2 years)

After the 3 criteria were applied, we got 435 projects, 428 projects have at least 1 issues

3_filter_repo_by_star_and_date.py script also returned the csv of the 435 projects to 3_filtered_repo.csv

### Step 4
4_get_issue_list.py downloaded the list of issues numbers for each of the project in 3_filtered_repo.csv and stored 435 txt file to issues_list folder. Because many issues got redirected to a pull request, we need to get a list of pull request numbers and exclude them from the list of the issues

### Step 5
5_get_pullrequest_list.py downloaded all pull request numbers and stored it in the pulls_list folder. This script was using the projects list from 3_filtered_repo.csv 

### Step 6
6_filter_issue.py removed all issue numbers that get redirect to a pull by scanning through the pull list and remove if it appeared in the issue list. The new issue numbers were stored in cleaned_issues_number folder.

### Step 7
7_download_issues.py downloaded the issues information and timeline of issues using the list of issue numbers in cleaned_issues_number folder.

### Step 8
8_get_issue_PR_pair.py scanned through the issue timeline and found issues that have at least a pull request that mentioned it, that pull request needed to be originated from the same project with the issue. The output was issue_pr.csv. 3969 issues were found (from the 40933 issues). 

### Step 9
9_scan_keyword scaned the titles of issue for ML keywords

### Step 10
10_download_pull.py downloaded the pull requests from issue_pr.csv. 

### Step 11
11_filter_close_PR.py generated issue_with_closed_pr.csv. This script selected only closed pull requests by looking at json file of the pull requests from pulls folder and filter closed issue only because we need to measure resolution time and only pr with closed and merged_at status. This step filtered 3969 to 3133 issues.

### Step 12 
Script 12_download_PR_code.py downloaded all files change in a PR and stored it in PR_files folder. 

### Step 13
13_find_imports.py checked each files in each commits, we found a behavior of github: A PR can be empty, for example https://github.com/sktime/sktime/pull/3222. The API for this pull returned nothing. There were 3 of them:
PR_files/sktime\*sktime/PR_3222
PR_files/sktime\*sktime/PR_3222 
PR_files/intel\*dffml/PR_1124

This script checked if keras, tensorflow or torch is imported. 1091 out of 3133 issues have script in the commits that contains at least one of them. 1091 issues filtered by ML libraries and it were stored in 13_issue_contain_ML.csv

### Step 14
14_scan_keyword.py this script read the ML glossary, remove dot, comma, single quotation and double quotation marks, round brackets and square brackets and separate the title by space. When applying this on the 1091 issue in step 13, we got 151 issues

### Step 15
15_get_merge_commit_sha_of_pull.py downloaded all merge commit sha when a pull request got merged to the master branch, this script downloaded the sha of the pull, the pulls were taken from the list of 151 issues in 14_issue_keyword_and_ML.csv and stored it in txt file in 15_merge_commit_sha_of_pull folder

### Step 16
16_auto_clone.py inside projects_clone folder automatically downloaded all repository to the local machine, get ready for the git diff in the next step. We did not upload the projects source code after cloning to this folder to avoid large files being uploaded.

### Step 17 
Nothing happen in this step, we tried to measure the lines of code change using git diff command but later realise that Github CLI command can do it with ease.

### Step 18
18_get_lines_change.py got the number of lines being deleted and added from each pr using the github cli command. It calculateed the days of fix using the issue json and generate. This generated 18_line_code_change.csv with the number of addition and deletion, and number of days for the fix

### Step 19
19_sample_non_ml_issue.py sampled non-ml issues, although there were 151 ml issues, only 147 non-ml issues were sampled, in 4 projects: ['Acellera/moleculekit', 'codertimo/BERT-pytorch', 'namisan/mt-dnn', 'nouhadziri/THRED'], there was only 1 ML issues, there was no non-ml issues to sample from. We removed these 4 projects from the ml dataset. Overall, we got 294 issues (147 ml and 147 non-ml), stored in combine_dataset.csv. Techincally, this is how we randomly sample the non ml issue: First, we started from the list of 3133 issues with PR that closed the issues. After that, we excluded the ml issues from the list to get the list of non-ml issues. After that, we counted the number of ml issues per project using the list of 151 ml issues that we got. Then we randomly sampled the non-ml issues so that the number of ml and non-ml issues were in equal proportion with ML issue per project, we used the issue url as the unique identifier throughout the process. Overall, there were 27 projects that were presented in the combine dataset

### Step 20
We manually validated the non-ml issues, picked the pull request the was the fix to each issue and calculated size of fix and fix duration for those issues. The result is in 20_all_issues.csv

### Step 21
21_get_line_duration_nonml.py calculated fix duration and line change of 147 non-ml issues and stored it in 21_line_change_and_duration_nonml.csv

### Step 22 
We manually merged 18_line_code_change.csv (ML issues) and 21_line_change_and_duration_nonml.csv (non ml issues) into 22_all_issues.csv. Removed 4 issues from the 4 projects that only have 1 issues, in total we had 147 non ml and 147 ml issues

### Step 23
23_cal_line.py calculated number of lines change by calculating the absolute difference between line added and line deleted, then stored the data in 23_all_issues_clean.csv

*** Note ***

When filtering the project by activeness (must have a commit in the last 2 years), we originally used "pushed_at" attribute in the JSON response but it only indicates the last commit of a branch, and didn't necessarily the last commit date of the actual master branch. We should use "updated at", this is the last change to the project, such as changing the description of the repo, creating wiki pages, etc. In other words, commits are a subset of updates, and the "pushed at" timestamp will therefore either be the same as the "updated at" timestamp, or it will be an earlier timestamp.

For example scikit-learn-contrib/stability-selection is an example, this has not been updated in 4 years but the commit (to a branch that is not master) is within 2 years

When getting the pr that mentioned the issue, we need to make sure that PR is comming from the same project, because every PR from any project can mention issues that are not comming from it's project

When changing attribute "pushed_at" to "updated_at", we get more project, from 435 to 675. Changing to updated at add all new repositories, all projects from the "push at" are included. We first use push at and get some project where last commit was 4 5 years ago, we hope that using updated at will remove those but it does not, so we stick to last commit date (push at attribute)

Label_ML_issues folder contains the result of the 3 labelling labelling process iteration.

