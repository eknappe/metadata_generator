#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  4 16:23:19 2025

@author: knappeel

Script to convert terminal entry of metadata information into a streamlit app
for better user experience.
"""


import streamlit as st
import requests
import csv
import json
import re
from io import StringIO
from datetime import datetime

#setup the page configuration
st.set_page_config(
    page_title="Datalakes Metadata Generator",
    layout="wide",
    initial_sidebar_state="expanded")


#initalize session state
#this is basically the storing the entered data

if 'metadata' not in st.session_state:
    st.session_state.metadata = {}
if 'current_step' not in st.session_state:
    st.session_state.current_step = 0
    

#import the api function developed for v1 of metadata generator

##set the different data/software licenses
DATASET_LICENSES = ["CC BY 4.0","CC0", "CC BY-NC 4.0", "CC BY-SA 4.0"]
SOFTWARE_LICENSES = ["MIT", "Apache License 2.0", "GNU GPL-3.0", "GNU GLP-2.0"]


#orcid id
def lookup_orcid_id(first_name, last_name, max_results =5):
    
    if not first_name or not last_name or not first_name.strip() or not last_name.strip():
        return []
    
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
        
        parsed_results = []
        for row in results:
            if len(row)>= 4 and row[0].strip():
                parsed_results.append({
                'orcid_id' : row[0].strip(),
                'given_names' : row[1].strip(),
                'family_name' : row[2].strip(),
                'institution' : row[3].strip() if len(row) > 3 else "",
                'display_name': f"{row[1].strip()} {row[2].strip()}"
                })
        
        return parsed_results
    
    except Exception as e:
        st.error(f"Error during ORCID lookup: {e}")
        return []

#ror lookup
def lookup_ror_id(affiliation_name, max_results= 3):
    #look up the ROR affiliation when an affiliation is given
    #this is the normal affiliation identifier for DataCite
    #don't want folks to have to look it up themselves

    if not affiliation_name or not affiliation_name.strip():
        return []
    
    search_query = affiliation_name.strip()
    
    try:
        #ROR api
        url = "https://api.ror.org/organizations"
        params = {"query" : search_query, "page": 1}

        response = requests.get(url, params =params, timeout = 10)
        response.raise_for_status()
        
        data = response.json()
        
        items = data.get('items', [])
        if not items:
            st.warning("NO results found.")
            return []
        
        
        parsed_results = []
        
        for i, result in enumerate(items[:max_results]):
            try:
                #extract the ror id
                ror_id_url = result.get('id')
                if not ror_id_url:
                    continue
                ror_id = ror_id_url.replace('https://ror.org/','')
                
                #extract the name - the structure of this api call is very odd
                name = 'Unknown'
                names = result.get('names', [])
                
                for n in names: 
                    if 'ror_display' in n.get('types', []):
                        name = n.get('value', 'Unknown')
                        break
                
                #if no ror display is found
                if name == 'Unknown':
                    for n in names:
                        if 'label' in n.get('types', []):
                            name = n.get('value', 'Unknown')
                            break
                
                #extract the country - again this json file is oddly formatted
                country = 'N/A'
                locations = result.get('locations', [])
                if locations:
                    geo = locations[0].get('geonames_details', {})
                    country = geo.get('country_name', 'N/A')

                #alias
                aliases = []
                for n in names:
                    if 'alias' in n.get('types', []):
                        alias = n.get('value')
                        if alias:
                            aliases.append(alias)
                
                parsed = {
                    'ror_id': ror_id,
                    'name': name,
                    'country': country,
                    'aliases': aliases[:2]}
                
                parsed_results.append(parsed)
            
                
            except Exception as e:
                st.warning(f"DEBUG parsed results #{i}: {e}")
        
        if not parsed_results:
            st.warning("No valid ROR results found.")
            
        return parsed_results
    
    except Exception as e:
        st.error(f"Error during ROR lookup: {e}")
        return []

#validate the coordinates
def validate_coordinates(coord_str, coord_type):
    #validate the lat/lon coordinates
    if not coord_str:
        return True, ""
    
    try:
        coord_float = float(coord_str)
        if coord_type == "latitude" and not (-90 <= coord_float <= 90):
            return False, f"Warning: latitude{coord_float} is outside expected range (-90 to 90), please enter as decimal degree"
        elif coord_type == "longitude" and not (-180 <= coord_float <= 180):
            return False, f"Warning: longitude{coord_float} is outside expected range (-180 to 180), please enter as decimal degree"
            
        return True, ""
    
    except ValueError:
        return False, f" '{coord_str}' is not a valid number for {coord_type}"

#validate the doi
def validate_doi(doi_str):
    #validate the format of the doi
    if not doi_str:
        return True, ""
        
    #remove common doi prefixes if present
    cleandoi = doi_str.replace('https://doi.org/', '').replace('doi:', '')
    
    #remove trailing unwanted characters:
    doi_match = re.match(r'^(10\.\d{4,}/[a-zA-Z0-9\-_.()]+)', cleandoi)
    
    if doi_match:
        cleandoi = doi_match.group(1)
    else:
        cleandoi = re.sub(r'[./]+$', '', cleandoi)
    
    doi_pattern = r'^10\.\d{4,}/[a-zA-Z0-9\-_.()]+$'
    
    if re.match(doi_pattern, cleandoi):
        return True, cleandoi
    
    else:
        return False, f"'{doi_str}' does not appear to be valid DOI format. Expected 10.xxxx/yyyy"


#set up the streamlit entry system for the orcid id
#result_key is like a dictionary key, allows for reuse of this funtion for the 
#primary author as well as the contributors 

def orcid_lookup_component(name_key_first, name_key_last, result_key):
    #look up ORCID ID based on first and last name - will also pull affil
    first_name = st.session_state.get(name_key_first, "")
    last_name = st.session_state.get(name_key_last, "")
    
    #display them nicely:
    col1, col2 = st.columns([3,1])
    #in the columns 
    with col1:
        if st.button("🔸 Look up ORCID ID 🔸", key =f"orcid_btn_{result_key}"):
            if first_name and last_name:
                with st.spinner("Search for ORCID ID..."):
                    results = lookup_orcid_id(first_name, last_name)
                    st.session_state[f'orcid_results_{result_key}'] = results
                    #search was performed
                    st.session_state[f'orcid_search_performed_{result_key}'] = True
                
            else:
                st.error("Please enter both first and last name")
                    
    #display the results
    results = st.session_state.get(f'orcid_results_{result_key}', [])
    #ensured the search was performed
    search_performed = st.session_state.get(f'orcid_search_performed_{result_key}', False)
    
    if results:
        if len(results) == 1:
            result = results[0]
            st.success(f"**Found** {result['display_name']}")
            st.write(f"ORCID: {result['orcid_id']}")
            #if affiliation/institution is there then store
            if result['institution']:
                st.write(f"Institution: {result['institution']}")
            
            col1,col2 = st.columns(2)
            
            #ask to use or not
            with col1:
                if st.button("✅ Use this ORCID ID", key=f"use_orcid_{result_key}"):
                    st.session_state[result_key] = result
                    #rerun the script/refreshes the script
                    #need to do this after updating the session state
                    st.rerun()
            with col2:
                if st.button("Do not use this ORCID ID", key=f"reject_orcid_{result_key}"):
                    st.session_state[f'orcid_results_{result_key}'] = []
                    #this also clears the search results
                    st.rerun()
        else:
            st.write(f"Found {len(results)} matches: ")
            for i, result in enumerate(results):
                if st.button(
                        f"{result['display_name']} ({result['orcid_id']}) = {result['institution'] or 'No institution listed'}",
                        key=f"select_orcid_{result_key}_{i}"):
                    
                        st.session_state[result_key] = result
                        st.session_state[f'orcid_results_{result_key}'] = []
                        st.rerun()
    elif search_performed and not results:
        st.error("No ORCID match found. Doublecheck first and last name or use manunal ORCID entry.")
                
#look up ROR in streamlit formatting
def ror_lookup_component(affiliation_key, result_key):
    affiliation = st.session_state.get(affiliation_key, "")
    
    #display it nicely
    col1, col2 = st.columns([3,1])
    with col1:
        if st.button("🔸 Lookup ROR ID 🔸", key=f"ror_btn_{result_key}"):
            if affiliation:
                with st.spinner("Searching ROR database..."):
                    results = lookup_ror_id(affiliation)
                    st.session_state[f'ror_results_{result_key}'] = results
                    #force rerun to show the results
                    st.rerun()
            else:
                st.error("Please enter an affiliaton")
    
    #display results
    results = st.session_state.get(f'ror_results_{result_key}', [])
    
    if results:
        if len(results) == 1:
            #single result, ask for confirmation:
            result = results[0]
            st.success(f"**Found:** {result['name']}")
            st.write(f"Country: {result['country']}")
            st.write(f"ROR ID: {result['ror_id']}")
            
            col1,col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Use this ROR ID", key=f"use_ror_{result_key}"):
                    st.session_state[result_key] = result
                    #clear the search results after selection
                    st.session_state[f'ror_results_{result_key}'] =[]
                    st.rerun()
            with col2:
                if st.button("Do not use this", key=f"reject_ror_{result_key}"):
                    st.session_state[f'ror_results_{result_key}'] = []
                    st.rerun()
        else:
            #thar be multiple results
            st.write(f"**Found {len(results)} matches. Please select the correct affiliation.**")
            
            for i, result in enumerate(results):
                with st.container():
                    st.write("---")
                    col1,col2 = st.columns([4,1])
                    with col1:
                        st.write(f"**{result['name']}**")
                        st.write(f"Country: {result['country']}")
                        st.write(f"ROR ID: {result['ror_id']}")
                    
                    with col2:
                        if st.button("Select", key = f"select_ror_{result_key}_{i}"):
                            st.session_state[result_key] = result
                            #clear serach after selection
                            st.session_state[f'ror_results_{result_key}']=[]
                            st.rerun()
                            
            #option to clear if none selected
            st.write("----")
            if st.button("None of these are correct", key = f"clear_ror_{result_key}"):
                st.session_state[f'ror_results_{result_key}']=[]
                st.rerun()
    
    #no results found
    elif f'ror_results_{result_key}' in st.session_state and st.session_state[f'ror_results_{result_key}'] == 0:
        st.warning("No ROR ID found for this institution.")
        st.warning("Check the spelling of the institution name.")
        
        #option to clear
        if st.button("Clear and try again", key =f"clear_no_results_{result_key}"):
            ror_results_key = f'ror_results_{result_key}'
            if ror_results_key in st.session_state:
                del st.session_state[ror_results_key]
            st.rerun()
            
    #show the selected ror 
    selected_ror = st.session_state.get(result_key, {})
    if selected_ror and selected_ror.get('ror_id'):
        #st.info(f"**Currently selected:** {selected_ror['name']} (ROR ID: {selected_ror['ror_id']})")
        
        #option to change selected
        if st.button("Change selection", key=f"change_ror_{result_key}"):
            #clear current selection
            if result_key in st.session_state:
                del st.session_state[result_key]
            
            ror_results_key = f'ror_results_{result_key}'
            if ror_results_key in st.session_state:
                del st.session_state[ror_results_key]
            st.rerun()
                    

#convert what is entered into Datacite json format
def generate_metadata():
    metadata = {
        "data": {
            "type":"dois",
            "attributes": {
                "titles":[{"title": st.session_state.get('dataset_title', ''),"xml:lang":"en-us"}],
                "creators": [],
                "publisher": "Datalakes",
                "publicationYear": st.session_state.get('publication_year', datetime.now().year),
                "resourceType": st.session_state.get('resource_type', 'Dataset'),
                "descriptions": [{"description": st.session_state.get('dataset_description', ''), "descriptionType": "Abstract", "xml:lang":"en-us"}]
                }}}
    
    #author/creator information
    author_first = st.session_state.get('author_first_name', '')
    author_last = st.session_state.get('author_last_name', '')
    
    if author_first and author_last:
        creator = {"name": f"{author_first} {author_last}", 
                   "nameType": "Personal"}
        #orcid
        author_orcid = st.session_state.get('author_orcid_data', {})
        if author_orcid.get('orcid_id'):
            creator["nameIdentifiers"] = [{
                "schemeUri": "https://orcid.org",
                "nameIdentifier": author_orcid['orcid_id'],
                "nameIdentifierScheme": "ORCID"}]
        
        #affiliation
        affiliation_name = st.session_state.get('author_affiliation', '')
        if affiliation_name:
            affiliation = {"name": affiliation_name}
            author_ror = st.session_state.get('author_ror_data', {})
            if author_ror.get('ror_id'):
                affiliation.update({
                "schemeUri": "https://ror.org",
                "affiliationIdentifier": author_ror['ror_id'],
                "affiliationIdentifierScheme": "ROR"})
            creator["affiliation"] = [affiliation]
        
        #add all the creator information into the metadata
        metadata["data"]["attributes"]["creators"] = [creator]

    #contributors
    contributors = st.session_state.get('contributors', [])
    #cycle throught all the contributors
    if contributors:
        datacite_contributors = []
        
        for contrib in contributors:
            contributor={
                "name": contrib['name'],
                "nameType": "Personal"}
            
            orcid_data = contrib.get('orcid_data', {})
            if orcid_data and orcid_data.get('orcid_id'):
                contributor["nameIdentifiers"] = [{
                    "schemeUri": "https://orcid.org",
                    "nameIdentifier": orcid_data['orcid_id'],
                    "nameIdentifierScheme": "ORCID"}]
            
            affiliation_name = contrib.get('affiliation', '')
            if affiliation_name:
                affiliation = {"name": affiliation_name}
                ror_data = contrib.get('ror_data', {})
                if ror_data and ror_data.get('ror_id'):
                    affiliation.update({
                    "schemeUri": "https://ror.org",
                    "affiliationIdentifier": ror_data['ror_id'],
                    "affiliationIdentifierScheme": "ROR"})
                contributor["affiliation"] = [affiliation]
            
            datacite_contributors.append(contributor)
            
        if datacite_contributors:
            metadata["data"]["attributes"]["contributors"] = datacite_contributors
    
    #add location
    locations = st.session_state.get('locations', [])
    if locations:
        geo_locations = []
        
        for location in locations:
            try:
                geo_location = {
                    "geoLocationPlace": location['lake_name']}
                
                lat = float(location['latitude'])
                lon = float(location['longitude'])
                
                geo_location["geoLocationPoint"] = {
                    "pointLatitude": lat,
                    "pointLongitude": lon}
                
                geo_locations.append(geo_location)
                
            except (ValueError, TypeError, KeyError):
                continue
        
        if geo_locations:
            metadata["data"]["attributes"]["geoLocations"] = geo_locations

    
    #add temporal 
    start_date = st.session_state.get('start_date')
    end_date = st.session_state.get('end_date')
    
    if start_date or end_date:
        dates = []
        if start_date and end_date:
            dates.append({"date":f"{start_date}/{end_date}", "dateType":"Collected"})
        #only one or the other
        elif start_date:
            dates.append({"date": str(start_date), "dateType": "Collected"})
        elif end_date:
            dates.append({"date": str(end_date), "dateType": "Collected"})
        
        if dates:
            metadata["data"]["attributes"]["dates"] = dates
    
    #keywords
    keywords = st.session_state.get('keywords', '')
    if keywords:
        keywords_list = [k.strip() for k in keywords.replace('\n', ',').split(',') if k.strip()]
        if keywords_list:
            metadata["data"]["attributes"]["subjects"] = [{"subject": kw, "xml:lang":"en-us"} for kw in keywords_list]
    
    #add optional fields
    if st.session_state.get('dataset_doi'):
        metadata["data"]["attributes"]["doi"] = st.session_state['dataset_doi']
    
    if st.session_state.get('license'):
        metadata["data"]["attributes"]["rightsList"] = [{"rights": st.session_state['license'],"xml:lang":"en-us"}]
    
    if st.session_state.get('dataset_version'):
        metadata["data"]["attributes"]["version"] = st.session_state['dataset_version']
    
    return metadata

#the "app"
def main():
    st.title("Datalakes Metadata Generator")
    st.markdown("Create DataCite compliant metadata for your datasets")

    with st.expander("Author Information", expanded = True):
        author_section()
        
    with st.expander("Dataset Information", expanded = True):
        dataset_section()
        
    with st.expander("Contributors & co-authors", expanded = True):
        contributors_section()
        
    with st.expander("Location", expanded = True):
        location_section()
        
    with st.expander("Time period", expanded = True):
        temporal_section()
        
    with st.expander("Keywords", expanded = True):
        keywords_section()
        
    with st.expander("Preview & export", expanded = True):
        export_section()
                

#outline each section 
def author_section():
    st.header("Author information")
    
    col1, col2 = st.columns(2)
    with col1: 
        st.text_input("First name", key="author_first_name", placeholder = "Enter first name")
    with col2:
        st.text_input("Last name", key="author_last_name", placeholder = "Enter last name")
    
    
    st.text_input("Email", key = "author_email", placeholder="author@institution.edu")
    
    #orcid lookup
    st.subheader("ORCID ID")
    orcid_lookup_component('author_first_name','author_last_name', 'author_orcid_data')
    
    #show selected
    author_orcid = st.session_state.get('author_orcid_data', {})
   
    if author_orcid:
        st.success(f"Selected ORCID: {author_orcid['display_name']} ({author_orcid['orcid_id']})")

    with st.expander("Or enter ORCID manually"):
        manual_author_orcid = st.text_input("ORCID ID (format: 0000-0000-0000-0000)", key = "manual_author_orcid",
                                             placeholder = "0000-0000-0000-0000")
        if manual_author_orcid:
            manual_author_orcid = manual_author_orcid.strip()
            #check to make sure it is correct
            orcid_pattern=r'^\d{4}-\d{4}-\d{4}-\d{4}$'
            if re.match(orcid_pattern, manual_author_orcid):
                st.success("Valid ORCID format")
            else:
                st.error("Invalid ORCID format. Expected: 0000-0000-0000-0000")
    
        
    #affiliation
    st.subheader("Affiliation")
    
    #did orcid hook us up?
    author_orcid = st.session_state.get('author_orcid_data')
    suggested_author_affiliation = author_orcid.get('institution', '') if author_orcid else ''
    
    if suggested_author_affiliation and "author_affiliation" not in st.session_state:
        st.session_state["author_affiliation"] = suggested_author_affiliation
    
    #seems like this just clutters it more
    # if suggested_author_affiliation:
    #     st.info(f"ORCID suggests: {suggested_author_affiliation}")
    
    
    st.text_input("Institution/Organization:", key="author_affiliation", placeholder = "Enter institution name")
    st.write("ROR ID is a unique ID for an organization.")
    # ror lookup
    if st.session_state.get('author_affiliation'):
        ror_lookup_component('author_affiliation', 'author_ror_data')

        #show selected
        author_ror = st.session_state.get('author_ror_data')
        if author_ror and 'name' in author_ror and 'ror_id' in author_ror:
            st.success(f"Selected ROR: {author_ror['name']} (ROR ID: {author_ror['ror_id']})")

    #sneakey submit button
    st.divider()
    if st.button("Save author information", type = "primary", key="submit_author"):
        #check if required fields are filled
        if st.session_state.get('author_first_name') and st.session_state.get('author_last_name'):
            st.success("Author information saved")

#dataset info section
def dataset_section():
    st.header("Dataset information")
            
    st.text_input("Dataset title", key="dataset_title", placeholder = "Enter descriptive title")
    st.text_area("Description/abstract", key="dataset_description", height = 100, placeholder= "Desribe your data...")
    
    col1,col2 = st.columns(2)
    
    with col1:
        st.number_input("Publication year", key="publication_year", min_value = 1950, max_value= 2050, value = datetime.now().year)
    with col2:
        resource_type = st.selectbox("Resource type", ["Dataset", "Software", "Collection", "Other"], key="resource_type")
    
    col1,col2 = st.columns(2)
    with col1:
        st.text_input("Version", key = "dataset_version", placeholder = "1.0",
                      value=st.session_state.get('dataset_version', ''))
    with col2:
        if resource_type == "Dataset":
            license_options = DATASET_LICENSES
            license_help="Select an appropriate license for your dataset. CC BY 4.0 is recommended."
            default_license = "CC BY 4.0"
        elif resource_type == "Software":
            license_options = SOFTWARE_LICENSES
            license_help="Select an appropriate license for your software. MIT or Apache is recommended."
            default_license = "MIT"
        else: #not data or software give data options
            license_options = DATASET_LICENSES
            license_help="Select an appropriate license for your resource. CC BY 4.0 is recommended."
            default_license = "CC BY 4.0"
            
        current_license = st.session_state.get('license', default_license)
        
        if current_license not in license_options:
            current_license = default_license
            st.session_state['license'] = current_license
            
        #find the index of current license for the selectbox
        try:
            license_index =license_options.index(current_license)
        except ValueError:
            license_index = 0
            
        license_select = st.selectbox(
            "License", options = license_options, index = license_index, help = license_help, key = "license")
    
    st.subheader("Additional information")
    
    doi_input=st.text_input("DOI (if published in another repository)", key="dataset_doi", placeholder = "10.XXXX/YYYY")
    
    if doi_input:
        is_valid, message = validate_doi(doi_input)
        if is_valid:
            st.success("Valid DOI format")
        else:
            st.error(f"{message}")
    
    #sneakey submit button
    st.divider()
    if st.button("Save dataset information", type = "primary", key="submit_dataset"):
        #check if required fields are filled
        if st.session_state.get('dataset_title') and st.session_state.get('dataset_description'):
            st.success("Dataset information saved")

##clear form function
def clear_contributor_form():
    #clearing any possible fields that might have been populated
    fields_to_clear = ['contrib_first', 'contrib_last', 'contrib_first_name','contrib_last_name', 'contrib_affiliation', 'manual_contrib_orcid', 'current_contrib_orcid',
                      'current_contrib_ror', 'orcid_results_current_contrib_orcid', 'ror_results_current_contrib_ror']
    for field in fields_to_clear:
        if field in st.session_state:
            del st.session_state[field]
    

def contributors_section():
    st.header("Contributors & Co-authors")
    
    #cleans up the form if you click add more contributors
    if st.session_state.get("form_needs_clearing"):
        clear_contributor_form()
        st.session_state.form_needs_clearing = False
    
    #ok start the contributor form:
    if 'contributors' not in st.session_state:
        st.session_state.contributors = []
    
    #handle editing exisiting contirbutors 
    editing_index = st.session_state.get('edit_contributor_index', None)
    if editing_index is not None:
        st.info(f"Editing contributor #{editing_index +1}")
        
        #get the contributor being edited
        if editing_index < len(st.session_state.contributors):
            editing_contrib = st.session_state.contributors[editing_index]
            
            #prepopulate with the existing data
            names = editing_contrib['name'].split(' ', 1)
            if 'temp_contrib_first' not in st.session_state:
                st.session_state.temp_contrib_first = names[0] if len(names)>0 else ''
            if 'temp_contrib_last' not in st.session_state:
                st.session_state.temp_contrib_last = names[1] if len(names)>1 else ''
            if 'temp_contrib_affiliation' not in st.session_state:
                st.session_state.temp_contrib_affiliation = editing_contrib.get('affiliation' ,'') 
     
    if st.session_state.contributors:
        st.subheader("Contributors")
        for i, contrib in enumerate(st.session_state.contributors):
            with st.expander(f"{contrib['name']} - {contrib.get('affiliation', 'No affiliation')}"):
                col1, col2, col3 = st.columns([3,1,1])
                
                with col1:
                    st.write(f"**Name:** {contrib['name']}")
                    st.write(f"**Affiliation:** {contrib.get('affiliation', 'Not specified')}")
                    
                    #show orcid info if available 
                    orcid_data = contrib.get('orcid_data', {})
                    if orcid_data and orcid_data.get('orcid_id'):
                        st.write(f"**ORCID:** {orcid_data['orcid_id']}")
                        if orcid_data.get('institution'):
                            st.write(f"**ORCID Institution:** {orcid_data['institution']}")
                    else:
                        st.write("**ORCID:** Not specified")
                    
                    #ror lookup
                    ror_data = contrib.get('ror_data', {})
                    if ror_data and ror_data.get('ror_id'):
                        st.write(f"**ROR ID:** {ror_data['ror_id']}")
                        st.write(f"**ROR Country:** {ror_data.get('country', 'Not specified')}")
                    else:
                        st.write("**ROR ID:** Not specified")
                
                #add edit option
                with col2:
                    if st.button("Edit", key=f"edit_contrib_{i}"):
                        #store exisiting contributor data for editing
                        st.session_state.edit_contributor_index = i
                        names = contrib['name'].split(' ',1)
                        st.session_state.temp_contrib_first = names[0] if len(names)>0 else ''
                        st.session_state.temp_contrib_last = names[1] if len(names)>1 else ''
                        st.session_state.temp_contrib_affiliation = contrib.get('affiliation', '')
                        st.session_state.temp_contrib_orcid = contrib.get('orcid_data', {})
                        st.session_state.temp_contrib_ror= contrib.get('ror_data', {})
                        st.rerun()
                    
                #remove the contributor
                with col3:
                    if st.button("Remove", key=f"remove_contrib_{i}"):
                        st.session_state.contributors.pop(i)
                        st.rerun()
            
        st.write(f"**Total contributors:** {len(st.session_state.contributors)}")
        st.divider()
    
    #check if were editing an existing contributor ... this feels highly inefficient way of doing this but were going with it for now
    editing_index = st.session_state.get('edit_contributor_index', None)
    if editing_index is not None and editing_index < len(st.session_state.contributors):
        st.subheader(f"Edit contributor #{editing_index +1}")


        col1, col2 = st.columns(2)
        
        with col1:
            #trying hard to not have the fields autopopulated with previous entry
            #addig this value = "" ... to try and stop that 
            contrib_first = st.text_input("First name", key="temp_contrib_first", placeholder="Enter first name",
                                          value=st.session_state.get('temp_contrib_first', ''))
        with col2:
            contrib_last = st.text_input("Last name", key="temp_contrib_last", placeholder="Enter last name",
                                         value=st.session_state.get('temp_contrib_last', ''))
        
        st.write("**ORCID ID**")

            
        orcid_lookup_component('temp_contrib_first', 'temp_contrib_last', 'temp_contrib_orcid_lookup')
        
        #show selected orcid
        temp_orcid = st.session_state.get('temp_contrib_orcid_lookup', {})
        if temp_orcid:
            st.success(f"Selected ORCID: {temp_orcid['display_name']} ({temp_orcid['orcid_id']})")

        #or manual entry
        with st.expander("OR enter ORCID manually"):
            manual_orcid = st.text_input("ORCID ID (format: 0000-0000-0000-0000)", key = "temp_manual_contrib_orcid",
                                                 placeholder = "0000-0000-0000-0000")
            if manual_orcid:
                #check to make sure the format is correct
                manual_orcid = manual_orcid.strip()
                orcid_pattern=r'^\d{4}-\d{4}-\d{4}-\d{4}$'
                if re.match(orcid_pattern, manual_orcid):
                    st.success("Valid ORCID format")
                else:
                    st.error("Invalid ORCID format. Expected: 0000-0000-0000-0000")
    
        #affiliation of contributors
        st.write("**Affiliation**")
        
        contrib_affiliation = st.text_input("Institution/Organization:", key="temp_contrib_affiliation", 
                                            placeholder="Enter institution name",
                                            value=st.session_state.get('temp_contrib_affiliation', ''))
        
        #look up with ROR
        if contrib_affiliation:
            st.write("**ROR ID lookup**")
            ror_lookup_component('temp_contrib_affiliation', 'temp_contrib_ror_lookup')
            
            #show selected ror
            temp_ror = st.session_state.get('temp_contrib_ror_lookup', {})
            if temp_ror:
                st.success(f"Selected ROR: {temp_ror['name']} (ROR ID:{temp_ror['ror_id']})")
        
        st.divider()
        col1,col2,col3 = st.columns(3)
        
        with col1:
            if st.button("Save change", type = "primary", key ="save_edit_contrib"):
                if contrib_first and contrib_last:
                    #update them
                    updated_contrib={
                        'name':f"{contrib_first.strip()} {contrib_last.strip()}",
                        'affiliation': contrib_affiliation.strip() if contrib_affiliation else ""}
                    
                    temp_orcid = st.session_state.get('temp_contrib_orcid_lookup', {})
                    manual_orcid = st.session_state.get('temp_manual_contrib_orcid', '').strip()
                    
                    if temp_orcid:
                        updated_contrib['orcid_data']= temp_orcid
                    elif manual_orcid and re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', manual_orcid):
                        updated_contrib['orcid_data'] = {
                            'orcid_id': manual_orcid,
                            'display_name': f"{contrib_first} {contrib_last}",
                            'institution':""
                            }
                    
                    #deal with ror
                    temp_ror = st.session_state.get('temp_contrib_ror_lookup', {})
                    if temp_ror:
                        updated_contrib['ror_data'] = temp_ror
                        
                    #update the contributor list now
                    st.session_state.contributors[editing_index] = updated_contrib
                    
                    #clear the editing state so slate is clean
                    del st.session_state.edit_contributor_index
                    for key in ['temp_contrib_first','temp_contrib_last', 'temp_contrib_affiliation',
                                'temp_contrib_orcid_lookup','temp_contrib_ror_lookup', 'temp_contrib_ror_lookup']:
                        if key in st.session_state:
                            del st.session_state[key]
                            st.rerun()
                    
                else:
                    st.error("Please enter both first and last name")
                        
        with col2:
            if st.button("Cancel edit", key="cancel_edit_contrib"):
                del st.session_state.edit_contributor_index
                for key in ['temp_contrib_first','temp_contrib_last', 'temp_contrib_affiliation',
                            'temp_contrib_orcid_lookup','temp_contrib_ror_lookup', 'temp_contrib_ror_lookup']:
                    if key in st.session_state:
                        del st.session_state[key]
                        st.rerun()
    
    #why did i do it this way
    #add new contributors
    else:
        st.subheader("Add new contributors")
        st.write("**Basic information**")

        
        col1, col2 = st.columns(2)
        
        with col1:
            #trying hard to not have the fields autopopulated with previous entry
            #addig this value = "" ... to try and stop that 
            contrib_first = st.text_input("First name", key="contrib_first_name", placeholder="Enter first name",
                                          value="" if st.session_state.get("form_needs_clearing") else st.session_state.get("contrib_first_name", ""))
        with col2:
            contrib_last = st.text_input("Last name", key="contrib_last_name", placeholder="Enter last name",
                                         value="" if st.session_state.get("form_needs_clearing") else st.session_state.get("contrib_last_name", ""))
        
        st.write("**ORCID ID**")
            
        orcid_lookup_component('contrib_first_name', 'contrib_last_name', 'current_contrib_orcid')
        
        #show selected orcid
        current_contrib_orcid = st.session_state.get('current_contrib_orcid', {})
        if current_contrib_orcid:
            st.success(f"Selected ORCID: {current_contrib_orcid['display_name']} ({current_contrib_orcid['orcid_id']})")
            # if current_contrib_orcid.get('institution'):
            #     st.info(f"ORCID suggested affiliation: {current_contrib_orcid['institution']}")
    
        #or manual entry
        with st.expander("OR enter ORCID manually"):
            manual_contrib_orcid = st.text_input("ORCID ID (format: 0000-0000-0000-0000)", key = "manual_contrib_orcid",
                                                 placeholder = "0000-0000-0000-0000")
            if manual_contrib_orcid:
                #check to make sure the format is correct
                manual_contrib_orcid = manual_contrib_orcid.strip()
                orcid_pattern=r'^\d{4}-\d{4}-\d{4}-\d{4}$'
                if re.match(orcid_pattern, manual_contrib_orcid):
                    st.success("Valid ORCID format")
                else:
                    st.error("Invalid ORCID format. Expected: 0000-0000-0000-0000")
        
        #affiliation of contributors
        st.write("**Affiliation**")
        
        #did orcid hook us up?
        current_contrib_orcid = st.session_state.get('current_contrib_orcid', {})
        suggested_affiliation = current_contrib_orcid.get('institution', '')
        
        #autofill the suggested affiliation
        if st.session_state.get("form_needs_clearing"):
            affiliation_value = ""
        elif suggested_affiliation and "contrib_affiliation" not in st.session_state:
            affiliation_value = suggested_affiliation
        else:
            affiliation_value = st.session_state.get("contrib_affiliation", "")
        #just makes it messy
        # if suggested_affiliation:
        #     st.info(f"ORCID suggest: {suggested_affiliation}")
        
        contrib_affiliation = st.text_input("Institution/Organization:", key="contrib_affiliation", 
                                            placeholder="Enter institution name",
                                            value=affiliation_value)
        
        #look up with ROR
        if contrib_affiliation:
            st.write("**ROR ID lookup**")
            ror_lookup_component('contrib_affiliation', 'current_contrib_ror')
            
            #show selected ror
            current_contrib_ror = st.session_state.get('current_contrib_ror', {})
            if current_contrib_ror:
                st.success(f"Selected ROR: {current_contrib_ror['name']} (ROR ID:{current_contrib_ror['ror_id']})")
        
        if st.session_state.get("form_needs_clearing"):
            st.session_state.form_needs_clearing = False
            
        #add more friends
        st.divider()
            
        col1, col2= st.columns([1,1])
        with col1:
            add_contributor = st.button("Add this contributor", type = "primary")
        with col2:
            clear_form = st.button("Clear form")
         
    
        #adding contrib
        if add_contributor:
            st.session_state.form_needs_clearing = True
            if not contrib_first or not contrib_last:
                st.error("Please enter first and last name")
            else:
                #prepare the data
                contributor_data = {'name': f"{contrib_first.strip()} {contrib_last.strip()}",
                                    'affiliation': contrib_affiliation.strip() if contrib_affiliation else ""}
                
                #toss in orcid if exists
                current_contrib_orcid = st.session_state.get('current_contrib_orcid', {})
                manual_orcid = st.session_state.get('manual_contrib_orcid', '').strip()
    
                if current_contrib_orcid:
                    contributor_data['orcid_data'] = current_contrib_orcid
                elif manual_orcid and re.match(r'^\d{4}-\d{4}-\d{4}-\d{4}$', manual_orcid):
                    contributor_data['orcid_data']= {
                        'orcid_id': manual_orcid,
                        'display_name': f"{contrib_first} {contrib_last}",
                        'institution': ""}
                
                #add in ror
                current_contrib_ror = st.session_state.get('current_contrib_ror', {})
                if current_contrib_ror:
                    contributor_data['ror_data'] = current_contrib_ror
                
                st.session_state.contributors.append(contributor_data)
                st.session_state.form_needs_clearing = True
                # clear_contributor_form()
                
                st.success(f"Added contributor: {contributor_data['name']}")
                st.rerun()
        
        if clear_form:
            clear_contributor_form()
            st.rerun()
    
    st.info("You can add as many contributors/co-authors as needed. Or skip this section if this dataset has no co-authors.")
       

#location location location
def location_section():
    st.header("Location")        
    
    #inialize location list
    if 'locations' not in st.session_state:
        st.session_state.locations = []
    
    if st.session_state.locations:
        for i, location in enumerate(st.session_state.locations):
            with st.expander(f"{location['lake_name']} ({location['latitude']}, {location['longitude']})"):
                col1, col2, col3 = st.columns([2,1,1])
                with col1:
                    st.write(f"**Lake/Site name:** {location['lake_name']}")
                    st.write(f"**Latitude (decimal degrees):** {location['latitude']}")
                    st.write(f"**Longitude (decimal degrees):** {location['longitude']}")
                with col2:
                    if st.button(f"Edit", key=f"edit_location_{i}"):
                        #add in the exisiting location data
                        st.session_state.edit_location_index = i
                        st.session_state.temp_lake_name = location['lake_name']
                        st.session_state.temp_latitude = location['latitude']
                        st.session_state.temp_longitude = location['longitude']
                        st.rerun()
                with col3:
                    if st.button(f"Remove", key=f"remove_location_{i}"):
                        st.session_state.locations.pop(i)
                        st.rerun()
        st.write(f"**Total locations:** {len(st.session_state.locations)}")
        st.divider()
    
    st.subheader("Add new location")
    
    #are we editing existing location?
    editing_index = st.session_state.get('edit_location_index', None)
    if editing_index is not None:
        st.info(f"Editing location #{editing_index +1}")

    #trying to get the form to clear are submission, on the struggle for some reason
    form_key = f"location_form_{st.session_state.get('location_form_counter', 0)}"
   
    with st.form(form_key):
        #for editing, temp vals are good
        if editing_index is not None:
            default_lake = st.session_state.get('temp_lake_name', '')
            default_lat = st.session_state.get('temp_latitude', '')
            default_lon = st.session_state.get('temp_longitude', '')
        else: #fresh and clean - new spot
            default_lake = ''
            default_lon = ''
            default_lat = ''
        
        lake_name = st.text_input("Lake/Site name", value = default_lake, placeholder="Enter lake name")
        
        col1,col2 = st.columns(2)
        with col1:
            latitude = st.text_input(
                "Latitude (decimal degrees)",
                value = default_lat,
                placeholder = "e.g. 47.404")
        with col2:
            longitude = st.text_input(
                "Longitude (decimal degrees)",
                value = default_lon,
                placeholder = "e.g. 8.609")
        
        #check its in decimal degrees
        validation_message = []
        if latitude:
            is_valid, message = validate_coordinates(latitude, "latitude")
            if not is_valid:
                validation_message.append(f"Latitude: {message}")
                
        if longitude:
            is_valid, message = validate_coordinates(longitude, "longitude")
            if not is_valid:
                validation_message.append(f"Longitude: {message}")
        
        if validation_message:
            for ms in validation_message:
                st.error(ms)
        
        
        col1,col2, col3 = st.columns([1,1,2])
        with col1:
            #update or add new location
            submit_button = st.form_submit_button("Update location" if editing_index is not None else "Add this location",
                                                  type="primary")
        with col2:
            if editing_index is not None:
                cancel_button = st.form_submit_button("Cancel edit")
            else:
                cancel_button = False
        
        #handle the submission
        if submit_button:
            if not lake_name.strip():
                st.error("Please enter lake/site name")
            elif not latitude.strip():
                st.error("Please enter latitude")
            elif not longitude.strip():
                st.error("Please enter longitude")
            else:
                #validate the coords
                lat_valid, lat_msg = validate_coordinates(latitude, "latitude")
                lon_valid, lon_msg = validate_coordinates(longitude, "longitude")
                
                if not lat_valid or not lon_valid:
                    if not lat_valid:
                        st.error(f"Invalid latitude: {lat_msg}")
                    if not lon_valid:
                        st.error(f"Invalid longitude: {lon_msg}")
                else:
                    #only proceed if both coordinates are valid
                    #yay create location object
                    new_location= {
                        'lake_name': lake_name.strip(),
                        'latitude': latitude.strip(),
                        'longitude': longitude.strip()}
                    
                    if editing_index is not None:
                        #then we are updating an exisiting location
                        st.session_state.locations[editing_index] = new_location
                        st.success(f"Updated location: {lake_name}")
                        
                        #clear editing status so theres no funny business
                        del st.session_state.edit_location_index
                         
                    else:
                        #new location
                        st.session_state.locations.append(new_location)
                        
                        if 'location_form_counter' not in st.session_state:
                            st.session_state.location_form_counter = 0
                        st.session_state.location_form_counter += 1
                            
                        
                    st.rerun()
        
        #cancel button handling
        if cancel_button:
            #clear away editing states
            if 'edit_location_index' in st.session_state:
                del st.session_state.edit_location_index
            if 'temp_lake_name' in st.session_state:
                del st.session_state.temp_lake_name
            if 'temp_latitude' in st.session_state:
                del st.session_state.temp_latitude
            if 'temp_longitude' in st.session_state:
                del st.session_state.temp_longitude       
            st.rerun()
    
        
    st.info("You can add multiple sampling locations if your dataset covers several sites/locations.")
    
    if st.session_state.locations:
        st.success(f"{len(st.session_state.locations)} locations added")
        
#time period collection      
def temporal_section():
    st.header("Time period of data collection")

    col1, col2 = st.columns(2)
    with col1:
        st.date_input("Start date (format: YYYY/MM/DD)", key = "start_date")
    with col2:
        st.date_input("End date (format: YYYY/MM/DD)", key="end_date")

    #sneakey submit button
    st.divider()
    if st.button("Save information", type = "primary", key="submit_temporal"):
        #check if required fields are filled
        if st.session_state.get('start_date') and st.session_state.get('end_date'):
            st.success("Saved")


#keyword collection
def keywords_section():
    st.header("Keywords")
    
    keywords = st.text_area("Keywords (one per line or comma seperated)",
                            key="keywords", height = 100, placeholder="e.g. measurement type, descriptor, variables collected")
    
    if keywords:
        #make a list
        keyword_list = [k.strip() for k in keywords.replace('\n', ',').split(',') if k.strip()] 
        if keyword_list:
            st.write(f"**Preview ({len(keyword_list)} keywords):**")
            st.write(" - ".join(keyword_list))

    #sneakey submit button
    st.divider()
    if st.button("Save keywords", type = "primary", key="submit_keywords"):
        #check if required fields are filled
        if st.session_state.get('keywords', '').strip():
            st.success("Keywords saved")



#wrap it all up in a nice bow
def export_section():
    st.header("Preview & export metadata")
    
    #check completeness of the metadata cant have no gaps 
    required_fields = {
        "Author name": bool(st.session_state.get('author_first_name') and st.session_state.get('author_last_name')),
        "Author email": bool(st.session_state.get('author_email')),
        "Dataset title": bool(st.session_state.get('dataset_title')),
        "Dataset description": bool(st.session_state.get('dataset_description')),
        "Location":bool(st.session_state.get('locations', []))
        }
    
    missing = [field for field, complete in required_fields.items() if not complete]
    
    #whats the current status
    st.subheader("Required fields status:")
    for field, complete in required_fields.items():
        if complete:
            st.success(f"Completed: {field}")
        else:
            st.success(f"Incomplete: {field}")
     
    #missed some things, let them know                
    if missing:
        st.warning("Missing required information:")
        st.write("Please complete all fields before exporting:")
        for field in missing:
            st.write(f"- {field}")
    else:
        st.success("All required field complete")

    #gen and display metadata for review
    try:
        metadata = generate_metadata()
        
        
        with st.expander("**Open to preview Metadata JSON:**"):
            st.json(metadata)
        
        #only export if all fields are there
        if not missing:
            st.subheader("Export the file")
            
            col1,col2 = st.columns([2,2])
            with col1:
                filename_prefix = st.text_input(
                    "Filename prefix", value= "my_dataset", placeholder = "dataset_name", 
                    help = "Final filename will be [prefix]_metadata_YYYYMMDD_HHMMSS.json")
            with col2:
                #show the preview filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                full_filename=f"{filename_prefix}_metadata_{timestamp}.json"
                st.write("**Preview:**")
                st.code(full_filename, language ="text")
            
            json_str = json.dumps(metadata, indent = 2)
            
            col1,col2 = st.columns([1,3])
            with col1:
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=full_filename,
                    mime="application/json",
                    type="primary")
        
            with col2:
                if st.button("Copy to clipboard"):
                    st.code(json_str, language="json")
                    st.info("JSON displayed above. You can copy and paste it where you like.")
    except Exception as e:
        st.error(f"Error generating the metadata: {str(e)}")
        st.write("Please check that all required information has been entered correctly.")
        
if __name__ == "__main__":
    main()        
        
        
        




