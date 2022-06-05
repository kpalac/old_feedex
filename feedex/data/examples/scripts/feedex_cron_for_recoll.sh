#!/bin/bash


#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


# This script exports read items from Feedex into a directory indexed by Recoll or other desktop indexer
# To use with cron or manually 

INDEXED_DIR_NEWS="$HOME/News/feedex"   # Indexed directory
INDEXED_DIR_NOTES="$HOME/Notes/feedex"   # Indexed directory

TEMPLATE_FILE="/usr/share/feedex/data/examples/templates/sample_templ_recoll_idx"
NAMES_TEMPLATE="<%id%>: <%title%>.html"

if [[ ! -d "$INDEXED_DIR_NEWS" ]]; then
    mkdir -p "$INDEXED_DIR_NEWS"
fi
if [[ ! -d "$INDEXED_DIR_NOTES" ]]; then
    mkdir -p "$INDEXED_DIR_NOTES"
fi



TMP_FILE="$HOME/.feedex_last_ix_check"


now="$(date +'%Y-%m-%d %H:%M:%S')"

if [[ ! -f "$TMP_FILE" ]]; then
    last_update="1899-12-31 00:00:00"
else
    last_update="$(< "$TMP_FILE")"
fi

feedex --html-template="$TEMPLATE_FILE" --to-files-at-dir="$INDEXED_DIR_NEWS" --to-files-names="$NAMES_TEMPLATE" --added_from="$last_update" --news --read -q
feedex --html-template="$TEMPLATE_FILE" --to-files-at-dir="$INDEXED_DIR_NOTES" --to-files-names="$NAMES_TEMPLATE" --added_from="$last_update" --note --read -q

# Handling deleted items can be a bit tricky for permatently removed ones. Basically, permanently removed entries may not be caught. 
mapfile -t DELETED_ITEMS < <(feedex --deleted --read --added_from="$last_update" --csv --trunc=20 -q | cut -d'|' -f1)
for ID in "${DELETED_ITEMS[@]}"; do
    rm "$INDEXED_DIR_NEWS"/"$ID: "*".html"
    rm "$INDEXED_DIR_NOTES"/"$ID: "*".html"
done

printf "$now" > "$TMP_FILE"

#exit 0