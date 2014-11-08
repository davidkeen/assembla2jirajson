#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json

data_input = []
data_output = []

if len(sys.argv) < 3 or len(sys.argv) > 4:
    print "Error incorrect argument number"
    print "Usage: " + sys.argv[0] + " <source_file> <destination_file> [<attachment_url>])"
    exit()

file_input = sys.argv[1]
file_output = sys.argv[2]

if len(sys.argv) == 4:
    attachment_url = sys.argv[3]
else:
    attachment_url = ""

# load config file
config = json.load(open('config.json'))
link_conversion = config["link_conversion"]
workflow_conversion = config["workflow_conversion"]
user_conversion = config["user_conversion"]

input_field = [
    'user_roles, ',
    'spaces, ',
    'milestones, ',
    'ticket_statuses, ',
    'tickets, ',
    'estimate_histories, ',
    'user_tasks, ',
    'ticket_comments, ',
    'ticket_associations, ',
    'documents, ',
    'document_versions, ']

input_dict = {}

# Assembla export file is not a regular json first we serialize data we want to use

# Initiate a dict key for each input type we want to save
for s in input_field:
    input_dict[s] = ''

# Read input file and save wanted line into destination key
with open(file_input) as f:
    for line in f:
        for s in input_field:
            if line.startswith(s):
                if input_dict[s] != '':
                    input_dict[s] += ',' + line[len(s):-1]
                else:
                    input_dict[s] += line[len(s):-1]

# Convert saved line into standard json data
for s in input_field:
    data_input.append(json.loads('{"' + s[:-2] + '": [' + input_dict[s] + ']}'))

# Now we can convert JSON data according to JIRA JSON schema

# Some function to return JIRA association and convert value between Assembla and Jira

def reporter_login(id, user_dict):
    login = ""
    for element in user_dict:
        if element["id"] == id:
            login = element["login"]
    return login

# milestones:fields, ["id","due_date","title","user_id","created_at","created_by","space_id","description","is_completed","completed_date","from_basecamp","basecamp_milestone_id","updated_at","updated_by","release_level","release_notes","planner_type","start_date","budget","obstacles"]
def ticket_milestone(id, input_dict):
    milestone = ""
    for element in input_dict[2]["milestones"]:
        if element[0] == id:
            milestone = element[2]
    return milestone

# spaces:fields, ["id","name","description","wiki_name","page_rank","public_permissions","team_permissions","can_join","can_apply","wiki_format","created_at","updated_at","viewers_can_post","flow_instructions","color","banner","banner_height","style","left_wikimenu","default_showpage","payer_id","is_commercial","amazon_access_key","amazon_secret_key","do_amazon_backup","amazon_backup_cleanup","do_amazon_backup_cleanup","tabs_order","parent_id","is_volunteer","allowed_ips","is_manager","subscriptions_allowed","promo_code","restricted","template_id","commercial_from","catalog_id","commission_status","watcher_permissions","banner_text","banner_link","use_as_template","restricted_date","downgraded_at","plan_subscription_id","team_tab_role","copy_link_status","ip_address","free_configuration_id","last_payer_changed_at","allowed_ips_watcher","active","status","approved","share_permissions","saml_settings","deleted_at","free_unrestricted_date","space_type"]
def space_key(id):
    key = ""
    for element in data_input[1]["spaces"]:
        if element[0] == id:
            key = element[1][0:2].upper()
    return key

# tickets:fields, ["id","number","reporter_id","assigned_to_id","space_id","summary","priority","description","created_on","updated_at","milestone_id","component_id","notification_list","completed_date","working_hours","is_story","importance","story_importance","permission_type","ticket_status_id","state","estimate","total_estimate","total_invested_hours","total_working_hours","status_updated_at"]
def ticket_key(id):
    key = ""
    for element in data_input[4]["tickets"]:
        if element[0] == id:
            key = space_key(element[4]) + '-' + str(element[1])
    return key

# We use "workflow_conversion" parameter for mapping assembla workflow to jira workflow.
# If a status is not present in "workflow_conversion" we use internal assembla state.
# ticket_statuses:fields, ["id","space_tool_id","name","state","list_order","settings","created_at","updated_at"] 
def ticket_status(id, input_dict):
    jira_name = ""
    for element in input_dict[3]["ticket_statuses"]:
        if element[0] == id:
            if element[2] in workflow_conversion:
                jira_name = workflow_conversion[element[2]]
            else:
                if element[3] == 1:
                    jira_name = "Open"
                else:
                    jira_name = "Closed"
    return jira_name

