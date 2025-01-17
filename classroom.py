"""Check out student submissions for an assignment"""

# driven by two csv files:
#  - export from GitHub Classroom roster containing
#       identifier, github_username, github_id, name
#  - export from iLearn containing
#       'Email address', 'ID number'
#
# input classroom name and assignment name
# then checks out one repository per student into a directory
# named for the 'ID number'
# reports any missing or extra students
#

import csv
import subprocess
import os
import re
import glob

def read_github_roster(pattern, csvfile):
    """Read the roster exported from github, return
    a dictionary with the student ID as the key and the
    github username as the value. If there is no github ID then
    the value will be ""
    """

    result = {}
    nogithub = []
    with open(csvfile) as fd:
        reader = csv.DictReader(fd)
        for line in reader:
            if 'identifier' in line:
                match = re.search(pattern, line['identifier'])
                if match:
                    result[match.group(0)] = line['github_username']

    return result


def read_ilearn_export(csvfile, key_field):
    """Read the file exported from iLearn, return a
    dictionary with student id as the key and
    a dictionary with 'email' and 'group' as the values
    """

    workshops = []
    result = {}
    with open(csvfile) as fd:
        reader = csv.DictReader(fd)
        for line in reader:
            if 'Email address' in line and line['Email address'] != '':
                groups = line['Groups'].split(';')
                workshop = [g for g in groups if 'Practical' in g]
                if workshop != []:
                    workshop = workshop[-1].replace('[', '').replace(']', '')
                    if not workshop in workshops:
                        workshops.append(workshop)
                
                tmp = {'id': line['ID number'], 'email': line['Email address'], 'workshop': workshop}
                result[tmp[key_field]] = tmp

    print(workshops)

    return result

def read_github_repos(csvfile):
    """Read the CSV file created by get-repos.py to get the Github URLs
    for each student"""

    repos = {}
    with open(csvfile) as fd:
        reader = csv.DictReader(fd)
        for line in reader:
            repos[line['githubID']] = line['githubURL']

    return repos


def merge_students(config, github, ilearn, repos):
    """Generate one dictionary with info from both
    rosters, also return a dictionary with people not
    in both"""

    keys = set(github.keys())
    keys = set(keys.union(set(ilearn.keys())))

    roster = []
    not_in_github = []
    extra_github = []
    no_github_account = []
    for key in keys:
        if key in github and key in ilearn:
            if github[key] != '':
                student = ilearn[key].copy() 
                student['github'] = github[key]
                if github[key] in repos:
                    student['url'] = repos[github[key]]
                else:
                    print("Can't find repo for ", github[key], student[config['key-field']])
                roster.append(student)
            else:
                no_github_account.append(ilearn[key])
        elif key in github:
            extra_github.append({'id': key, 'github': github[key]})
        else:
            not_in_github.append(ilearn[key])

    return roster, not_in_github, extra_github, no_github_account


def checkout(config, student):
    """Checkout one student assignment into a directory
    named for the student id and workshop
    """

    if 'url' in student:
        outdir = os.path.join(config['outdir'], student['workshop'].replace("|", "-").replace(":", "."))
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        targetdir = os.path.join(outdir, student['id'])
        
        if os.path.exists(targetdir):
            # existing repo, pull
            cmd = ['git', 'pull']
            p1 = subprocess.Popen(cmd, cwd=targetdir, stdout=subprocess.PIPE)
            output = p1.communicate()
        else:
            try:
                cmd = ['git', 'clone', student['url'], targetdir]
                p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                output = p1.communicate()
            except:
                output = "Git clone error."

        if config["nbconvert"]:
            title = "<p>" + student['id'] + "</p>"
            return title + nbconvert(targetdir)
        else:
            return ""
    else:
        print(student)
        return ""


def nbconvert(targetdir):
    """Run 'jupyter nbconvert' in the target directory and return
    the path to any HTML files generated"""

    from nbconvert import HTMLExporter

    # 2. Instantiate the exporter. We use the `classic` template for now; we'll get into more details
    # later about how to customize the exporter further.
    html_exporter = HTMLExporter()
    html_exporter.template_name = 'classic'

    links = "<ul>"
    for root, dirs, files in os.walk(targetdir):
        for fname in files:
            if '.ipynb_checkpoints' not in root and fname.endswith('.ipynb'):
                try:
                    nbfile = os.path.join(root, fname)
                    htmlfile = os.path.splitext(nbfile)[0] + '.html'
                    (body, resources) = html_exporter.from_filename(nbfile)
                    links += "<li><a target='new' href='" + htmlfile +"'>" + htmlfile + "</a></li>"
                    with open(htmlfile, 'w') as out:
                        out.write(body)
                except:
                    links += "<li>Error processing <a target='new' href='" + nbfile + "'>" + nbfile + "</li>"

    links += "</ul>"

    return links


def checkout_workshop(config, students, workshops):
    """Checkout all students in the given workshops to
    targetdir, make subdirectories per workshop"""

    html = ""
    for student in students:
        if student['workshop'] in workshops:
            html += checkout(config, student)
            print('.', end='', flush=True)

    return html

def process(config):

    github = read_github_roster(config['github-id-pattern'], config['github-roster'])
    ilearn = read_ilearn_export(config['ilearn-csv'], config['key-field'])
    repos = read_github_repos(config['github-repos-csv'])

    print(len(github))
    print(len(ilearn))
    print(len(repos))
    students, not_in_github, extra_github, no_github_account = merge_students(config, github, ilearn, repos)
    
    if config['report']:
        print("Extra names in Github Classroom roster")
        for m in extra_github:
            print(m['id'])
        print("\nStudents not in Github Classroom Roster")
        print("Add these to the roster to associate with student github accounts")
        for m in not_in_github:
            print(m[config['key-field']])

        print("\nThese students have no github account yet")
        for m in no_github_account:
            print(m['email'])
    
    return checkout_workshop(config, students, config['workshops'])



if __name__=='__main__':

    import sys
    import json
 
    with open(sys.argv[1]) as input:
        config = json.load(input)

    github = process(config)

