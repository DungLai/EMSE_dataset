import findimports
from findimports import find_imports
import os
# invalid_py_script = 0
def is_contain_ML_lib(script_path):
    # Check whether the script import one of the following tensorFlow, keras, pyTorch
    # This library parse the source code, but does not check it the library is in use or not
    try:
        imports = find_imports(script_path)
    except:
        # invalid_py_script+=1
        return False
    for module in imports:
        if "tensorflow" in module.name:
            return True
        if "torch" in module.name:
            return True
        if "keras" in module.name:
            return True
    return False

import os
from pathlib import Path

# 1. Check each issue in issue_with_closed_pr.csv
# 2. Check each PR associated to that issue
# 3. For each PR, check all script in all commit, if one script in a commit has ML lib, return true

def main():
    data = [] #issue pr pairs
    data.append(["Project Name","Issue URL", "issue number", "Closed PR that mention", "title"]) # Header
    
    file = open("issue_with_closed_pr.csv", "r")
    rows = file.read().split("\n")[1:]
    # check each issue 
    count=1
    non_exist_pr = []

    for row in rows:
        print("Processing row: " + str(count))
        count+=1
        row = row.split(",")
        name = row[0]
        owner = name.split("/")[0]
        repo = name.split("/")[1]
        issue_url = row[1]
        issue_number = row[2]
        pr_list = row[3]

        # Some title have comma in it, this will concatenate them
        title = ""
        for i in range(4,len(row)):
            title += row[i]

        pr_list_list = pr_list.split(" ")
        is_issue_contain_ML = False
        for pr in pr_list_list:
            if is_issue_contain_ML:
                break
            pr = pr.strip()

            pr_path = "PR_files/{}*{}/PR_{}".format(owner,repo,pr)
            # check if PR exist, some PR return emptiness
            # For example: https://github.com/sktime/sktime/pull/3222
            if not os.path.isdir(pr_path): 
                print("add non exist")
                non_exist_pr.append(pr_path)
                continue

            # sort commits by time
            commits_sha_path = sorted(Path(pr_path).iterdir(), key=os.path.getmtime)
            # loop through each commit in the pr
            for commit_path in commits_sha_path:
                if is_issue_contain_ML:
                    break

                # Loop through each file in the commit sha
                # skip DS_Store file
                if ".DS_Store" in str(commit_path):
                    continue
                files = os.listdir(commit_path)
                for file in files:
                    file_path = "{}/{}".format(commit_path, file)
                    if is_contain_ML_lib(file_path):
                        is_issue_contain_ML = True
                        break
        if is_issue_contain_ML:
            data.append([name,issue_url,issue_number,pr_list,title])

    import csv
    file = open("13_issue_contain_ML.csv",'w', newline='')
    with file:
        write = csv.writer(file)
        write.writerows(data)

    print("--")
    print(non_exist_pr)
    print(len(non_exist_pr))
    # print(invalid_py_script)
main()


# dirpath = "PR_files/HazyResearch*fonduer/PR_7"
# paths = sorted(Path(dirpath).iterdir(), key=os.path.getmtime)
# print(paths)