def ticket_priority(id):
    ticket_priorities = {1: "Blocker", 2: "Critical", 3: "Major", 4: "Minor", 5: "Trivial"}
    return ticket_priorities[id]

#Convert input string according to JSON encoding

users_output = ''
for i, element in enumerate(user_conversion):
    users_output += '{"name":' + json.dumps(element["login"]) + ','
    if "email" in element:
        users_output += '"email":' + json.dumps(element["email"]) + ','
    users_output += '"fullname": ' + json.dumps(element["fullname"]) + '}'
    if i < len(user_conversion) - 1:
        users_output += ','

# ticket_associations:fields, ["id","ticket1_id","ticket2_id","relationship","created_at"]
links_output = ''
for i, element in enumerate(data_input[8]["ticket_associations"]):
    links_output += '{"name":' + json.dumps(link_conversion[str(element[3])]) + ','
    links_output += '"sourceId":' + json.dumps(ticket_key(element[1])) + ','
    links_output += '"destinationId":' + json.dumps(ticket_key(element[2])) + '}'
    if i < len(data_input[8]["ticket_associations"]) - 1:
        links_output += ','

# milestones:fields, ["id","due_date","title","user_id","created_at","created_by","space_id","description","is_completed","completed_date","from_basecamp","basecamp_milestone_id","updated_at","updated_by","release_level","release_notes","planner_type","start_date","budget","obstacles"]
versions_output = {}
for element in data_input[2]["milestones"]:
    space_id = element[6]
    if element[8] == 1:
        released = 'true'
    else:
        released = 'false'
    if element[1] is None:
        releaseDate = ''
    else:
        releaseDate = str(element[1]) + 'T00:00:00+00:00'
    if space_id not in versions_output:
        versions_output[space_id] = '{"name":' + json.dumps(element[2]) + ','
        versions_output[space_id] += '"released":' + released + ','
        versions_output[space_id] += '"releaseDate":"' + releaseDate + '"}'
    else:
        versions_output[space_id] += ',{"name":' + json.dumps(element[2]) + ','
        versions_output[space_id] += '"released":' + released + ','
        versions_output[space_id] += '"releaseDate":"' + releaseDate + '"}'

# ticket_comments:fields, ["id","ticket_id","user_id","created_on","updated_at","comment","ticket_changes","rendered"]
comments_output = {}
for element in data_input[7]["ticket_comments"]:
    ticket_id = element[1]
    
    # we do not import empty comment created by assembla to notify user actions
    if (element[5] is not None) and ((element[5] != "")):
        if ticket_id not in comments_output:
            comments_output[ticket_id] = ''
        else:
            comments_output[ticket_id] += ','
        comments_output[ticket_id] += '{"author":' + json.dumps(reporter_login(element[2], user_conversion)) + ','
        comments_output[ticket_id] += '"body":' + json.dumps(element[5]) + ','
        comments_output[ticket_id] += '"created":"' + element[3] + '"}'

# document_versions:fields, ["id","document_id","version","filename","name","description","created_at","created_by","content_type","filesize","use_as","updated_at","image_filename","ticket_id","has_thumbnail","external_download_uri","external_document_id","external_filesystem_id"]
attachments_version_output = {}
for element in data_input[10]["document_versions"]:
    document_id = element[1]
    if document_id not in attachments_version_output:
        attachments_version_output[document_id] = []
    attachments_version_output[document_id].append(element[2])

# documents:fields, ["id","filename","name","description","indexable_text","created_at","updated_at","created_by","updated_by","space_id","content_type","filesize","use_as","version","attachable_guid","image_filename","position","attachable_type","ticket_id","has_thumbnail","cached_tag_list","attachable_id","external_download_uri","external_document_id","external_filesystem_id","token","secret"]
attachments_output = {}
for element in data_input[9]["documents"]:
    ticket_id = element[18]
    document_id = element[0]
    version_list = attachments_version_output[document_id]
    for version in version_list:
        if ticket_id not in attachments_output:
            attachments_output[ticket_id] = ''
        else:
            attachments_output[ticket_id] += ','
        if  element[2] in attachments_output[ticket_id]:
            split_name = element[2].split(".")
            new_name = ".".join(split_name[0:-1])
            new_name += element[5].replace('-', '').replace('T', '').replace(':', '')[0:14]
            new_name += "." + ".".join(split_name[-1:])
            attachments_output[ticket_id] += '{"name" :' + json.dumps(new_name) + ','
        else:
            attachments_output[ticket_id] += '{"name" :' + json.dumps(element[2]) + ','
        attachments_output[ticket_id] += '"attacher":' + json.dumps(reporter_login(element[7], user_conversion)) + ','
        attachments_output[ticket_id] += '"created":' + json.dumps(element[5]) + ','
        if element[3] is not None:
            attachments_output[ticket_id] += '"description":' + json.dumps(element[3]) + ','
        attachments_output[ticket_id] += '"uri":"' + attachment_url + element[0] + '_' + str(version) + '"}'

