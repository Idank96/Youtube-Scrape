from __future__ import unicode_literals
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.folders.folder import Folder
from office365.sharepoint.files.file import File
from googleapiclient.discovery import build
from scipy.fftpack import fft
from scipy.io import wavfile
from pathlib import Path
import pandas as pd
import numpy as np
import youtube_dl
import datetime
import librosa
import pickle
import html
import os


def get_youtube_urls(database_path, search_term, must_have_in_title_or_description, must_not_have_in_title_or_description, pickle_exists_only_download=False):
    """
    To make it work you need to create google (Youtube) API key.
    Returns a list of YouTube urls that match the search term.
    """

    # Set the API key and service name, Idan's key.
    API_KEY = ''
    date_format = '%d_%m_%y'
    current_date = datetime.datetime.now().strftime(date_format)
    pickle_name = f'urls_{search_term}_{current_date}.pickle'

    # First page of 50 videos (still not using it. first use in the while loop)
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    # if pickle already exists, meaning the script failed yesterday
    # so it load the last urls so that it wont add the same urls to urls dict.
    if pickle_name in os.listdir(database_path):
        with open(database_path.joinpath(pickle_name), 'rb') as pickle_file:
            urls = pickle.load(pickle_file)
    else:
        urls = dict()
    if pickle_exists_only_download:
        return urls

    nextPageToken = 'default'
    limit_queries_reached = False
    while nextPageToken:
        request = youtube.search().list(q=search_term, part='snippet',
                                        type='video',
                                        maxResults=50,
                                        pageToken=nextPageToken)
        try:
            res = request.execute()
        # Meaning reached limit queries for today.
        except Exception as e:
            print(e)
            limit_queries_reached = True
            break

        for video in res['items']:
            lower_case_title = video['snippet']['title'].lower()
            lower_case_description = video['snippet']['description'].lower()

            # check if any word in must_have_in_title are present in the title or description
            # continue if found.
            if must_have_in_title_or_description:
                for word in must_have_in_title_or_description:
                    if (word in lower_case_title) or (word in lower_case_description):
                        break
                else:
                    continue

            # check if any word in must_not_have_in_title_or_description is present in the title or description.
            # break if yes.
            if must_not_have_in_title_or_description:
                found_wrong_word = False
                for word in must_not_have_in_title_or_description:
                    if (word in lower_case_title) or (word in lower_case_description):
                        found_wrong_word = True
                        break
            if found_wrong_word:
                continue

            # if both checks pass, add the video URL and title to the urls dictionary
            video_id = video['id']['videoId']
            urls[f'https://www.youtube.com/watch?v={video_id}'] = video['snippet']['title']

        if 'nextPageToken' not in res or limit_queries_reached:
            break

        nextPageToken = res['nextPageToken']

    # Pickle the urls that found. There is a limit for each day.
    # So if it found 600 files and then failed,
    # it will continue the next day.
    # The search is looking for different videos names.
    with open(database_path.joinpath(pickle_name), 'wb') as f:
        pickle.dump(urls, f)

    return urls


