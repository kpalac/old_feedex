BEGIN TRANSACTION;
DELETE FROM params where name = 'version';
INSERT INTO "main"."params" ("name", "val") VALUES ('version', '1.0.0');
COMMIT;
