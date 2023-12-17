create table sticker_info
(
    username        text    not null,
    sticker_title   text    not null,
    sticker_name    text    not null
        constraint short_name
            unique,
    line_sticker_id char(100) default '-1'::bpchar,
    user_id         integer not null,
    date            text
);