def downloaded_from_youtube(database_path, url, with_video=False):
    """
    Download audio/video from a YouTube video and save it to the specified database path.

    Parameters:
    - database_path (Path): The directory where the downloaded audio file will be saved.
    - url (str): The URL of the YouTube video to download audio from.
    - with_video (bool, optional): Whether to download both audio and video. If True, the audio will be extracted
      from the video. If False (default), only the audio will be downloaded.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(database_path.joinpath('%(title)s.%(ext)s')),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if with_video:
        ydl_opts = {
            'format': 'worst',
            'outtmpl': str(database_path.joinpath('%(title)s.%(ext)s')),
            'preferredcodec': 'mp4'

        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])


def upload_file_to_sharepoint(file_path, search_term):
    """
    *** NOT WORKING YET ***
    Upload file to s SharePoint server.
    To make it work you need your sharepoint_user and sharepoint_password.
    """
    # SharePoint URL
    url = 'https://wavesaudio.sharepoint.com/teams/Waves - AudioData'

    # SharePoint folder URL
    general_folder_url = url + '/Shared%20Documents/Sample%20Surfer/Instrument%20Classifier/To%20Sort%20From%20Youtube'
    specific_folder_url = general_folder_url + '/' + search_term.replace(' ', '%20') + '%20' + 'Search'
    # Create an authentication context
    context = AuthenticationContext(url)

    # Authenticate with SharePoint
    sharepoint_user = '*****@waves.com'
    sharepoint_password = '???????'
    context.acquire_token_for_user(sharepoint_user, sharepoint_password)

    # Create a client context
    client = ClientContext(url, context)

    try:
        # Check if the folder exists
        client.web.get_folder_by_server_relative_url(specific_folder_url).execute_query()
        print("Folder already exists")
    except:
        # Create the folder if it does not exist
        new_folder = Folder()
        new_folder.name = search_term + ' ' +'Search'
        client.web.folders.add(general_folder_url, new_folder).execute_query()
        print("Folder created")

    # Open the local file
    file_contents = open(file_path, "rb").read()

    target_folder = client.web.get_folder_by_server_relative_url(specific_folder_url)

    with open(file_path, 'rb') as content_file:
        file_content = content_file.read()
        target_folder.upload_file(file_path, file_content).execute_query()

    # # Create a new file on SharePoint
    # sp_file = File.create_with_binary(client, file_contents, specific_folder_url, file_path)
    #
    # # Execute the request
    # client.execute_query()


def scrape_audio(database_path, search_term, must_have_in_title, must_not_have_in_title_or_description, with_video=False):
    """
    Scrape audio files from YouTube based on search criteria and store information in a database.

    This function performs the following steps:
    1. Creates a directory at the specified 'database_path' if it doesn't exist.
    2. Retrieves YouTube video URLs based on search criteria.
    3. Creates or updates a 'scanned_files.csv' file to keep track of downloaded files.
    4. Downloads audio files from YouTube.
    
    Parameters:
    - database_path (pathlib.Path): The path to the directory where audio files and metadata will be stored.
    - search_term (str): The search term used to find relevant YouTube videos.
    - must_have_in_title (str): A string that must be present in the video title or description.
    - must_not_have_in_title_or_description (str): A string that must not be present in the video title or description.
    - with_video (bool, optional): If True, download video along with audio. Defaults to False.
    """
    if not database_path.exists():
        os.makedirs(database_path)
    urls = get_youtube_urls(database_path,
                            search_term=search_term,
                            must_have_in_title_or_description=must_have_in_title,
                            must_not_have_in_title_or_description=must_not_have_in_title_or_description,
                            pickle_exists_only_download=False)
    # create or update scanned_files.csv
    scanned_files_path = database_path.joinpath('scanned_files.csv')
    if not scanned_files_path.exists():
        scanned_files = pd.DataFrame(columns=['url', 'video name'])
        scanned_files.to_csv(scanned_files_path, index=False)

    scanned_files = pd.read_csv(scanned_files_path)
    for url in urls:
        if url in scanned_files['url'].values:
            print(f'skipping {url}: {urls[url]}')
            continue
        try:
            downloaded_from_youtube(database_path, url, with_video)
            scanned_files.loc[len(scanned_files)] = (url, urls[url])
            scanned_files.to_csv(scanned_files_path, index=False)
            # upload_file_to_sharepoint(database_path.joinpath(urls[url]), search_term=search_term)
        except Exception as e:
            print(f'Couldn\'t download because of error: \n {e}')

    print(f'Done. All the files in {database_path}'
          f'url and name were saved in scanned_files.csv file'
          f'Please upload them to SharePoint.'
          f'Delete all the files manually (without delete the scanned_files.csv) !!!!!.')
    

def main():
    """
    This function is the entry point for scraping audio files from YouTube based on specific search criteria
    and processing them (a future feature). It allows you to customize your search criteria and control
    whether to download videos along with audio.

    Parameters:
    - search_term (str): The search term used to find relevant YouTube videos.
    - must_have_in_title_or_description (list of str): A list of keywords that must be present either in the
      video title or description for the video to be downloaded. At least one keyword from this list must match.
    - must_not_have_in_title_or_description (list of str): A list of keywords that must not be present either in the
      video title or description for the video to be downloaded. If any keyword from this list matches, the video
      will not be downloaded.
    - with_video (bool, optional): If True, download the video along with the audio. Defaults to True.

    Notes:
    - The 'search_term' parameter should be a descriptive keyword or phrase to narrow down your search.
    - 'must_have_in_title_or_description' should contain keywords that help filter relevant videos.
    - 'must_not_have_in_title_or_description' should contain keywords to exclude unwanted videos.
    - The 'with_video' parameter controls whether video files are downloaded in addition to audio.
    """
    
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

    # process_audio(database_path) # Future feature


if __name__ == '__main__':
    main()


#@TODO:
    # 1) Trim leading and trailing silence from an audio signal.
    # 1) Delete files that contain band.
    # 2) Trim people talking and remain only bass parts.









    # with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    #     info_dict = ydl.extract_info(url, download=False)
    #     video_size = info_dict.get('filesize') / (1024 * 1024)  # convert to MB
    #     print(f'video_size={video_size}')
    #     if video_size <= 50:
    #         print('can download')
    #     else:
    #         print(f"Video is too large ({video_size:.2f} MB), skipping download.")

    # if with_video:
    #     ydl_opts = {
    #         'outtmpl': str(database_path.joinpath('%(title)s.%(ext)s')),
    #
    #     }
    # with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    #     ydl.download([url])

# def spectral_analysis(file):
#     # Read in the audio file
#     fs, data = wavfile.read(file)
#
#     # Perform FFT on the audio data
#     spectrum = np.abs(fft(data))
#
#     # Get the frequency values corresponding to the FFT data
#     frequencies = np.fft.fftfreq(len(spectrum), 1 / fs)
#
#     # Calculate the average amplitude for the low, mid, and high frequency bands
#     low_freq_band = spectrum[(frequencies >= 0) & (frequencies <= 1000)].mean()
#     mid_freq_band = spectrum[(frequencies > 1000) & (frequencies <= 5000)].mean()
#     high_freq_band = spectrum[(frequencies > 5000)].mean()
#
#     return low_freq_band, mid_freq_band, high_freq_band
#
# # Find the best threshold values
# def find_best_thresholds_2(bass_only_path):
#     instrument_files = [bass_only_path.joinpath(file) for file in os.listdir(bass_only_path)]
#     low_thresholds = []
#     mid_thresholds = []
#     high_thresholds = []
#     for file in instrument_files:
#         fs, data = wavfile.read(file)
#         spectrum = np.abs(fft(data))
#         frequencies = np.fft.fftfreq(len(spectrum), 1/fs)
#         low_thresholds.append(spectrum[(frequencies >= 0) & (frequencies <= 1000)].mean())
#         mid_thresholds.append(spectrum[(frequencies > 1000) & (frequencies <= 5000)].mean())
#         high_thresholds.append(spectrum[(frequencies > 5000)].mean())
#     best_low_threshold = np.mean(low_thresholds)
#     best_mid_threshold = np.mean(mid_thresholds)
#     best_high_threshold = np.mean(high_thresholds)
#     return best_low_threshold, best_mid_threshold, best_high_threshold

# def test():
#     res = {
#         'items': [
#             {
#                 'id': {'videoId': '123'},
#                 'snippet': {
#                     'title': 'acoustic bass guitar',
#                     'description': 'This is the first video'
#                 }
#             },
#             {
#                 'id': {'videoId': '456'},
#                 'snippet': {
#                     'title': 'bass guitar',
#                     'description': 'This is the second video'
#                 }
#             },
#             {
#                 'id': {'videoId': '789'},
#                 'snippet': {
#                     'title': 'Video 3',
#                     'description': 'bass'
#                 }
#             }
#         ]
#     }
#     search_term = 'electronic fretless bass'
#     must_have_in_title_or_description = ['fretless', 'bass', ]
#     must_not_have_in_title_or_description = ['acoustic']
#     urls = {}
#     for video in res['items']:
#         lower_case_title = video['snippet']['title'].lower()
#         lower_case_description = video['snippet']['description'].lower()
#
#         # check if any word in must_have_in_title are present in the title or description
#         # continue if found.
#         if must_have_in_title_or_description:
#             for word in must_have_in_title_or_description:
#                 if (word in lower_case_title) or (word in lower_case_description):
#                     break
#             else:
#                 continue
#
#         # check if any word in must_not_have_in_title_or_description is present in the title or description.
#         # break if yes.
#         if must_not_have_in_title_or_description:
#             found_wrong_word = False
#             for word in must_not_have_in_title_or_description:
#                 if (word in lower_case_title) or (word in lower_case_description):
#                     found_wrong_word = True
#                     break
#         if found_wrong_word:
#             continue
#
#         # if both checks pass, add the video URL and title to the urls dictionary
#         video_id = video['id']['videoId']
#         urls[f'https://www.youtube.com/watch?v={video_id}'] = video['snippet']['title']


"""
-------------- 6.3 --------------
search_term = 'kick drum'
must_have_in_title_or_description = ['foot', 'kick', 'bass', 'pedal']
must_not_have_in_title_or_description = ['guitar', 'slap']
with_video = True

