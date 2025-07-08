create table users (
  id bigint primary key, -- Telegram ID
  alias text not null, -- 1 kata alias unik (untuk mention)
  division text not null, -- Divisi (sales, HRD, dll)
  can_assign boolean not null default false -- Boleh kasih tugas atau tidak
);

create table tasks (
  id bigint generated always as identity primary key, -- Auto-increment ID
  giver_id bigint not null references users(id) on delete cascade, -- Pemberi tugas
  receiver_id bigint not null references users(id) on delete cascade, -- Penerima tugas
  description text not null, -- Isi tugas
  deadline date not null, -- Deadline
  created_at timestamp with time zone default timezone('utc', now()) -- Waktu dibuat
);

create table pending_users (
  id bigint primary key, -- Telegram ID
  first_name text,
  last_name text,
  requested_by bigint references users(id) on delete set null, -- Siapa yang ngajukan
  requested_at timestamp with time zone default timezone('utc', now()) -- Waktu request
);

create unique index idx_users_alias on users(alias);
