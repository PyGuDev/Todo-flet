create table task(
    id uuid not null primary key,
    text varchar not null,
    created_at date not null
);