-------------- 28.2 --------------
# option to add: "guitar"
search_term = 'clean electric guitar'
must_have_in_title_or_description = ['clean']
must_not_have_in_title_or_description = ['how to', 'acoustic', 'dirty', 'wipe', 'cleaning', 'cleaned']
with_video = False

-------------- 27.2 --------------
# if there is not enough - maybe worse trying to add 'bach' to must_have_in_title_or_description
search_term = 'church organ'
must_have_in_title_or_description = ['church', 'pipe']
must_not_have_in_title_or_description = ['hammond']
with_video = False
DONE

search_term = 'guitar overdrive'
must_have_in_title_or_description = ['overdrive', 'pedal']
must_not_have_in_title_or_description = ['acoustic', 'distor']
with_video = True
DONE
-------------- 22.2 --------------

search_term = 'electronic fretless bass'
must_have_in_title_or_description = ['fretless', 'bass']
must_not_have_in_title_or_description = ['acoustic']
DONE

-------------- 24.1 -------------- - search list, everything again with new method of excels:

search_term = 'acoustic fretless bass'
must_have_in_title_or_description = ['acoustic']
DONE (2 runs + upload both)

search_term = 'beatbox female'
must_have_in_title_or_description = ['female' ,'women', 'woman','girl', 'her']
DONE (2 runs + upload both)

