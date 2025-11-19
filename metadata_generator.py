# -*- coding: utf-8 -*-
"""
Created on Tue Jul  1 08:47:05 2025

@author: knappeel

Script to create metadata for Datalakes upload 
Generates DataCite-compliant metadata
More info on DataCite metadata schema : https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/


"""

import json
from datetime import datetime
import re
import requests
import os
from io import StringIO
import csv
#from pathlib import Path
#import yaml


class DatalakeMetadataGen:
    def __init__(self):
        self.metadata = {}
    
    ##################################################
    """FIRST DEFINE ALL THE CHECKS AND VALIDATIONS"""
    ###################################################
    
    def print_welcome(self):
        #display intro text
        print("=========================================================")
        print(" THIS SCRIPT IS TO HELP CREATE METADATA")
        print(" for all the information you will need to create a metadata file")
        print(" see README")
        print("=========================================================")
        
        
    def get_user_input(self, prompt: str, required: bool = True, default: str = None) -> str:
        #User input and validation check for the different sections 
        
        #after a certain amount of time, leave the infinite loop
        max_attempts = 6
        attempts=0
        
        while attempts < max_attempts:
            remaining = max_attempts - attempts

            display_prompt = f"{prompt} (default: {default}): " if default else f"{prompt}: "
            user_input = input(display_prompt).strip()
            
            if not user_input:
                if default is not None:
                    return default
                elif not required:
                    return ""
                else:
                    attempts += 1
                    remaining = max_attempts - attempts #need this again so that it prints when max reached
                    if remaining > 0:
                        print("This field is required. Please enter a value.")
                    else:
                        print("Max attempts reached. Skipping this field.")
                        return ""
            else:
                return user_input
            
            
    def get_yes_no(self, prompt: str) -> bool:
        #yes/no input from user
        while True: 
            response = input(f"{prompt} (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please enter 'y' or 'n'")
    
    
    def validate_doi(self, doi: str) -> str:
        #validate the format of the doi
        while True:
            if not doi:
                return ""
            
            #remove common doi prefixes if present
            cleandoi = doi.replace('https://doi.org/', '').replace('doi:', '')
            
            doi_pattern =r'^10\.\d{4,}/\S+$'
            
            if re.match(doi_pattern, cleandoi):
                return cleandoi
            
            else:
                print(f"Warning '{doi}' does not appear to be a valid doi format")
                print("Expected format: 10.xxxx/yyyy")
                choice = input("\nTo re-enter DOI press 'y', or press enter to skip: ").strip().lower()
                if choice in ('y','yes'): #in case they say yes
                    doi = input("\nEnter DOI: ").strip()
                    continue #start again
                else:
                    return ""
        
        
        
    def validate_coordinates(self, coord:str, coord_type: str) -> str:
        #validate the lat/lon coordinates
        if not coord:
            return ""
        
        try:
            coord_float = float(coord)
            if coord_type == "latitude" and not (-90 <= coord_float <= 90):
                print(f"Warning: latitude{coord_float} is outside expected range (-90 to 90), please enter as decimal degree")
            elif coord_type == "longitude" and not (-180 <= coord_float <= 180):
                print(f"Warning: longitude{coord_float} is outside expected range (-180 to 180), please enter as decimal degree")
                
            return coord
        
        except ValueError:
            print(f"Warning: '{coord}' is not a valid number for {coord_type}")
            return coord
     
        
    def lookup_orcid_id(self, first_name, last_name, max_results =5):
        #look up ORCID ID based on first and last name - will also pull affil
        if not first_name or not last_name or not first_name.strip() or not last_name.strip():
            return None
        
        first_name = first_name.strip()
        last_name = last_name.strip()
        
        try:
            #orcid api - using the csv search because allows for affil  pull
            #want affil so if there are mult entries then its easier to differentiate
            #more info here: https://github.com/ORCID/ORCID-Source/blob/main/orcid-api-web/tutorial/search.md
            url = "https://pub.orcid.org/v3.0/csv-search"
            
            search_query = f'given-names: "{first_name}" AND family-name: "{last_name}"'
            
            params = {"q":search_query, "fl": "orcid,given-names,family-name,current-institution-affiliation-name"}
            headers = {"Accept": "text/csv"}
            
            print(f"Searching for ORCID ID for: {first_name} {last_name}")
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            csv_data = StringIO(response.text)
            csv_reader = csv.reader(csv_data)
            
            #orcid api lists the headers as the first entry, don't want that
            results = list(csv_reader)[1:max_results]
            
            def parse_csv_row(row):
                if len(row)<4:
                    print("ISSUE WITH ORCID RETRIVAL")
                    return None
                orcid_id = row[0].strip()
                given_names = row[1].strip()
                family_names = row[2].strip()
                current_institution = row[3].strip() if len(row) > 3 else ""

                display_name = f"{given_names} {family_names}"
                
                return orcid_id, display_name, current_institution
            
            valid_results = []
            for row in results:
                parsed = parse_csv_row(row)
                if parsed and parsed[0]:
                    valid_results.append(parsed)
                    
            if not valid_results:
                print(f"\nNo valid ORCID entries found for {first_name} {last_name}")
                return None
            
            if len(valid_results) ==1:
                orcid_id, display_name, current_institution = valid_results[0]
                
                print("\nSingle match found")
                print(f"    Name: {display_name}")
                if current_institution:
                    print(f"    Current institution: {current_institution}")
                else:
                    print("     No insitution listed")
                print(f"    ORCID ID: {orcid_id}")
                
                if self.get_yes_no("\nUse this ORCID ID?"):
                    return orcid_id, display_name, current_institution
                else:
                    return None
                
            #when there are multiple matches
            print(f"\n Found {len(results)} potential matches: ")
            print("--------------------------------------------")
            
            for i, (orcid_id, display_name, current_institution) in enumerate(valid_results, 1):
                print(f"\n{i}. {display_name}")
                print(f"     ORCID ID: {orcid_id}")
                
                if current_institution:
                    print(f"    Current institution: {current_institution}")
                else:
                    print("    No insitution listed")
                print()
             
            print(f"{len(results) +1}. None of these match/ Skip ORCID ID")
             
            while True:
                try:
                    choice = int(input(f"\nSelect option (1-{len(results)+1}): "))
                    
                    if 1 <= choice <= len(valid_results):
                        selected = valid_results[choice-1]
                        print(f"\nSelected: {selected[1]} ({selected[0]})")
                        return selected
                    elif choice == len(valid_results)+1:
                        return None
                    else:
                        print(f"Please enter a anumber between 1 and {len(results)+1}")
                except ValueError:
                    print("Please enter a valid number")
                    
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to ORCID API: {e}")
            print("Continuing without ORCID ID...")
            return None
        except Exception as e:
            print(f"Unexpected error during ORCID lookup: {e}")
            print("Continuing without ORCID ID...")
            return None                    
    
    def get_name_with_orcid(self, prompt_text, required= True):
        #ask for name and then optionally look up orcid id and affil
        name = ""
        
        #dont get stuck in an infinite loop
        max_attempts = 10 #they really should have a name!
        attempts = 0
        
        while attempts < max_attempts:
            name = input(f"{prompt_text}: ").strip()
            
            if name or not required:
                break
            
            attempts += 1
            remaining = max_attempts - attempts
            if remaining > 0:
                print("\nThis field is required. Please enter a name.")
            else:
                print("\nMaximum attempts reached. Skipping this field.")
                print("\nYou really don't have a name?......")
        if not name:
            return {'name': '', 'orcid_id': '', 'primary_affiliation': ''}
        
        name_parts = name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:]) #for multiple last names
            
            print("\nThe ORCID ID is a unique identifier for researchers.")
            
            if self.get_yes_no("\nWould you like us to automatically look up the ORCID ID for this person?"):
                orcid_result = self.lookup_orcid_id(first_name, last_name)
            
                if orcid_result:
                    orcid_id, full_name, affiliations = orcid_result
                    primary_affiliation = affiliations if affiliations else ''
                    
                    if primary_affiliation:
                        print(f"\nFound primary affiliation from ORCID: {primary_affiliation}")
                        
                    return {'name': name, 'orcid_id': orcid_id, 'primary_affiliation': primary_affiliation}
                else:
                    return {'name': '', 'orcid_id': '', 'primary_affiliation': ''}
                
            else:
                return {'name': '', 'orcid_id': '', 'primary_affiliation': ''}

        else:
            print("\nCould not split name into first and last name for ORCID ID lookup.")
            return {'name': '', 'orcid_id': '', 'primary_affiliation': ''}
            
    
    def validate_orcid(self, orcid: str) -> str:
        #make sure orcid id is correct if manually entered
        if not orcid:
            return ""
        
        while True:
            #if they enter with the webaddress
            cleaned_orcid = orcid.replace('https://orcid.org/', '').replace('http://orcid.org/', '').replace('orcid.org/', '')
            
            #typical orcid format 0000-0000-0000-0000 (4 sets of 4 = 16 total digits)
            orcid_pattern= r'^\d{4}-\d{4}-\d{4}-\d{4}$' 
            
            if re.match(orcid_pattern, cleaned_orcid):
                return cleaned_orcid
            else:
                print(f"Warning: '{orcid}' is not a valid ORCID format.")
                print("Expected format is 0000-0000-0000-0000 (last digit can be X)")
                
                choice = input("\nEnter 'y' to re-enter ORCID, or 'n' to skip (to leave blank)").strip().lower()
                if choice == 'n' or choice == '':
                    return ""
                elif choice == 'y':
                    orcid = input("Enter ORCID ID: ").strip()
                    if not orcid: #eg they entered nothing
                        return ""
                else:
                    print("\nPlease enter 'y' or 'n'")
                    continue
        
        
    def display_section_summary(self, section_name: str, fields: dict):
        #display a summary of the metadata for checking
        print("---------------------------------")
        print(f"\n{section_name.upper()} SUMMARY")
        
        #print the exisiting info
        for key,value in fields.items():
            if key == 'identifiers': #since there is orcid and email
                if value:
                    identifier_strings = []
                    for identifier in value:
                        identifier_strings.append(f"{identifier['identifier_type']}: {identifier['identifier']}")
                    print(f"Identifiers: {', '.join(identifier_strings)}")
                else:
                    print("Identifiers: None")
            
            elif isinstance(value,list):
                if value:
                    print(f"{key.capitalize()}: {', '.join(str(v) for v in value)}")
                else:
                    print(f"{key.capitalize()}: None")
            else: 
                print(f"{key.capitalize()}: {value  or 'None'}")


        print("------------------------------")
            
            
    def get_correction_choice(self, fields: dict) -> str:
        #get user input on if they want to change any of their answers
        #will be based on numbers for ease of changing things
        field_list = list(fields.keys())
        print("\nWhich field would you like to correct?")
        
        for i, field in enumerate(field_list, 1):
            print(f"{i}. {field}")
        print(f"{len(field_list) +1}. Cancel corrections")

        while True:
            try:
                choice = int(input(f"Enter (1-{len(field_list) +1}): "))
                #they want to change something
                if 1 <= choice <=len(field_list):
                    return field_list[choice - 1]
                #mistake, no corrections needed
                elif choice == len(field_list) + 1:
                    return None
                else:
                    print(f"Please enter a number between 1 and {len(field_list) +1}")
            except ValueError:
                print("Please enter valid number")
       
        
        
    def lookup_ror_id(self, affiliation_name, max_results= 5):
        #look up the ROR affiliation when an affiliation is given
        #this is the normal affiliation identifier for DataCite
        #don't want folks to have to look it up themselves
        
        if not affiliation_name or not affiliation_name.strip():
            return None
        
        search_query = affiliation_name.strip()
        
        try:
            #ROR api
            url = "https://api.ror.org/organizations"
            params = {"query" : search_query, "page": 1}
            

            print(f"\nSearching for ROR ID for: {affiliation_name}")

            response = requests.get(url, params =params, timeout = 10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('items'):
                print(f"\nNo ROR enteries found for '{affiliation_name}'")
                return None
            
            results = data['items'][:max_results]
            
            if len(results) ==1:
                result = results[0]
                ror_id = result['id'].replace('https://ror.org/','')
                
                #display aliases 
                aliases = result.get('aliases',[])
                alias_str = f" (aliases: {', '.join(aliases[:2])})" if aliases else ""

                
                #display
                print("\nFound match")
                print(f" Name: {result['name']}{alias_str}")
                print(f" Country: {result.get('country', {}).get('country_name','N/A')}")
                
                if self.get_yes_no("\nUse this ROR ID?"):
                    return ror_id
                else:
                    return None
                
            #when multiple results found, let user choose
            #sadly using the orcid affil means there are generally more options here
            #can't decide if its easier or harder to use the orcid affil and not
            #have to bother the user with adding it themselves - would love input
            print(f"\nFound {len(results)} potential matches")
            print("-----------------------------------------")
            
            for i, result in enumerate(results, 1):
                ror_id = result['id'].replace('https://ror.org/', '')
                name = result['name']
                country = result.get('country', {}).get('country_name', 'N/A')
                
                #get alternative names 
                aliases = result.get('aliases',[])
                alias_str = f" (aliases: {', '.join(aliases[:2])})" if aliases else ""
                
                print(f"{i}. {name}{alias_str}")
                print(f"    Country: {country}")
            
            print(f"{len(results)+1}. None of these match / Skip ROR ID")
            
            while True:
                try:
                    choice = int(input(f"\nSelect option (1-{len(results) +1}): "))
                    
                    if 1 <= choice <= len(results):
                        selected = results[choice -1]
                        return selected['id'].replace('https://ror.org/', '')
                    elif choice == len(results)+1:
                        return None
                    else:
                        print(f"Please enter a number between 1 and {len(results)+1}")
                except ValueError:
                    print("Please enter a valid number")
                    
                    
        except requests.exceptions.RequestException as e:
            print(f"Error connecting with ROR API: {e}")
            print("Continuing without ROR ID...")
            return None
        except Exception as e:
            print(f"Unexpected error during ROR lookup: {e}")
            print("Continuing without ROR ID...")
            return None
        
            
    def get_affiliation_with_ror(self, prompt_text, required= True):
        #ask if they want to look up the ror affiliation id
        affiliation_name = ""
        
        while True:
            affiliation_name = input(f"{prompt_text}: ").strip()
            
            if affiliation_name or not required:
                break
            print("This field is required. Use NA, if needed")
        
        if not affiliation_name:
            return {'name': '', 'ror_id': ''}
        
        
        print("\nThe ROR ID is a unique identifier for an affiliation.")
        #ask
        if self.get_yes_no("\nWould you like us to automatically look up the ROR ID for this affiliation?"):
            ror_id = self.lookup_ror_id(affiliation_name)
        else:
            ror_id = ""
        
        return {'name': affiliation_name, 'ror_id': ror_id or ''}
            
                 
    ###############################################             
    ###############################################
    """START COLLECTING THE METADATA INFORMATION"""
    ################################################
    ################################################
    
    """BASIC INFO"""
    def collect_initial_metadata(self):
        #collect the author and dataset information
        while True:
            print("---------------------------------")
            print('\n BASIC INFORMATION')
            print("------------------------------")
            
            #the fields to be collected in this function
            creator_data = self.get_name_with_orcid("\nPrimary author name")
            creator = creator_data['name']
            auto_orcid = creator_data['orcid_id']
            suggested_affiliation = creator_data['primary_affiliation']
            
            #orcid is just a suggestion, they dont have to use it 
            if suggested_affiliation:
                #print(f"\nFound affiliation from ORCID: {suggested_affiliation}")
                if self.get_yes_no("\nUse this affiliation?"):
                    affiliation_data = {'name': suggested_affiliation, 'ror_id': ''}
                    #look up ROR
                    if self.get_yes_no("\nROR is a unique ID for institutions. Look up ROR ID for this affilation?"):
                        ror_id = self.lookup_ror_id(suggested_affiliation)
                        affiliation_data['ror_id'] = ror_id or ''
                else:
                    #allow user input
                    affiliation_data = self.get_affiliation_with_ror("Primary author affilitation")
            else:
                affiliation_data = self.get_affiliation_with_ror("Primary author affilaition")
                    
            orcid = ""
            if auto_orcid:
                orcid = auto_orcid
                print(f"Using ORCID ID: {orcid}")
            else:
                #allow manual entry of orcid
                orcid = self.get_user_input("Author's ORCID ID (optional, format: 0000-0000-0000-0000)", required = False)
                if orcid:
                    orcid = self.validate_orcid(orcid)
            
            #build identifiers - eg add the info on the indentifiers were using
            identifiers = []
            
            if orcid:
                identifiers.append({'identifier':orcid,
                               'identifier_type': 'ORCID'})
            
            email = self.get_user_input("\nAuthor/contact email")

            
            if email:
                identifiers.append({'identifier':email,
                                    'identifier_type': 'email'})
            
            #more metadata info
            title= self.get_user_input("\nTitle of data")
            description = self.get_user_input("\nDescription/abstract of the data")
            publicationYear = self.get_user_input("\nData publication year (YYYY)", default = datetime.now().year)
            resource_type = self.get_user_input("\nResource type (e.g. Dataset, Software, etc", default = 'Dataset')
            
            #store temporarily as basic_fields so user can then check the output and correct as needed
            basic_fields = {
                'affiliation' : affiliation_data['name'],
                'affiliationIdentifier': affiliation_data['ror_id'],
                'creatorName' : creator,
                'identifiers' : identifiers,
                'title' : title, 
                'description' : description,
                'publicationYear': publicationYear,
                'resourceType': resource_type
            }

            #user to review the section
            self.display_section_summary("\nBASIC INFORMATION", basic_fields)
            
            if self.get_yes_no("\nIs this information correct?"):
                #save to metadata
                self.metadata.update(basic_fields)
                break
            else:
                #allow corrections
                while True:
                    field_to_correct = self.get_correction_choice(basic_fields)
                    if field_to_correct is None:
                        break
                    
                    if field_to_correct == 'affiliation':
                        basic_fields['affiliation'] = self.get_user_input("Primary author affiliation")
                    elif field_to_correct == 'affiliationIdentifier':
                        affiliation_data = self.get_affiliation_with_ror("Primary author affiliation")
                        basic_fields['affiliationIdentifier'] = affiliation_data['ror_id']
                    elif field_to_correct == 'resourceType':
                        basic_fields['resourceType'] = self.get_user_input("Resource type (e.g. Dataset, Software, etc", default = 'Dataset')
                    elif field_to_correct == 'creatorName':
                        basic_fields['creatorName'] = self.get_user_input("Primary author name")
                    elif field_to_correct == 'identifiers':
                        orcid = self.get_user_input("Author's ORCID ID (optional, format: 0000-0000-0000-0000)", required = False)
                        if orcid:
                            orcid = self.validate_orcid(orcid)
                        email = self.get_user_input("Author email/contact email")
                        
                        identifiers = []
                        if orcid:
                            identifiers.append({'identifier':orcid,
                                               'identifier_type': 'ORCID'})
                        if email:
                            identifiers.append({'identifier':email,
                                                'identifier_type': 'email'})
                        
                        basic_fields['identifiers'] = identifiers
                        
                    elif field_to_correct == 'title':
                        basic_fields['title'] = self.get_user_input("Title of data")
                    elif field_to_correct == 'description':
                        basic_fields['description'] = self.get_user_input("Description/abstract of the data")                    
                    elif field_to_correct == 'publicationYear':
                        basic_fields['publicationYear'] = self.get_user_input("Data publication year (YYYY)")                    


                    self.display_section_summary("BASIC INFORMATION", basic_fields)
                    #double check
                    if self.get_yes_no("Is this information correct now?"):
                        self.metadata.update(basic_fields)
                        return
     
        
    """CO_AUTHOR AND CONTRIBUTOR INFO"""                    
    def collect_contributors(self):
        ##collect co-author/contributor information
        #at some point adding the contributor type could be good but seems like too much at the moment
        print("---------------------------------")
        print(" COAUTHORS & CONTRIBUTORS")
        print("---------------------------------")
        contributors = [] 
        
        if self.get_yes_no("\nAdd contributors/co-authors?"):
            contributor_count = 1
            #tracking the number of contributors since there are likely to be more then 1
            while True:
                print(f"\nEntering contributor #{contributor_count}:")
                contributor_data = self.get_name_with_orcid("\nContributor/co-author name")
                name = contributor_data['name']
                auto_orcid = contributor_data['orcid_id']
                suggested_affiliation = contributor_data['primary_affiliation']
                
                if suggested_affiliation:
                    print(f"\nFound affiliation from ORCID: {suggested_affiliation}")
                    if self.get_yes_no("\nUse this affiliation?"):
                        affiliation_data = {'name':suggested_affiliation, 'ror_id': ''}
                        #look up ror
                        if self.get_yes_no("\nLook up ROR IS for this affiliation?"):
                            ror_id = self.lookup_ror_id(suggested_affiliation)
                            affiliation_data['ror_id'] = ror_id or ''
                        else:
                            affiliation_data = self.get_affiliation_with_ror("Primary author affiliation")
                    else:
                        affiliation_data = self.get_affiliation_with_ror("Primary author affiliation")

                                        
                orcid = ""
                if auto_orcid:
                    orcid = auto_orcid
                    print(f"Using ORCID ID: {orcid}")
                else:
                    orcid = self.get_user_input('Contributor ORCID ID (optional, format: 0000-0000-0000-0000)', required = False)
                
                    if orcid:
                        orcid = self.validate_orcid(orcid)
                                       
                contributor_info = {
                    'contributorName': name,
                    'contributor_affiliation': affiliation_data['name'],
                    'contributor_affiliationIdentifier':  affiliation_data['ror_id'],
                    'contributor_nameIdentifier': orcid
                    }
                
                #show contributor summary, allow for correction
                print("--------------------------------")
                for key,value in contributor_info.items():
                    print(f" {key}: {value or 'None'}")
                
                if self.get_yes_no("Is this contributor information correct?"):   
                    contributors.append(contributor_info)
                    contributor_count += 1
                
                    if not self.get_yes_no("Add another contributor?"):
                        break
                else:
                    #correct contributor
                    print("Let's correct the contributor information")
                    continue
            
            if contributors:
                self.metadata['contributors'] = contributors
                #review
                contributors_fields = {'contributors': contributors}
            
                #check them
                while True:
                    self.display_section_summary("CONTRIBUTORS", contributors_fields)
                
                
                    if self.get_yes_no("Is this contributor information correct?"):
                        break
                
                    else:
                        # allow additional corrections
                        while True:
                            print("\nWhich contributor would you like to correct?")
                            for i, contrib in enumerate(contributors,1):
                                print(f"{i}. {contrib['contributorName']} ({contrib['contributor_affiliation']})")
                            print(f"{len(contributors) +1}. Start over with all contributors")
                            print(f"{len(contributors) +2}. Cancel corrections")
                            
                            try:
                                choice = int(input(f"Enter choice (1-{len(contributors) +2}): "))
                                
                                #change the requested contributor
                                if 1 <= choice <= len(contributors):
                                    contrib_index = choice - 1 #indexing
                                    print(f"\nCorrecting contributor: {contributors[contrib_index]['contributorName']}")
                                    name = self.get_user_input("Contributor/co-author name", default=contributors[contrib_index]['contributorName'])
                                    affiliation_data = self.get_affiliation_with_ror("Contributor affiliation", default=contributors[contrib_index]['contributor_affiliation'])
                                    orcid = self.get_user_input('Contributor ORCID ID (optional, format: 0000-0000-0000-0000)', required = False, default=contributors[contrib_index]['contributor_nameIdentifier'])
                                    
                                    if orcid:
                                        orcid = self.validate_orcid(orcid)
                                                           
                                           
                                    contributors[contrib_index] = {
                                        'contributorName': name,
                                        'contributor_affiliation': affiliation_data['name'],
                                        'contributor_affiliationIdentifier': affiliation_data['ror_id'],
                                        'contributor_nameIdentifier': orcid
                                        }
                                    
                                    #check it again
                                    self.display_section_summary("CONTRIBUTORS", {'contributors':contributors})
                                    
                                    if self.get_yes_no("Is this contributor information correct?"):
                                        self.metadata.update({'contributors':contributors})
                                        return
                                    
                                #else want to redo all?
                                elif choice == len(contributors) +1:
                                    print("Starting over")
                                    break
                                
                                #else cancel corrections:
                                elif choice == len(contributors) +2:
                                    if contributors:
                                        self.metadata['contributors'] = contributors
                                    return
                                
                                else:
                                    print(f"Please enter a number between 1 and {len(contributors) +2}")
                            
                            except ValueError:
                                print("Please enter a valid number")
                        

                        continue
            else:
                return
                
            
                                
    """LOCATION INFORMATION"""          
    def collect_location(self):
        #collect the location and lake information since for datalakes
        #assuming its point obs -- could update to polygons eventually as well
        #would need another logic loop to ask which 
        
        while True:
            print("---------------------------------")
            print(" LOCATION INFO")
            print("---------------------------------")
            
            #user input and validate its in the correct format
            lat_input = self.get_user_input("\nLatitude (decimal degrees)")
            latitude = self.validate_coordinates(lat_input, "latitude")
            
            lon_input = self.get_user_input("\nLongitude (decimal degrees)")
            longitude = self.validate_coordinates(lon_input, "longitude")
            
            lake_input = self.get_user_input("\nName of lake").strip().upper()
        
            location_fields = {
                'geoLocationPlace': lake_input,
                'pointLatitude': latitude,
                'pointLongitude': longitude}
            
            #summary and review
            self.display_section_summary("\nLOCATION", location_fields)
        
            if self.get_yes_no('\nIs the location information correct?'):
                self.metadata.update(location_fields)
                break
            else:
                #allow corrections
                while True:
                    field_to_correct = self.get_correction_choice(location_fields)
                    if field_to_correct is None:
                        break
                    if field_to_correct == 'geoLocationPlace':
                        lake_input = self.get_user_input("Name of lake")
                        location_fields['geoLocationPlace'] = lake_input.strip().upper()
                    elif field_to_correct == 'pointLatitude':
                        lat_input = self.get_user_input("Latitude (decimal degrees)")
                        location_fields['pointLatitude'] = self.validate_coordinates(lat_input, "pointLatitude")
                    elif field_to_correct == 'pointLongitude':
                        lon_input = self.get_user_input("Longitude (decimal degrees)")
                        location_fields['pointLongitude'] = self.validate_coordinates(lon_input, "pointLongitude")
                    
                    self.display_section_summary("\nLOCATION", location_fields)
                    if self.get_yes_no("\nIs the location information correct now?"):
                        self.metadata.update(location_fields)
                        return
   
    """ COLLECT TEMPORAL INFORMATION"""
    def collect_temporal_coverage(self):
        #start and end times of the data collection
        
        while True:
            print("---------------------------------")
            print(" TIME PERIOD OF DATA COLLECTION")
            print("---------------------------------")
            
            start_date = self.get_user_input("\nStart date (YYYY-MM-DD)", required = False)
            start_time = self.get_user_input("\nStart time (hh:mm:ss), if needed", required = False)
            end_date = self.get_user_input("\nEnd date (YYYY-MM-DD)", required = False)
            end_time = self.get_user_input("\nEnd time (hh:mm:ss), if needed", required = False)
    
            temporal_fields = {
                'startDate': start_date,
                'startTime': start_time,
                'endDate': end_date,
                'endTime': end_time}
            
            #review and ask for summary
            self.display_section_summary("\nTEMPORAL COVERAGE", temporal_fields)
            
            if self.get_yes_no("\nIs this information correct?"):
                self.metadata.update(temporal_fields)
                break
            
            else:
                while True:
                    fields_to_correct = self.get_correction_choice(temporal_fields)
                    if fields_to_correct is None:
                        break
                    
                    if fields_to_correct == 'startDate':
                        temporal_fields['startDate'] = self.get_user_input("Start date (YYYY-MM-DD)", required = False)
                    elif fields_to_correct == 'startTime':
                        temporal_fields['startTime'] = self.get_user_input("Start time (hh:mm:ss), if needed", required = False)
                    elif fields_to_correct == 'endDate':
                        temporal_fields['endDate'] = self.get_user_input("End date (YYYY-MM-DD)", required = False)
                    elif fields_to_correct == 'endTime':
                        temporal_fields['endTime'] = self.get_user_input("End time (hh:mm:ss), if needed", required = False)
                    
                    self.display_section_summary("TEMPORAL COVERAGE", temporal_fields)
                    
                    if self.get_yes_no("Is this information correct now?"):
                        self.metadata.update(temporal_fields)
                        return
    
    
    """COLLECT ATTRIBUTIONS"""    
    def collect_attributes(self):
        #collect license info, doi, version
        while True:
            print("---------------------------------")
            print(" DATA INFO")
            print("---------------------------------")
            
            license_info = self.get_user_input("\nData license (recommended: CC-BY-4.0)", default="CC BY 4.0")
            doi_info = self.get_user_input("\nData doi (optional)", required = False)
            if doi_info:
                doi_info = self.validate_doi(doi_info)
            version_info = self.get_user_input("\nVersion of data (optional)", required = False)
            
            attribute_fields = {
                'license': license_info,
                'doi': doi_info,
                'version': version_info}
    
            self.display_section_summary("DATA INFO", attribute_fields)
            
            if self.get_yes_no("\nIs this informaiton correct?"):
                self.metadata.update(attribute_fields)
                break
            else:
                #allow for corrections
                while True:
                    fields_to_correct = self.get_correction_choice(attribute_fields)
                    if fields_to_correct is None:
                        break
                    
                    if fields_to_correct == 'license':
                        attribute_fields['license'] = self.get_user_input("Data license (recommended: CC-BY-4.0)", default="CC BY 4.0")
                        
                    elif fields_to_correct == 'doi':
                        doi_info = self.get_user_input("Data doi (optional)", required = False)
                        if doi_info:
                            attribute_fields['doi'] = self.validate_doi(doi_info)
                            
                    elif fields_to_correct == 'version':
                        attribute_fields['version'] = self.get_user_input("Version of data (optional)", required = False)
    
    
                    self.display_section_summary("DATA INFO", attribute_fields)
                    if self.get_yes_no("Is this information correct now?"):
                        self.metadata.update(attribute_fields)
                        return
                    
    """COLLECT KEYWORDS"""   
    def collect_keywords(self):
        #collect keywords - just user input, this is a spot where finding a good suggestion
        #of keywords could be helpful - I've looked but haven't found anything great
        #we could also ask james to use the datalakes variable names and put them somewhere
        #as a suggested start? 
        while True:
            print("---------------------------------")
            print(" KEYWORDS")
            print("---------------------------------")
    
            keywords_input = self.get_user_input("\nKeywords (comma seperated)", required = False)
            
            if keywords_input:
                keywords_list = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
                
            else:
                keywords_list = []
                
            
            self.display_section_summary("Keywords", {"keywords": keywords_list})
                
    
            if self.get_yes_no("\nIs this keyword information correct?"):
                self.metadata['keywords_list'] = keywords_list
                return
            
            else:
                # allow additional corrections
                while True:
                    print("\nWhich keyword would you like to correct?")
                    for i, keykey in enumerate(keywords_list,1):
                        print(f"{i}. {keykey}")
                    print(f"{len(keywords_list) +1}. Start over with all keywords")
                    print(f"{len(keywords_list) +2}. Cancel corrections")
                    
                    try:
                        choice = int(input(f"Enter choice (1-{len(keywords_list) +2}): "))
                        
                        #change the requested keyword
                        if 1 <= choice <= len(keywords_list):
                            key_index = choice - 1 #indexing
                            print(f"\nCorrecting keywords: {keywords_list[key_index]}")
                            new_keyword = self.get_user_input("Keyword", default=keywords_list[key_index])

                            keywords_list[key_index] = new_keyword
                            
                            #check it again
                            self.display_section_summary("Keywords", {'keywords':keywords_list})
                            
                            if self.get_yes_no("Is this keyword information correct?"):
                                self.metadata['keywords_list'] = keywords_list
                                return
                            
                        #else want to redo all?
                        elif choice == len(keywords_list) +1:
                            print("Starting over")
                            break
                        
                        #else cancel corrections:
                        elif choice == len(keywords_list) +2:
                            self.metadata['keywords_list'] = keywords_list
                            return
                        
                        else:
                            print("Invalid choice. please try again.")
                            
                    except ValueError:
                        print("Please enter a valid number.")

    ################################################
    ###############################################
    """CONVERT METADATA INTO DATACITE FORMAT"""
    ################################################
    ################################################    
        
    def to_datacite_json(self) -> dict:
        """Convert collected metadata to DataCite JSON format"""
        
        #build creator array
        creators = []
        if self.metadata.get('creatorName'):
            creator = {
                "name": self.metadata['creatorName'],
                "nameType": "Personal"
                }
            
            #start with none
            affiliations = None

            if self.metadata.get('affiliation'): #get no ROR
                affiliations = {
                    "name": self.metadata['affiliation']}
                if self.metadata.get('affiliationIdentifier'):
                    affiliations.update({
                        "name": self.metadata['affiliation'],
                        "schemeUri": "https://ror.org",
                        "affiliationIdentifier": self.metadata['affiliationIdentifier'],
                        "affiliationIdentifierScheme": "ROR"})
                creator['affiliation'] = [affiliations]
                
                
            #add in identifiers if they exist
            #start with empty
            nameIdentifiers = None
            
            if self.metadata.get('identifiers'):
                for identifier in self.metadata['identifiers']:
                    if identifier.get('identifier_type') == 'ORCID':  
                        nameIdentifiers = {
                            "schemeUri": "https://orcid.org",
                            "nameIdentifier": self.metadata['identifiers'],
                            "nameIdentifierScheme": "ORCID"}
                        break
        
            if nameIdentifiers:
                creator['nameIdentifiers'] = [nameIdentifiers]
            
            #create the creators segment (to be added to the final json format at the end)
            creators.append(creator)

        #build contributors array
        contributors = []
        if self.metadata.get('contributors'):
            #cycle through as many contributors as they are
            for contrib in self.metadata['contributors']:
                contributor = {
                    "name": contrib['contributorName'],
                    "nameType" :"Personal"}
                
                if contrib.get('contributor_affiliation'):
                    affiliation = {"name": contrib['contributor_affiliation']}
                    if contrib.get('contributor_affiliationIdentifier'):
                        affiliation.update({
                            "schemeUri": "https://ror.org",
                            "affiliationIdentifer": contrib['contributor_affiliationIdentifier'],
                            "affiliationScheme": "ROR"})
                    contributor['affiliation'] = [affiliation]
                
                #if orcid is there
                if contrib.get('contributor_nameIdentifier'):
                    contributor['nameIdentifier'] = [{
                        "schemeUri": "https://orcid.org",
                        "nameIdentifier":contrib['contributor_nameIdentifier'],
                        "nameIdentifierScheme": "ORCID"}]
                
                
                #add to contributors    
                contributors.append(contributor)
                
        #build location array
        geo_locations = []
        
        if self.metadata.get('geoLocationPlace') or (self.metadata.get('pointLatitude') and self.metadata.get('pointLongitude')):
            geo_location = {}
            
            if self.metadata.get('geoLocationPlace'):
                geo_location['geoLocationPlace'] = self.metadata['geoLocationPlace']
            
            if self.metadata.get('pointLatitude') and self.metadata.get('pointLongitude'):
                geo_location['geoLocationsPoint'] = {
                    "pointLatitude": float(self.metadata['pointLatitude']),
                    "pointLongitude": float(self.metadata['pointLongitude'])}
            
            geo_locations.append(geo_location)
        
        #build date array
        dates = []
        
        if self.metadata.get('startDate') or self.metadata.get('endDate'):
            date_range = ""
            
            if self.metadata.get('startDate') and self.metadata.get('endDate') and self.metadata.get('startTime') and self.metadata.get('endTime'):
                date_range = f"{self.metadata['startDate']}T{self.metadata['startTime']}/{self.metadata['endDate']}T{self.metadata['endTime']}"
            elif self.metadata.get('startDate') and self.metadata.get('endDate'):
                date_range = f"{self.metadata['startDate']}/{self.metadata['endDate']}"
            elif self.metadata.get('startDate'):
                date_range = self.metadata['startDate']
            elif self.metadata.get('endDate'):
                date_range = self.metadata['endDate']
            
            if date_range:
                dates.append({
                    "date": date_range,
                    "dateType": "Collected"})   
        
        #build subjects (keywords)
        subjects = []
        if self.metadata.get('keywords_list'):
            for keyword in self.metadata['keywords_list']:
                subjects.append({"subject":keyword})
        
        
        datacite_json = {
            "data": {
                "type": "dois",
                "attributes": {
                    "titles": [{"title" : self.metadata.get('title', '')}],
                    "creators": creators,
                    "publisher": "Datalakes",
                    "publicationYear": int(self.metadata.get('publicationYear')),
                    "resourceType": self.metadata.get('resourceType')
                    },
                    "descriptions": [{"description": self.metadata.get('description', ''), "descriptionType": "Abstract"}]
                }
            }
       
        #add in the other optional fields
        if contributors:
            datacite_json["data"]["attributes"]["contributors"] = contributors
        if geo_locations:
            datacite_json["data"]["attributes"]["geoLocations"] = geo_locations
        if dates:
            datacite_json["data"]["attributes"]["dates"] = dates
        if subjects:
            datacite_json["data"]["attributes"]["subjects"] = subjects
        if self.metadata.get('doi'):
            datacite_json["data"]["attributes"]["doi"] = self.metadata['doi']
        if self.metadata.get('license'):
            datacite_json["data"]["attributes"]["rightsList"] = [{"rights": self.metadata['license']}]
        if self.metadata.get('version'):
            datacite_json["data"]["attributes"]["version"] = self.metadata['version']
        
        return datacite_json

        
    
####################
    #### TESTING ###
    def run(self):
        self.print_welcome()
        self.collect_initial_metadata()
        self.collect_contributors()
        self.collect_location()
        self.collect_attributes()
        self.collect_keywords()
        self.collect_temporal_coverage()
        print(f"\nFinal metadata so far: {self.metadata}")


# Test the code
if __name__ == "__main__":
    print('Starting metadata generator test...')
    generator = DatalakeMetadataGen()
    generator.run()

    #generate the json                   
    print("\nConverting metadata to DataCite JSON format:")
    print("\nPlease wait......")

    datacite_json = generator.to_datacite_json()
    print(json.dumps(generator.to_datacite_json(), indent=2))
    
    #save the file
    if generator.get_yes_no("\nWould you like to save this to a file? (y/n): "):
        while True:
            filename_prefix = generator.get_user_input("\nEnter filename prefix", default="metadata")
            filename_suffix = datetime.now().strftime("%Y-%m-%d")
            filename = f"{filename_prefix}_{filename_suffix}"
            
            output_directory = generator.get_user_input("\nSave directory (enter full folder path) :", default="./metadata_output")
            
            output_directory = os.path.abspath(output_directory)
            print(f"Resolved output directory: '{output_directory}'")
            
            file_loc = os.path.join(output_directory, f"{filename}.json")
             
            
            confirm = generator.get_yes_no(f"\nWill save file as: {file_loc} - is this correct? (y/n)")
                
            if confirm:
                break

        if not os.path.exists(output_directory):
            try:
                os.makedirs(output_directory, exist_ok = True)
                print(f"Created directory: {output_directory}")
            except Exception as e:
                print(f"Failed to create directory: {e}")
                
            
        with open(file_loc, "w") as f:
            json.dump(datacite_json, f, indent = 2)
        print(f"Metadata saved to {filename}.json")
        
            















