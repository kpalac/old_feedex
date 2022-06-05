BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "params" (
	"name"	TEXT,
	"val"	TEXT
);
CREATE TABLE "actions" (
	"name"	TEXT,
	"time"	INTEGER
);
CREATE TABLE IF NOT EXISTS "search_history" (
	"id"	INTEGER NOT NULL UNIQUE,
	"string"	TEXT,
	"feed_id"	INTEGER,
	"date"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "rules" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT,
	"type"	INTEGER,
	"feed_id"	INTEGER,
	"field_id"	TEXT,
	"string"	TEXT,
	"case_insensitive"	INTEGER,
	"lang"	TEXT,
	"weight"	NUMERIC,
	"additive"	INTEGER,
	"learned"	INTEGER,
	"context_id"	INTEGER,
	"flag"	INTEGER,
	"archive"	NUMERIC,
	"path"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE "feeds" (
	"id"	INTEGER NOT NULL UNIQUE,
	"charset"	TEXT,
	"lang"	TEXT,
	"generator"	TEXT,
	"url"	TEXT,
	"login"	TEXT,
	"domain"	TEXT,
	"passwd"	TEXT,
	"auth"	TEXT,
	"author"	TEXT,
	"author_contact"	TEXT,
	"publisher"	TEXT,
	"publisher_contact"	TEXT,
	"contributors"	TEXT,
	"copyright"	TEXT,
	"link"	TEXT,
	"title"	TEXT,
	"subtitle"	TEXT,
	"category"	TEXT,
	"tags"	TEXT,
	"name"	TEXT,
	"lastread"	TEXT,
	"lastchecked"	TEXT,
	"interval"	INTEGER,
	"error"	INTEGER,
	"autoupdate"	INTEGER,
	"http_status"	TEXT,
	"etag"	TEXT,
	"modified"	TEXT,
	"version"	TEXT,
	"is_category"	INTEGER,
	"parent_id"	INTEGER,
	"handler"	TEXT,
	"deleted"	INTEGER,
	"user_agent"	TEXT,
	"fetch"	INTEGER,
	"rx_entries"	TEXT,
	"rx_title"	TEXT,
	"rx_link"	TEXT,
	"rx_desc"	TEXT,
	"rx_author"	TEXT,
	"rx_category"	TEXT,
	"rx_text"	TEXT,
	"rx_images"	TEXT,
	"rx_pubdate"	TEXT,
	"rx_pubdate_feed"	TEXT,
	"rx_image_feed"	TEXT,
	"rx_title_feed"	TEXT,
	"rx_charset_feed"	TEXT,
	"rx_lang_feed"	TEXT,
	"script_file"	TEXT,
	"icon_name"	TEXT,
	"display_order"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "entries" (
	"id"	INTEGER NOT NULL,
	"feed_id"	INTEGER,
	"charset"	TEXT,
	"lang"	TEXT,
	"title"	TEXT,
	"author"	TEXT,
	"author_contact"	TEXT,
	"contributors"	TEXT,
	"publisher"	TEXT,
	"publisher_contact"	TEXT,
	"link"	TEXT,
	"pubdate"	INTEGER,
	"pubdate_str"	TEXT,
	"guid"	TEXT,
	"desc"	TEXT,
	"category"	TEXT,
	"tags"	TEXT,
	"comments"	TEXT,
	"text"	TEXT,
	"source"	TEXT,
	"adddate"	INTEGER,
	"adddate_str"	TEXT,
	"links"	TEXT,
	"read"	INTEGER,
	"importance"	NUMERIC,
	"tokens"	TEXT,
	"sent_count"	INTEGER,
	"word_count"	INTEGER,
	"char_count"	INTEGER,
	"polysyl_count"	INTEGER,
	"com_word_count"	INTEGER,
	"numerals_count"	INTEGER,
	"caps_count"	INTEGER,
	"readability"	NUMERIC,
	"weight"	NUMERIC,
	"flag"	INTEGER,
	"images"	TEXT,
	"enclosures"	TEXT,
	"tokens_raw"	TEXT,
	"deleted"	INTEGER,
	"note" INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE "flags" (
	"id"	INTEGER NOT NULL,
	"name"	TEXT,
	"desc"	TEXT,
	"color"	TEXT,
	"color_cli"	TEXT,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE INDEX IF NOT EXISTS "idx_rules_id" ON "rules" (
	"id"	ASC
);
CREATE INDEX IF NOT EXISTS "idx_rules_name" ON "rules" (
	"name"
);
CREATE INDEX IF NOT EXISTS "idx_rules_string" ON "rules" (
	"string"
);
CREATE INDEX IF NOT EXISTS "idx_entries_id" ON "entries" (
	"id"
);
CREATE INDEX IF NOT EXISTS "idx_entires_title" ON "entries" (
	"title"
);
CREATE INDEX IF NOT EXISTS "idx_entries_author" ON "entries" (
	"author"
);
CREATE INDEX IF NOT EXISTS "idx_entries_pubdate" ON "entries" (
	"pubdate"	DESC
);
CREATE INDEX IF NOT EXISTS "idx_entries_addeddate" ON "entries" (
	"adddate"
);
CREATE INDEX IF NOT EXISTS "idx_entries_tokens" ON "entries" (
	"tokens"
);
CREATE INDEX IF NOT EXISTS "idx_entries_link" ON "entries" (
	"link"	DESC
);
CREATE INDEX IF NOT EXISTS "idx_entries_tokens_raw" ON "entries" (
	"tokens_raw"
);
CREATE INDEX IF NOT EXISTS "idx_entries_weight" ON "entries" (
    "weight"    ASC
);
CREATE INDEX IF NOT EXISTS "idx_entries_importance" ON "entries" (
    "importance"    ASC
);
CREATE INDEX "idx_entries_pubdate_asc" ON "entries" (
    "pubdate"   ASC
);
CREATE INDEX "idx_entries_adddate_asc" ON "entries" (
    "adddate"   ASC
);
CREATE INDEX "idx_entries_feed_id" ON "entries" ( "feed_id" );

CREATE INDEX "idx_search_history_date" ON "search_history" (
	"date"
);
CREATE INDEX "idx_search_history_feed_id" ON "search_history" (
	"feed_id"
);
CREATE INDEX "idx_search_history_id" ON "search_history" (
	"id"	DESC
);
CREATE INDEX "idx_feeds_id" ON "feeds" (
	"id"
);
CREATE INDEX "idx_feeds_name" ON "feeds" (
	"name"
);
CREATE INDEX "idx_feeds_parent_id" ON "feeds" (
	"parent_id"
);
CREATE INDEX "idx_feeds_title" ON "feeds" (
	"link"
);
CREATE INDEX "idx_params_name" ON "params" (
	"name"
);
CREATE INDEX "idx_actions_name" ON "actions" (
	"name"
);
CREATE INDEX "idx_actions_time" ON "actions" (
	"time"	DESC
);
CREATE INDEX "idx_flags_id" ON "flags" (
	"id"	ASC
);
CREATE INDEX "idx_flags_name" ON "flags" (
	"name"
);
COMMIT;
