# Datalake metadata generator

This metadata generation script was tailored for uploading data to DataLakes (https://www.datalakes-eawag.ch/?home), but it follows a general format that can be used for other projects. 

The metadata schema is DataCite, which is the new recommendation for all ETH Domain data repositories. More info on DataCite here (https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/description/)

DataCite is typically in JSON format, and this script collects all the necessary metadata from the user via prompting, then converts it into the DataCite JSON formatting. Knowledge of python is not necessary for this script. 

##Prior to use

The script will prompt the user for the information. For certain things, like ORCID ID and ROR IDs, the script will take the prompted information and suggest an option. The user has the option to correct or change items throughout the process.

    Creator = Primary author (first and last name)
    Affiliation = Primary author's current affiliation
    ORCID ID 
    Title = title of the dataset
    Description = abstract explaining the dataset (unlimited characters)
    Publication Year = year the data is being published
    Resource Type = typically 'dataset'
    
    Co-authors
        First and last name
        ORCID ID (will prompt based on first and last name)
        Affiliation (will prompt based on first and last name)
    
    Location of data collection
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
    
##Use

Launch the session. Once it opens, you will see a "Streamlit" app in the launcher. Click and wait for the webinterface to load. Enter the required information, check the resulting json, and donwload. 



##Renku formatting

The Renku environment setup was used from Rok Roksar's example script found here: https://gitlab.renkulab.io/rok.roskar/streamlit-v2-example

Following the instructions provided here:
    https://renku.notion.site/How-to-create-a-Streamlit-app-on-top-of-your-project-815f09a34f384396ab1f758db4110f46
    
Slight modifications were made to the .gitlab-ci.yml for compiling. 
