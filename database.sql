create table sticker_info
(
    username        text    not null,
    sticker_title   text    not null,
    sticker_name    text    not null
        constraint short_name
            unique,
    line_sticker_id integer default '-1'::integer,
    user_id         integer not null,
    date            text
);