search_term = 'sub kick'
must_have_in_title_or_description = ['kick', 'sub mic']
DONE

search_term = 'contrabass clarinet'
must_have_in_title_or_description = ['contrabass' ,'contra']
DONE

------------------------------------------

-------------- TODO --------------
search_term = 'snare top'
must_have_in_title_or_description = ['top mic', 'snare', 'placement']
must_not_have_in_title_or_description = ['?']
with_video = True



-------------- PROBLEMATIC --------------
*Its mostly with music and not separated.
search_term = 'female rap'
must_have_in_title_or_description = ['female', 'lady', 'she', 'woman', 'girl', '']
must_not_have_in_title_or_description = ['']
with_video = False






# # Define a function to find the best threshold values
# def find_best_thresholds(instrument_files):
#     # Initialize variables to store the best thresholds
#     best_low_threshold = 0
#     best_mid_threshold = 0
#     best_high_threshold = 0
#     best_mse = float('inf')
#
#     # Iterate through a range of possible threshold values
#     for low_threshold in range(0, 200):
#         for mid_threshold in range(0, 200):
#             for high_threshold in range(0, 200):
#                 # Initialize a variable to store the mean squared error
#                 mse = 0
#
#                 # Perform spectral analysis on each instrument file
#                 for file in instrument_files:
#                     instrument_spectrum = spectral_analysis(file)
#                     low_error = (instrument_spectrum[0] - low_threshold) ** 2
#                     mid_error = (instrument_spectrum[1] - mid_threshold) ** 2
#                     high_error = (instrument_spectrum[2] - high_threshold) ** 2
#                     mse += low_error + mid_error + high_error
#
#                 # Average the mean squared error
#                 mse /= len(instrument_files)
#
#                 # Check if this set of thresholds has a lower mean squared error
#                 if mse < best_mse:
#                     best_low_threshold = low_threshold
#                     best_mid_threshold = mid_threshold
#                     best_high_threshold = high_threshold
#                     best_mse = mse
#
#     return best_low_threshold, best_mid_threshold, best_high_threshold
#
# def process_audio(database_path):
#     """
#     1) Trim leading and trailing silence from an audio signal.
#     2) Delete files that contain band.
#     3) Trim people talking and remain only bass parts.
#     """
#     best_thresholds_2 = find_best_thresholds_2(Path(r'/Volumes/p4client/RND/MainDev/RND/Idanko/AudioScrape/bass_only')) # ran 1 time and get the best thresholds for 3 samples of single acoustic bass.
#     best_low_threshold, best_mid_threshold, best_high_threshold = best_thresholds_2[0], best_thresholds_2[1], best_thresholds_2[2]
#     # best_low_threshold, best_mid_threshold, best_high_threshold = 1680.3934075789475, 3132.2453727500047, 3335.117955657623
#     database_path = Path('/Volumes/p4client/RND/MainDev/RND/Idanko/AudioScrape/Fretless Bass Search cropped_30_seconds')
#     band_samples, single_instrument, failed_files = [], [], []
#     for file in os.listdir(database_path):
#         file = Path(database_path.joinpath(file))
#         try:
#             file_spectrum = spectral_analysis(file)
#         except Exception as e:
#             failed_files.append(file)
#             continue
#         if file_spectrum[0] > best_low_threshold and file_spectrum[1] > best_mid_threshold and file_spectrum[2] > best_high_threshold:
#             print("This is may be full band sample")
#             band_samples.append(file)
#         else:
#             print('This is an instrument sample')
#             single_instrument.append(file)
#
#     print(band_samples)
#     print(single_instrument)
#     print(failed_files)

# def scan_already_downloaded_files(database_path):
#     youtube_video_names = os.listdir(database_path)
#     if len(youtube_video_names) > 0:
#         scanned_files_df = pd.DataFrame(youtube_video_names)
#         scanned_files_df.to_csv(database_path.joinpath('scanned_files.csv'), index=False)
