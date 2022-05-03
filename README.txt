

ABOUT

FEEDEX is a modern news and notes aggregator to help you monitor, classify, group, rank and display your favourite news sources. 
It learns what you have found interesting in the past and ranks incomming news accordingly. 

Features:

  - RSS/Atom protocols (using Universal FeedParser)
  - HTML protocol. Downloaded resources can be parsed by predefined REGEX strings and saved as entries just like RSS items
    allowing you to monitor webpages that do not support RSS
  - External scripting support. News can be fetched by scripts (output should be JSON)
  
  - Support for rules and flags that can be manually added. This allows to automatically parse incomming entries for interesting
    information and flag/rank them accordingly. Flagging rules effectively act as alerts
  - Channels can be grouped into categories
  - Entries can be manually added to Channels and Categories as notes, hilights etc.
  - Entries that are read by you (openned in browser or added manually) are marked as interesting and keywords are automatically extracted from them
    to rank future entries by importance to you and push them to the top
  
  - Support for desktop notifications on incomming news or in scripting
  - Desktop integration with selected text and window names. They can be used for manually adding entries, e.g. by keyboard shortcut.
    This enables you to hilight some text and quickly add it to a database and contribute to ranking.
  - Feedex can be used solely as a CLI tool and in shell scripts

  - Support for queries:
      a) Full Text Search - with stemming
      b) Exact FTS - no stemming
      c) String matching

      Queries support wildcards and also FTS allows proximity search. Searching by field is possible. Multiple filtering options.

      d) Similarity search - find document similar to one selected
      e) Time series - generate time series for a term, choose grouping
      f) Term relatedness - which terms go together

  - Display options:
      b) Simple result list
      a) Grouping by category, channel or flag with preferred depth, allowing for nice news summaries in a form of a tree
      b) Showing terms in contexts
      c) Time series plot

  - Exporting results to CSV or JSON

  - Keyword extractiom is based on language models - no fancy stuff here - just phrase lists and extraction rules 
    Currently english, polish, russian and german are supported.
    Model generators can be found in data directory to modify and generate new models based on word lists and dictionaries

  - Full documentation can be viewed by feedex -hh option


INSTALLATION:

  - Unpack ZIP to temporary location
  - Run install.sh script in the base directory, to install all files to your system as well as dependencies
    Note: You need an active internet connection

  
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





