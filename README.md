# Datalake metadata generator

This script prompts users and then generates a standardized metadata file.

This metadata generation script was tailored for uploading data to DataLakes (https://www.datalakes-eawag.ch/?home), but it follows a general format that can be used for other projects. 

The metadata schema is DataCite, which is the new recommendation for all ETH Domain data repositories. More info on DataCite here (https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/description/)

DataCite is typically in JSON format, and this script collects all the necessary metadata from the user via prompting, then converts it into the DataCite JSON formatting. Knowledge of python is not necessary for this script. 

## Prior to use

The script will prompt the user for the information. For certain things, like ORCID ID and ROR IDs, the script will take the prompted information and suggest an option. The user has the option to correct or change items throughout the process.

    Primary author (first and last name, email) (REQUIRED)
    Affiliation = Primary author's current affiliation
    Title = title of the dataset (REQUIRED)
    Description = abstract explaining the dataset (unlimited characters) (REQUIRED)
    Publication Year = year the data is being published
    Resource Type = typically 'dataset'
    
    Co-authors
        First and last name
        ORCID ID (will prompt based on first and last name)
        Affiliation (will prompt based on first and last name)
    
    Location of data collection (REQUIRED)
        Latitude (decimal degrees)
        Longitude (decimal degrees)
        Name of lake

    Time period of data collection
        Start date
        Start time (if applicable)
        End data
        End time (if applicable)
    
    Data license to use (recommend CCBY 4.0)
    DOI = doi of data if published in another repository (if applicable)
    Version = if applicable
    
    Keywords = list of comma separated keywords for ease of searching data (e.g. measurementtype,lakename, etc.)
    
## Use

### Using the streamlit app on Renku
The streamlit app is also hosted on Renku, which would not require the user to have python or any libraries on their machine. The Renku session is here: https://renkulab.io/p/ellen.knappe/datalakes-streamlit. To use, launch the session (it can take sometime to launch the first session). Once it opens, you will see a "Streamlit" app in the launcher. Click and wait for the webinterface to load. Enter the required information, check the resulting json, and donwload. 

### Using the streamlit app on your computer
Make sure python and the streamlit library (along with any dependencies) are installed on your machine. Clone the repo. To start the streamlit app:
        streamlit run metadata_app.py
        python -m streamlit run metadata_app.py

This will open the app within your browser and allow you to fill in the necessary information. At the end, you can preview the information you have provided, correct as needed, and then save the metadata file (it will save to the downloads in your browser with the datastring of when the file was created). The file will not be able to be exported until all the required fields (author name, email, dataset title and description, and location are filled out). 

### Using the metadata_generator code (less recommended, not maintained)
There is also a python code that allows you to create the file without streamlit. This code will run directly in the terminal window and prompt the user, before exporting a metadata file. To run this code in your terminal window:
        python metadata_generator.py
It will then prompt the user for the correct information, allowing the user to make corrections if needed, before exporting the file into a JSON format.  


## Contact

For feedback of comments, contact ellen.knappe@lib4ri.ch


## Functions within the project

* __lookup_orcid_id(first_name, last_name, max_results=NUM)__
    * Function to lookup the ORCID and current affiliation automatically based on first and last name using the ORCID API
    * _INPUTS:_
        * first_name = author's first name
        * last_name = author's last name
        * max_results = maximum amount of results to return from the ORCID lookup
    * _RETURNS:_
        * orcid_id
        * first_name
        * last_name
        * current_institution
        * display_name

* __orcid_lookup_component(first_name, last_name, result_key)__
    * Sets up the orcid lookup within the streamlit app and displays the results for the user to select the correct ORCID or select not found using the lookup_orcid_id function 
    * _INPUTS:_
        * first_name = author's first name
        * last_name = author's last name
        * result_key = maximum amount of results to return from the ORCID lookup

* __lookup_ror_id(affiliation_name, max_results=NUM)__
    * Function to lookup the ROR ID (which is like an ORCID but for institutions) using the ROR api
    * _INPUTS:_
        * affiliation_name = full affiliation name
        * max_results = maximum amount of results to return from the  lookup
    * _RETURNS:_
        * ror_id
        * affiliation_name
        * country - location of the institute (for ease of identifying the correct institute)
        * aliases - other names for the institute (e.g. Cal for University of California)

* __ror_lookup_component(first_name, last_name, max_results)__
    * Sets up the ror lookup within the streamlit app and displays the results for the user to select the correct institution or select not found using the lookup_ror_id function 
    * _INPUTS:_
        * first_name = author's first name
        * last_name = author's last name
        * max_results = maximum amount of results to return from the ORCID lookup

* __validate_coordinates(coord_string, coord_type)__
    * Function to validate the lat and lon coordinates and ensure they are in the correct format
    * _INPUTS:_
        * coordinate_string = latitutude or longitude value
        * coordinate_type = latitutude or longitude
    * _RETURNS:_
        * False if not in the correct format
        
* __validate_doi(doi_string)__
    * Function to validate the DOI is a DOI and in the correct format
    * INPUTS:_
        * doi_string = doi
    * _RETURNS:_
        * False if not in the correct format
      
* __generate_metadata()__
    * Collects the user input information and converts it into a JSON format with the correct formatting, depending on if the user input the information (e.g. if no co-authors were filled out then it skips this section)
    * _INPUTS:_
        * dataset_title
        * primary_author_first_name
        * primary_author_last_name
        * primary_author_orcid_id
        * primary_author_affiliation
        * primary_author_affiliation_ror_id
        * data_publisher : Defaults to Datalakes
        * publicationYear : Defaults to current year
        * resourceType : Defaults to dataset
        * data_description/abstract
        * co_author_first_name : will store as many co-authors as entered by the user
        * co_author_last_name
        * co_author_orcid_id
        * co_author_affiliation
        * co_author_affiliation_ror_id
        * location_latitude
        * location_longitude
        * location_name : the name of the lake where the data was collect
        * data_collection_start_date
        * data_collect_end_date
        * keywords : as many as entered
        * dataset_doi
        * license
        * dataset_version
    * _RETURNS:_
        * A dictionary of all the metadata in the correct Datacite format

* __main()__
    * Sets up the main streamlit app and how it should look by laying out the various sections. It currently is setup to be one page that has various sections that are already expanded out 

* __author_section()__
    * Function to collect the author information within the streamlit format from the user and use the author's name too look up the ORCID ID. Once the user selects the correct ORCID, it will use this information to look up the ROR ID based on the affiliation listed in the ORCID. User has options to decline both the ORCID and ROR ID but would be required to input an affiliation. At the end of the section there is a submit button that ensures required information (author first and last name is entered)
    * _INPUTS:_
        * first_name (required) : free text response in the app
        * last_name (required): free text response in the app
        * email (required): free text response in the app
        * orcid_id : produces options based on first and last name, but also has a manual entry option that checks the orcid format
        * affiliation : uses the ORCID to suggest affiliation, allows for manual input 
        * ror_id : suggests ROR ID based on the affiliation that the user can select the correct ID
    * _RETURNS:_
        * Saves the information

* __dataset_section()__
    * Function to collect information about the dataset within the streamlit format
    * _INPUTS:_
        * dataset_title : free text respose
        * publicationYear : Defaults to current year, but will not allow data prior to 1920 or past 2099
        * resourceType : allows for selection of dataset, software, colleciton or other (Defaults to Dataset)
        * data_description/abstract : free text respose
        * dataset_version : defaults to 1
        * license: based on the resource_type, provides a recommended license but allows for selection opf a different license
        * data_doi 
    * _RETURNS:_
        * Saves the information

* __contributors_section()__
    * Function to collect the co-author information within the streamlit format from the user and use the author's name too look up the ORCID ID. Once the user selects the correct ORCID, it will use this information to look up the ROR ID based on the affiliation listed in the ORCID. User has options to decline both the ORCID and ROR ID but would be required to input an affiliation. Allows for the user to add additional co-authors or delete already entered co-authors if the information is incorrect. 
    * _INPUTS:_
        * first_name: free text response in the app
        * last_name : free text response in the app
        * email: free text response in the app
        * orcid_id : produces options based on first and last name, but also has a manual entry option that checks the orcid format
        * affiliation : uses the ORCID to suggest affiliation, allows for manual input 
        * ror_id : suggests ROR ID based on the affiliation that the user can select the correct ID
    * _RETURNS:_
        * Saves the information

* __location_section()__
    * Function to collect the information on the location the data was collected, allows user to add multiple locations. Currently setup to just allow point locations not polygons. Latitude and longitude are checked to ensure they are in decimal degrees. Will return an error and re-prompt the user if they are in a different format. 
    * _INPUTS:_
        * latitude: lat in decimal degrees
        * longitude : lon in decimal degrees
        * lake_name: free text response in the app
    * _RETURNS:_
        * Saves the information
        
* __temporal_section()__
    * Function to collect the information on the time of data collection in YYYY/MM/DD format
    * _INPUTS:_
        * start_date: lat in decimal degrees
        * end_date : lon in decimal degrees
    * _RETURNS:_
        * Saves the information        
        
* __keywords_section()__
    * Function to collect keywords. Suggests comma seperated and will divide the keywords based on this seperator. If another seperator is used, it will not seperate them
    * _INPUTS:_
        * keywords: free text response
    * _RETURNS:_
        * Saves the information            
        
* __export_section()__
    * Exports all the information into a proprely formatted JSON file with the current time as a suffix to the file name. Allows user to preview the JSON file prior to export or just copy the JSON to the clipboard. Will not allow for export if required fields are not filled in. And displays un-filled in fields for the user. 
    * _INPUTS:_
        * filename_prefix : defaults to my_dataset
    * _RETURNS:_
        * exports information into a json file and saves to the browser downloads.      
                
## License

MIT

## Authors

Ellen Knappe

## Project status

In development. 

## Renku formatting

The Renku environment setup was used from Rok Roksar's example script found here: https://gitlab.renkulab.io/rok.roskar/streamlit-v2-example

Following the instructions provided here:
    https://renku.notion.site/How-to-create-a-Streamlit-app-on-top-of-your-project-815f09a34f384396ab1f758db4110f46
    
Modifications were made to the .gitlab-ci.yml for compiling. 
