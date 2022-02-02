

ABOUT

FEEDEX is a tool for managing RSS/Atom feeds along with notes, highlights etc. It was created out of personal need to sift through large amount of information and make sense out of it 
and, even more importantly, rank it according to personal preference. Feedex stores news, ranks them by:

    a) Keyword relevance, highlighting news with phrases explicitly specified
    b) Usage relevance, learning important features based on whitch news are viewed and opened in browser or manually marked, as well as what information is highlightded and saved as annotations
    c) Readability and information content, to avoid pointing at short, non-informative articles. Text statistics are calculated and saved


Incoming news is ranked according to the criteria above, sorted and highlighted if needed. Annotations can be used as notes. Terms can be analysed by their relationship to eachother
(context dependent) and occurrence over time.

- Entries (news and notes) can be querried (string matching or full text) and filtered by many criteria.

- Feedex can notify on important/all news (if ran periodically at your desktop) or with GUI

- Links can be quickly opened in a specified browser

- New feeds, annotations and keywords can be quickly added

- Feedex learns features using language models based on extensive dictionaries. It is purely heuristic, and is a basic form of learning by extracting tags/phrases that may be important.
  Learning this way is not extremely precise, but has been enough for my personal purposes. There are no NLP or Neural Networks working under the hood. It is all embarrasingly simple :)
  Modules SnowballStemmer and Pyphen are extensively used

- You can add language models (it is pretty easy to do) by using sample_model_generator_*.py utilities in model_generators folder. 

- Available models for now: English (most developed), Polish, German, Russian

- "feedex_clip" utility can be used on Linux desktops to facilitate work by binding hotkeys to specific actions on currently selected text (by using "xclip" tool). Ever wanted to save 
  some highlighted text quickly without opening text editor? Now you can

- Feedex uses SQLite3 database to store data, and FeedParser library to download and parse RSS/Atom feeds

- Feedex displays information in terminal, but can be used for scripts as it is easy to get CSV data from it with custom delimiter (--csv, --delim)

- Special thanks to creators of Super Flat Remix icon theme

- Feedex uses Pillow module for image processing

- To run GUI run feedex with no arguments or with --gui



INSTALLATION

    Run install.sh script in the base directory, to install all files to your system as well as dependencies




ACKNOWLEDGEMENTS:

    Kurt McKee (FeedParser)
    People to thank for Snowballstemmer: https://snowballstem.org/credits.html
    Kozea community (Pyphen)
    Fredrik Lundh (PIL author), Alex Clark (Pillow fork author) and GitHub Contributors
    daniruiz (Super Flat Remix icon theme)
    Kim Saunders <kims@debian.org> Peter Ãstrand <astrand@lysator.liu.se> (XClip)
    

    If I failed to give credit to someone, please inform me and accept my apologies
    


CONTACT: Karol Pałac, palac.karol@gmail.com

Feel free to modify and play around :)