# tickets:fields, ["id","number","reporter_id","assigned_to_id","space_id","summary","priority","description","created_on","updated_at","milestone_id","component_id","notification_list","completed_date","working_hours","is_story","importance","story_importance","permission_type","ticket_status_id","state","estimate","total_estimate","total_invested_hours","total_working_hours","status_updated_at"]
issues_output = {}
for element in data_input[4]["tickets"]:
    space_id = element[4]
    if space_id not in issues_output:
        issues_output[space_id] = ''
    else:
        issues_output[space_id] += ','
    issues_output[space_id] += '{"summary": ' + json.dumps(element[5]) + ','
    issues_output[space_id] += '"description": ' + json.dumps(element[7]) + ','
    issues_output[space_id] += '"status": ' + json.dumps(ticket_status(element[19],data_input)) + ','
    issues_output[space_id] += '"reporter": ' + json.dumps(reporter_login(element[2],user_conversion)) + ','
    issues_output[space_id] += '"assignee": ' + json.dumps(reporter_login(element[3],user_conversion)) + ','
    issues_output[space_id] += '"created": "' + element[8] + '",'
    if element[10] is not None:
        issues_output[space_id] += '"fixedVersions": [' + json.dumps(ticket_milestone(element[10],data_input)) + '],'
    if element[9] is not None:
        issues_output[space_id] += '"updated":"' + element[9] + '",'
    if element[13] is not None:
        issues_output[space_id] += '"resolution": "Resolved",'
        issues_output[space_id] += '"resolutionDate": "' + element[13] + '",'
    if element[0] in comments_output:
        issues_output[space_id] += '"comments": [' + comments_output[element[0]] + '],'
    if element[6] is not None:
        issues_output[space_id] += '"priority": ' + json.dumps(ticket_priority(element[6])) + ','
    if element[0] in attachments_output:
        issues_output[space_id] += '"attachments": [' + attachments_output[element[0]] + '],'
    issues_output[space_id] += '"key": "' + space_key(space_id) + '-' + str(element[1]) + '",'
    issues_output[space_id] += '"externalId": "' + str(element[1]) + '"}'

# spaces:fields, ["id","name","description","wiki_name","page_rank","public_permissions","team_permissions","can_join","can_apply","wiki_format","created_at","updated_at","viewers_can_post","flow_instructions","color","banner","banner_height","style","left_wikimenu","default_showpage","payer_id","is_commercial","amazon_access_key","amazon_secret_key","do_amazon_backup","amazon_backup_cleanup","do_amazon_backup_cleanup","tabs_order","parent_id","is_volunteer","allowed_ips","is_manager","subscriptions_allowed","promo_code","restricted","template_id","commercial_from","catalog_id","commission_status","watcher_permissions","banner_text","banner_link","use_as_template","restricted_date","downgraded_at","plan_subscription_id","team_tab_role","copy_link_status","ip_address","free_configuration_id","last_payer_changed_at","allowed_ips_watcher","active","status","approved","share_permissions","saml_settings","deleted_at","free_unrestricted_date","space_type"]
project_output = ''
for i, element in enumerate(data_input[1]["spaces"]):
    project_output += '{"name": ' + json.dumps(element[1]) + ','
    project_output += '"key": "' + element[1][0:2].upper() + '",'
    if element[2] != "":
        project_output += '"description": ' + json.dumps(element[2]) + ','
    project_output += '"versions": [' + versions_output[element[0]] + '],'
    project_output += '"issues": [' + issues_output[element[0]] + ']}'
    if i < len(data_input[1]["spaces"]) - 1:
        project_output += ','

# Create JSON data and write it to export file
data_output.append(json.loads('{"users": [' + users_output + '], "links": [' + links_output + '], "projects": [' + project_output + ']}'))

with open(file_output, 'wb') as f:
    f.write((json.dumps(data_output))[1:-1])


