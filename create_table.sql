-- SQLite
CREATE TABLE users(
userId text,
channelId text,
teamId text,
convoId text,
realName text,
email text
);

CREATE TABLE tokens(
teamId text,
botUserId text,
botAccessToken text
);