-- SQLite
DROP TABLE teams;
CREATE TABLE teams(
  userId text,
  convoId text,
  realName text,
  reference blob
);