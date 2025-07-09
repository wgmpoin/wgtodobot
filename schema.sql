-- Table: users
create table users (
  id bigint primary key, -- Telegram ID
  alias text not null unique, -- 1 kata alias unik (untuk mention)
  division text not null, -- Divisi (sales, HRD, dll)
  role text not null check (role in ('owner', 'admin', 'user')), -- Role user: owner, admin, atau user
  can_assign boolean not null default false -- Boleh kasih tugas atau tidak
);

-- Index untuk alias
create unique index idx_users_alias on users(alias);

-- Table: tasks
create table tasks (
  id bigint generated always as identity primary key, -- Auto-increment ID
  giver_id bigint not null references users(id) on delete cascade, -- Pemberi tugas
  receiver_id bigint not null references users(id) on delete cascade, -- Penerima tugas
  description text not null, -- Isi tugas
  deadline date not null, -- Deadline
  created_at timestamp with time zone default timezone('utc', now()) -- Waktu dibuat
);

-- Table: pending_users
create table pending_users (
  id bigint primary key, -- Telegram ID
  first_name text,
  last_name text,
  requested_by bigint references users(id) on delete set null, -- Siapa yang ngajukan
  requested_at timestamp with time zone default timezone('utc', now()) -- Waktu request
);

-- Contoh INSERT untuk OWNER (Ganti 123456789 dengan Telegram ID kamu)
-- PASTIKAN MENGGANTI ID INI DENGAN ID TELEGRAM KAMU YANG SEBENARNYA
-- Ini akan menjadikan akun Telegram kamu sebagai owner pertama bot.
INSERT INTO users (id, alias, division, role, can_assign)
VALUES (123456789, 'owner', 'Owner', 'owner', TRUE);
