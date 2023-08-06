# Youtube-Scrape
This script is used to scrape audio files from YouTube based on a given search term and specific search filters.

# Prerequisites
Python 3.6 or higher
google-api-python-client library
pytube library

# Installation
Clone or download this repository.
Install the required libraries using pip:
Copy code
pip install google-api-python-client pytube
Set up the YouTube API key. Please follow the instructions here to obtain an API key.
Update the search_term, must_have_in_title_or_description, must_not_have_in_title_or_description, and with_video variables in the main() function according to your requirements.

# Usage
Run the main() function to start scraping audio files. The function takes the following parameters:

database_path: The path where the scraped files will be saved.

search_term: The search term to be used in the YouTube search.

must_have_in_title_or_description: A list of words that must appear in the title or description of the YouTube videos for the script to download them.

must_not_have_in_title_or_description: A list of words that must not appear in the title or description of the YouTube videos for the script to download them.

with_video: A boolean value indicating whether the script should download video along with the audio file.

# Examples
To download all male choir audios which include the words "male", "men", "man", or "boy" in the title or description, and which do not include the words "women" or "girl" in the title or description, with the videos included, run the following command:

```
search_term = 'male choir'
must_have_in_title_or_description = ['male', 'men', 'man', 'boy']
must_not_have_in_title_or_description = ['women', 'girl']
with_video = True

database_path = Path(f'/Volumes/p4client/RND/MainDev/RND/Idanko/AudioScrape/{search_term} Search')

scrape_audio(database_path,
             search_term,
             must_have_in_title_or_description,
             must_not_have_in_title_or_description,
             with_video=with_video)
```
